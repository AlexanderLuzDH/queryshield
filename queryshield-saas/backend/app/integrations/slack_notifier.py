"""Slack integration for QueryShield alerts"""

import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Sends formatted alerts to Slack"""
    
    def __init__(self, webhook_url: str, channel: Optional[str] = None):
        """
        Initialize Slack notifier
        
        Args:
            webhook_url: Slack webhook URL (from app config)
            channel: Optional channel override (e.g., #alerts)
        """
        self.webhook_url = webhook_url
        self.channel = channel
        self.client = httpx.Client(timeout=10)
    
    async def send_alert(self, alert_type: str, data: Dict[str, Any]) -> bool:
        """
        Send formatted alert to Slack
        
        Args:
            alert_type: "slow_query", "regression", "budget_violation", "nplus1"
            data: Alert data (problem, threshold, actual, etc.)
        
        Returns:
            True if sent successfully
        """
        
        handler = getattr(self, f"_format_{alert_type}", None)
        if not handler:
            logger.warning(f"Unknown alert type: {alert_type}")
            return False
        
        try:
            payload = handler(data)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,
                )
                
                if response.status_code == 200:
                    logger.info(f"Slack alert sent: {alert_type}")
                    return True
                else:
                    logger.error(f"Slack error {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False
    
    def _format_slow_query(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format slow query alert"""
        
        query_hash = data.get("query_hash", "unknown")
        duration_ms = data.get("duration_ms", 0)
        threshold_ms = data.get("threshold_ms", 500)
        sql = data.get("sql", "SELECT ...")[:100]  # Truncate long SQL
        test_name = data.get("test_name", "")
        
        color = "#FF6B6B" if duration_ms > threshold_ms * 2 else "#FFA94D"
        
        return {
            "channel": self.channel,
            "attachments": [
                {
                    "fallback": f"🐌 Slow query detected: {duration_ms}ms",
                    "color": color,
                    "title": "🐌 Slow Query Detected",
                    "fields": [
                        {
                            "title": "Duration",
                            "value": f"{duration_ms}ms (threshold: {threshold_ms}ms)",
                            "short": True,
                        },
                        {
                            "title": "Slowness",
                            "value": f"{(duration_ms / threshold_ms):.1f}x threshold",
                            "short": True,
                        },
                        {
                            "title": "Query",
                            "value": f"`{sql}`",
                            "short": False,
                        },
                        {
                            "title": "Test",
                            "value": test_name or "Production",
                            "short": True,
                        },
                        {
                            "title": "Timestamp",
                            "value": datetime.utcnow().isoformat(),
                            "short": True,
                        },
                    ],
                    "footer": "QueryShield",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ],
        }
    
    def _format_regression(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format regression alert"""
        
        query_hash = data.get("query_hash", "unknown")
        previous_ms = data.get("previous_duration_ms", 0)
        current_ms = data.get("current_duration_ms", 0)
        percent_change = data.get("percent_change", 0)
        sql = data.get("sql", "SELECT ...")[:100]
        
        return {
            "channel": self.channel,
            "attachments": [
                {
                    "fallback": f"📈 Performance regression: {percent_change:+.1f}%",
                    "color": "#FF6B6B",
                    "title": "📈 Performance Regression Detected",
                    "fields": [
                        {
                            "title": "Previous",
                            "value": f"{previous_ms}ms",
                            "short": True,
                        },
                        {
                            "title": "Current",
                            "value": f"{current_ms}ms",
                            "short": True,
                        },
                        {
                            "title": "Change",
                            "value": f"{percent_change:+.1f}%",
                            "short": True,
                        },
                        {
                            "title": "Slowdown Factor",
                            "value": f"{(current_ms / previous_ms):.2f}x",
                            "short": True,
                        },
                        {
                            "title": "Query",
                            "value": f"`{sql}`",
                            "short": False,
                        },
                    ],
                    "footer": "QueryShield",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ],
        }
    
    def _format_budget_violation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format budget violation alert"""
        
        test_name = data.get("test_name", "Unknown")
        budget_type = data.get("budget_type", "queries")  # queries or duration
        max_value = data.get("max_value", 100)
        actual_value = data.get("actual_value", 150)
        
        return {
            "channel": self.channel,
            "attachments": [
                {
                    "fallback": f"💥 Budget violation: {test_name}",
                    "color": "#FF0000",
                    "title": "💥 Budget Violation",
                    "fields": [
                        {
                            "title": "Test",
                            "value": test_name,
                            "short": True,
                        },
                        {
                            "title": "Budget Type",
                            "value": budget_type.title(),
                            "short": True,
                        },
                        {
                            "title": "Budget",
                            "value": str(max_value),
                            "short": True,
                        },
                        {
                            "title": "Actual",
                            "value": str(actual_value),
                            "short": True,
                        },
                        {
                            "title": "Overage",
                            "value": f"{actual_value - max_value} ({((actual_value/max_value - 1) * 100):.0f}%)",
                            "short": True,
                        },
                    ],
                    "footer": "QueryShield",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ],
        }
    
    def _format_nplus1(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format N+1 query alert"""
        
        sql = data.get("sql", "SELECT ...")[:100]
        count = data.get("count", 0)
        suggestion = data.get("suggestion", "Use lazy loading optimization")
        code_example = data.get("code_example", "")
        test_name = data.get("test_name", "")
        
        fields = [
            {
                "title": "Problem",
                "value": f"N+1 query detected: {count} repetitions",
                "short": True,
            },
            {
                "title": "Potential Impact",
                "value": f"{count}x slower (~{count * 50}ms)",
                "short": True,
            },
            {
                "title": "Query",
                "value": f"`{sql}`",
                "short": False,
            },
            {
                "title": "Fix",
                "value": suggestion,
                "short": False,
            },
        ]
        
        if test_name:
            fields.append({
                "title": "Test",
                "value": test_name,
                "short": True,
            })
        
        if code_example:
            # Truncate if too long
            example = code_example[:200] + "..." if len(code_example) > 200 else code_example
            fields.append({
                "title": "Example",
                "value": f"```{example}```",
                "short": False,
            })
        
        return {
            "channel": self.channel,
            "attachments": [
                {
                    "fallback": f"🔄 N+1 query detected: {sql}",
                    "color": "#FFA500",
                    "title": "🔄 N+1 Query Pattern",
                    "fields": fields,
                    "footer": "QueryShield",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ],
        }
    
    def _format_missing_index(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format missing index alert"""
        
        column = data.get("column", "unknown")
        table = data.get("table", "unknown")
        sql = data.get("sql", "SELECT ...")[:100]
        impact = data.get("impact", "10-100x slower")
        
        return {
            "channel": self.channel,
            "attachments": [
                {
                    "fallback": f"🗂️ Missing index on {table}.{column}",
                    "color": "#FFD700",
                    "title": "🗂️ Missing Index",
                    "fields": [
                        {
                            "title": "Table",
                            "value": table,
                            "short": True,
                        },
                        {
                            "title": "Column",
                            "value": column,
                            "short": True,
                        },
                        {
                            "title": "Potential Impact",
                            "value": impact,
                            "short": False,
                        },
                        {
                            "title": "Query",
                            "value": f"`{sql}`",
                            "short": False,
                        },
                        {
                            "title": "Fix",
                            "value": f"`CREATE INDEX idx_{column} ON {table}({column});`",
                            "short": False,
                        },
                    ],
                    "footer": "QueryShield",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ],
        }


class SlackAlertRule:
    """Configurable alert rules for Slack"""
    
    def __init__(
        self,
        webhook_url: str,
        channel: Optional[str] = None,
        alert_thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize with thresholds
        
        Args:
            webhook_url: Slack webhook
            channel: Slack channel
            alert_thresholds: Custom thresholds for alerts
                - slow_query_ms: Slow query threshold
                - regression_percent: Regression % threshold
                - budget_percent: Budget overage % threshold
        """
        self.notifier = SlackNotifier(webhook_url, channel)
        
        self.thresholds = {
            "slow_query_ms": 500,
            "regression_percent": 25,  # 25% slower = alert
            "budget_percent": 10,  # 10% over budget = alert
            "nplus1_min_count": 5,  # 5+ repetitions = alert
        }
        
        if alert_thresholds:
            self.thresholds.update(alert_thresholds)
    
    async def evaluate_and_alert(
        self,
        problems: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Evaluate problems and send alerts if thresholds exceeded
        
        Args:
            problems: List of problem dicts from report
        
        Returns:
            List of alert types sent
        """
        
        alerts_sent = []
        
        for problem in problems:
            problem_type = problem.get("type", "")
            
            if problem_type == "SLOW_QUERY":
                if problem.get("duration_ms", 0) > self.thresholds["slow_query_ms"]:
                    sent = await self.notifier.send_alert("slow_query", problem)
                    if sent:
                        alerts_sent.append("slow_query")
            
            elif problem_type == "N+1":
                if problem.get("count", 0) >= self.thresholds["nplus1_min_count"]:
                    sent = await self.notifier.send_alert("nplus1", problem)
                    if sent:
                        alerts_sent.append("nplus1")
            
            elif problem_type == "REGRESSION":
                if abs(problem.get("percent_change", 0)) > self.thresholds["regression_percent"]:
                    sent = await self.notifier.send_alert("regression", problem)
                    if sent:
                        alerts_sent.append("regression")
            
            elif problem_type == "BUDGET_VIOLATION":
                overage_percent = ((problem.get("actual", 0) / problem.get("max", 100)) - 1) * 100
                if overage_percent > self.thresholds["budget_percent"]:
                    sent = await self.notifier.send_alert("budget_violation", problem)
                    if sent:
                        alerts_sent.append("budget_violation")
            
            elif problem_type == "MISSING_INDEX":
                sent = await self.notifier.send_alert("missing_index", problem)
                if sent:
                    alerts_sent.append("missing_index")
        
        return alerts_sent
