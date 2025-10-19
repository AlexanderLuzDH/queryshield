"""Production monitoring middleware for capturing and reporting queries"""

import time
import random
import threading
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio

import httpx

logger = logging.getLogger(__name__)


@dataclass
class QueryMetric:
    """Production query metric"""
    sql: str
    duration_ms: float
    timestamp: datetime
    slow: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql": self.sql,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "slow": self.slow,
        }


class QuerySampler:
    """Samples queries based on configurable rate"""
    
    def __init__(self, sample_rate: float = 0.01):
        """
        Args:
            sample_rate: Fraction of requests to sample (default: 1%)
        """
        self.sample_rate = max(0.0, min(1.0, sample_rate))
    
    def should_sample(self) -> bool:
        """Determine if current request should be sampled"""
        if self.sample_rate >= 1.0:
            return True
        if self.sample_rate <= 0.0:
            return False
        return random.random() < self.sample_rate


class QueryBatcher:
    """Batches queries for efficient SaaS upload"""
    
    def __init__(self, batch_size: int = 100, batch_timeout_seconds: int = 30):
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.queries: List[QueryMetric] = []
        self.last_flush = time.time()
        self._lock = threading.Lock()
    
    def add(self, metric: QueryMetric) -> bool:
        """Add query metric. Returns True if batch should be flushed."""
        with self._lock:
            self.queries.append(metric)
            
            # Check if batch is full
            if len(self.queries) >= self.batch_size:
                return True
            
            # Check if timeout reached
            if time.time() - self.last_flush >= self.batch_timeout_seconds:
                return True
            
            return False
    
    def get_batch(self) -> List[QueryMetric]:
        """Get and clear current batch"""
        with self._lock:
            batch = self.queries.copy()
            self.queries.clear()
            self.last_flush = time.time()
            return batch


class SaaSUploader:
    """Uploads query metrics to QueryShield SaaS"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(timeout=10)
    
    async def upload_async(self, metrics: List[QueryMetric], org_id: str, env: str = "production") -> bool:
        """Upload metrics asynchronously"""
        if not metrics:
            return True
        
        try:
            url = f"{self.api_url}/api/production-queries"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "org_id": org_id,
                "environment": env,
                "queries": [m.to_dict() for m in metrics],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
                
                if response.status_code in (200, 201):
                    logger.debug(f"Uploaded {len(metrics)} query metrics")
                    return True
                else:
                    logger.warning(f"Failed to upload metrics: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error uploading metrics: {e}")
            return False
    
    def close(self):
        """Close HTTP client"""
        self.client.close()


class MonitoringConfig:
    """Configuration for production monitoring"""
    
    def __init__(
        self,
        api_url: str = "https://api.queryshield.app",
        api_key: str = "",
        org_id: str = "",
        environment: str = "production",
        sample_rate: float = 0.01,
        slow_query_threshold_ms: float = 500,
        batch_size: int = 100,
        batch_timeout_seconds: int = 30,
        enabled: bool = True,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.org_id = org_id
        self.environment = environment
        self.sample_rate = sample_rate
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.enabled = enabled
    
    @classmethod
    def from_env(cls) -> "MonitoringConfig":
        """Load configuration from environment variables"""
        import os
        
        return cls(
            api_url=os.getenv("QUERYSHIELD_API_URL", "https://api.queryshield.app"),
            api_key=os.getenv("QUERYSHIELD_API_KEY", ""),
            org_id=os.getenv("QUERYSHIELD_ORG_ID", ""),
            environment=os.getenv("QUERYSHIELD_ENV", "production"),
            sample_rate=float(os.getenv("QUERYSHIELD_SAMPLE_RATE", "0.01")),
            slow_query_threshold_ms=float(os.getenv("QUERYSHIELD_SLOW_QUERY_MS", "500")),
            batch_size=int(os.getenv("QUERYSHIELD_BATCH_SIZE", "100")),
            batch_timeout_seconds=int(os.getenv("QUERYSHIELD_BATCH_TIMEOUT", "30")),
            enabled=os.getenv("QUERYSHIELD_ENABLED", "true").lower() == "true",
        )


class ProductionMonitor:
    """Main monitoring coordinator"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.sampler = QuerySampler(config.sample_rate)
        self.batcher = QueryBatcher(config.batch_size, config.batch_timeout_seconds)
        self.uploader = SaaSUploader(config.api_url, config.api_key) if config.api_key else None
        self._background_thread = None
        self._stop_event = threading.Event()
    
    def record_query(self, sql: str, duration_ms: float) -> None:
        """Record a query metric"""
        if not self.config.enabled or not self.sampler.should_sample():
            return
        
        metric = QueryMetric(
            sql=sql,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
            slow=duration_ms > self.config.slow_query_threshold_ms,
        )
        
        should_flush = self.batcher.add(metric)
        if should_flush and self.uploader:
            self._flush_async()
    
    def _flush_async(self) -> None:
        """Flush batch asynchronously"""
        batch = self.batcher.get_batch()
        if batch and self.uploader:
            # Run upload in background
            asyncio.create_task(self.uploader.upload_async(batch, self.config.org_id, self.config.environment))
    
    def shutdown(self) -> None:
        """Shutdown monitor"""
        self._stop_event.set()
        if self.uploader:
            # Final flush
            batch = self.batcher.get_batch()
            if batch:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.uploader.upload_async(batch, self.config.org_id, self.config.environment))
                loop.close()
            self.uploader.close()
