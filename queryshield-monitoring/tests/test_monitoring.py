"""Tests for QueryShield production monitoring"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from queryshield_monitoring.middleware import (
    QueryMetric,
    QuerySampler,
    QueryBatcher,
    MonitoringConfig,
    ProductionMonitor,
)


class TestQueryMetric:
    """Tests for QueryMetric"""
    
    def test_query_metric_creation(self):
        """Test creating a query metric"""
        metric = QueryMetric(
            sql="SELECT * FROM users",
            duration_ms=42.5,
            timestamp=datetime.now(timezone.utc),
        )
        assert metric.sql == "SELECT * FROM users"
        assert metric.duration_ms == 42.5
        assert metric.slow is False
    
    def test_query_metric_slow_flag(self):
        """Test slow query detection"""
        metric = QueryMetric(
            sql="SELECT * FROM users",
            duration_ms=600,
            timestamp=datetime.now(timezone.utc),
            slow=True,
        )
        assert metric.slow is True
    
    def test_query_metric_to_dict(self):
        """Test serialization"""
        now = datetime.now(timezone.utc)
        metric = QueryMetric(
            sql="SELECT 1",
            duration_ms=1.5,
            timestamp=now,
            slow=False,
        )
        d = metric.to_dict()
        assert d["sql"] == "SELECT 1"
        assert d["duration_ms"] == 1.5
        assert d["slow"] is False
        assert d["timestamp"] == now.isoformat()


class TestQuerySampler:
    """Tests for QuerySampler"""
    
    def test_sampler_100_percent(self):
        """Test 100% sampling"""
        sampler = QuerySampler(sample_rate=1.0)
        assert sampler.should_sample() is True
        assert sampler.should_sample() is True
    
    def test_sampler_0_percent(self):
        """Test 0% sampling"""
        sampler = QuerySampler(sample_rate=0.0)
        assert sampler.should_sample() is False
        assert sampler.should_sample() is False
    
    def test_sampler_1_percent(self):
        """Test 1% sampling (probabilistic)"""
        sampler = QuerySampler(sample_rate=0.01)
        samples = sum(1 for _ in range(1000) if sampler.should_sample())
        # Should be roughly 10 (1% of 1000), allow ±50% variance
        assert 5 <= samples <= 30
    
    def test_sampler_clamping(self):
        """Test that sample rate is clamped to [0, 1]"""
        sampler = QuerySampler(sample_rate=2.0)
        assert sampler.sample_rate == 1.0
        
        sampler = QuerySampler(sample_rate=-1.0)
        assert sampler.sample_rate == 0.0


class TestQueryBatcher:
    """Tests for QueryBatcher"""
    
    def test_batcher_batch_size(self):
        """Test batch size triggering"""
        batcher = QueryBatcher(batch_size=3, batch_timeout_seconds=60)
        now = datetime.now(timezone.utc)
        
        # First two shouldn't trigger flush
        assert batcher.add(QueryMetric("SELECT 1", 1.0, now)) is False
        assert batcher.add(QueryMetric("SELECT 2", 2.0, now)) is False
        
        # Third should trigger
        assert batcher.add(QueryMetric("SELECT 3", 3.0, now)) is True
    
    def test_batcher_get_batch(self):
        """Test batch retrieval"""
        batcher = QueryBatcher(batch_size=10, batch_timeout_seconds=60)
        now = datetime.now(timezone.utc)
        
        # Add a few queries
        for i in range(3):
            batcher.add(QueryMetric(f"SELECT {i}", float(i), now))
        
        # Get batch
        batch = batcher.get_batch()
        assert len(batch) == 3
        assert batch[0].sql == "SELECT 0"
        
        # Batch should be cleared
        assert len(batcher.get_batch()) == 0
    
    def test_batcher_timeout(self):
        """Test batch timeout"""
        batcher = QueryBatcher(batch_size=100, batch_timeout_seconds=0.1)
        now = datetime.now(timezone.utc)
        
        batcher.add(QueryMetric("SELECT 1", 1.0, now))
        assert batcher.add(QueryMetric("SELECT 2", 2.0, now)) is False
        
        # Wait for timeout
        time.sleep(0.15)
        assert batcher.add(QueryMetric("SELECT 3", 3.0, now)) is True


class TestMonitoringConfig:
    """Tests for MonitoringConfig"""
    
    def test_config_defaults(self):
        """Test default configuration"""
        config = MonitoringConfig()
        assert config.sample_rate == 0.01
        assert config.slow_query_threshold_ms == 500
        assert config.batch_size == 100
        assert config.enabled is True
    
    def test_config_custom(self):
        """Test custom configuration"""
        config = MonitoringConfig(
            sample_rate=0.5,
            slow_query_threshold_ms=1000,
            batch_size=50,
        )
        assert config.sample_rate == 0.5
        assert config.slow_query_threshold_ms == 1000
        assert config.batch_size == 50
    
    @patch.dict('os.environ', {
        'QUERYSHIELD_SAMPLE_RATE': '0.5',
        'QUERYSHIELD_SLOW_QUERY_MS': '1000',
    })
    def test_config_from_env(self):
        """Test loading config from environment"""
        config = MonitoringConfig.from_env()
        assert config.sample_rate == 0.5
        assert config.slow_query_threshold_ms == 1000


class TestProductionMonitor:
    """Tests for ProductionMonitor"""
    
    def test_monitor_record_query(self):
        """Test recording queries"""
        config = MonitoringConfig(api_key="", enabled=True)
        monitor = ProductionMonitor(config)
        
        # Should not raise
        monitor.record_query("SELECT 1", 10.0)
    
    def test_monitor_disabled(self):
        """Test disabled monitoring"""
        config = MonitoringConfig(enabled=False)
        monitor = ProductionMonitor(config)
        
        # Should still not raise
        monitor.record_query("SELECT 1", 10.0)
    
    def test_monitor_sampling(self):
        """Test sampling in monitor"""
        config = MonitoringConfig(sample_rate=0.0, api_key="")
        monitor = ProductionMonitor(config)
        
        # With 0% sampling, no queries should be recorded
        monitor.record_query("SELECT 1", 10.0)
        batch = monitor.batcher.get_batch()
        assert len(batch) == 0


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_flow_mock_upload(self):
        """Test full monitoring flow with mocked upload"""
        config = MonitoringConfig(
            api_url="http://localhost:8000",
            api_key="sk_test",
            org_id="org_123",
            sample_rate=1.0,
            batch_size=2,
        )
        
        monitor = ProductionMonitor(config)
        
        # Mock the uploader
        with patch.object(monitor.uploader, 'upload_async', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = True
            
            # Record queries
            monitor.record_query("SELECT 1", 50.0)
            monitor.record_query("SELECT 2", 75.0)  # Should trigger batch
            
            # Give async task time to complete
            await asyncio.sleep(0.1)
            
            # Verify upload was called
            assert mock_upload.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
