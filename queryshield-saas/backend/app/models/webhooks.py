"""Webhook configuration models for SaaS integrations"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON

from app.database import Base


class WebhookConfig(Base):
    """Webhook configuration for external integrations"""
    
    __tablename__ = "webhook_configs"
    
    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Integration type
    provider = Column(String(50), nullable=False)  # slack, github, pagerduty, custom
    
    # Connection details
    webhook_url = Column(Text, nullable=False)  # Encrypted in production
    channel = Column(String(100), nullable=True)  # For Slack: #channel override
    
    # Configuration
    is_active = Column(Boolean, default=True)
    
    # Alert thresholds (for this webhook)
    alert_thresholds = Column(JSON, default=dict)  # {
    #     "slow_query_ms": 500,
    #     "regression_percent": 25,
    #     "budget_percent": 10,
    #     "nplus1_min_count": 5
    # }
    
    # Which alerts to send
    alert_types = Column(JSON, default=lambda: [
        "slow_query",
        "regression",
        "budget_violation",
        "nplus1",
        "missing_index",
    ])  # List of alert types to send
    
    # Test status
    last_test_at = Column(DateTime(timezone=True), nullable=True)
    last_test_status = Column(String(20), nullable=True)  # success, failed
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_webhooks_org_provider", "org_id", "provider"),
    )
    
    organization = relationship("Organization", back_populates="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook")


class WebhookDelivery(Base):
    """Record of webhook delivery for debugging"""
    
    __tablename__ = "webhook_deliveries"
    
    id = Column(String(36), primary_key=True)
    webhook_id = Column(String(36), ForeignKey("webhook_configs.id"), nullable=False, index=True)
    
    # Alert info
    alert_type = Column(String(50), nullable=False)
    alert_data = Column(JSON, nullable=False)
    
    # Delivery status
    status_code = Column(Integer, nullable=True)
    response_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Retry info
    attempt_number = Column(Integer, default=1)
    max_retries = Column(Integer, default=3)
    
    # Timing
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index("idx_deliveries_webhook", "webhook_id"),
        Index("idx_deliveries_status", "webhook_id", "status_code"),
    )
    
    webhook = relationship("WebhookConfig", back_populates="deliveries")


class SlackWebhookConfig(WebhookConfig):
    """Slack-specific webhook configuration"""
    
    __mapper_args__ = {
        'polymorphic_identity': 'slack',
    }
    
    @classmethod
    def create(
        cls,
        org_id: str,
        webhook_url: str,
        channel: Optional[str] = None,
        alert_thresholds: Optional[Dict[str, Any]] = None,
    ):
        """Create Slack webhook config"""
        
        config = cls(
            id=str(__import__('uuid').uuid4()),
            org_id=org_id,
            provider="slack",
            webhook_url=webhook_url,
            channel=channel,
            alert_thresholds=alert_thresholds or {
                "slow_query_ms": 500,
                "regression_percent": 25,
                "budget_percent": 10,
                "nplus1_min_count": 5,
            },
            alert_types=[
                "slow_query",
                "regression",
                "budget_violation",
                "nplus1",
                "missing_index",
            ],
        )
        return config


class GitHubWebhookConfig(WebhookConfig):
    """GitHub-specific webhook configuration"""
    
    __mapper_args__ = {
        'polymorphic_identity': 'github',
    }
    
    @classmethod
    def create(
        cls,
        org_id: str,
        webhook_url: str,
        alert_thresholds: Optional[Dict[str, Any]] = None,
    ):
        """Create GitHub webhook config"""
        
        config = cls(
            id=str(__import__('uuid').uuid4()),
            org_id=org_id,
            provider="github",
            webhook_url=webhook_url,
            alert_thresholds=alert_thresholds or {
                "create_issue_on_severe": True,  # Create issue if severity >= critical
            },
            alert_types=[
                "regression",
                "budget_violation",
            ],
        )
        return config
