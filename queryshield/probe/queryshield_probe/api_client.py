"""
SaaS API client for uploading QueryShield reports
"""
import httpx
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class QueryShieldAPIClient:
    """Client for interacting with QueryShield SaaS API"""
    
    def __init__(
        self,
        api_url: str = "https://api.queryshield.app",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
    
    def submit_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a report to the SaaS backend
        
        Args:
            report: QueryShield report JSON
            
        Returns:
            Response from server with report ID
            
        Raises:
            Exception if upload fails
        """
        if not self.api_key:
            raise ValueError("API key required to submit reports")
        
        url = f"{self.api_url}/api/reports"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            response = self.client.post(
                url,
                json=report,
                headers=headers,
            )
            
            if response.status_code == 401:
                raise Exception("Invalid API key")
            elif response.status_code == 400:
                raise Exception(f"Bad request: {response.text}")
            elif response.status_code >= 500:
                raise Exception(f"Server error: {response.status_code}")
            elif response.status_code not in (200, 201):
                raise Exception(f"Unexpected status: {response.status_code}")
            
            return response.json()
        except httpx.TimeoutException:
            raise Exception("Request timeout - server not responding")
        except httpx.RequestError as e:
            raise Exception(f"Network error: {e}")
    
    def fetch_baseline(self, org_id: str, test_name: str) -> Optional[Dict[str, Any]]:
        """Fetch baseline report for a test
        
        Args:
            org_id: Organization ID
            test_name: Test name to fetch baseline for
            
        Returns:
            Baseline report if found, None otherwise
        """
        if not self.api_key:
            return None
        
        url = f"{self.api_url}/api/reports"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"org_id": org_id, "test": test_name, "limit": 1}
        
        try:
            response = self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                reports = data.get("reports", [])
                if reports:
                    return reports[0]
        except Exception as e:
            logger.warning(f"Failed to fetch baseline: {e}")
        
        return None
    
    def close(self):
        """Close HTTP client"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class LocalBaseline:
    """Manage local baseline reports for comparison"""
    
    def __init__(self, baseline_dir: str = ".queryshield"):
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(exist_ok=True)
    
    def save_baseline(self, report: Dict[str, Any], name: str = "baseline") -> Path:
        """Save report as local baseline
        
        Args:
            report: QueryShield report JSON
            name: Baseline name (default: baseline)
            
        Returns:
            Path to saved baseline file
        """
        baseline_file = self.baseline_dir / f"{name}.json"
        with open(baseline_file, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved baseline: {baseline_file}")
        return baseline_file
    
    def load_baseline(self, name: str = "baseline") -> Optional[Dict[str, Any]]:
        """Load local baseline report
        
        Args:
            name: Baseline name
            
        Returns:
            Loaded report if found, None otherwise
        """
        baseline_file = self.baseline_dir / f"{name}.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                return json.load(f)
        return None
    
    def baseline_exists(self, name: str = "baseline") -> bool:
        """Check if baseline file exists"""
        return (self.baseline_dir / f"{name}.json").exists()
