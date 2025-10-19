"""Production query models for SaaS backend"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON

from app.database import Base


class ProductionQuery(Base):
    """Captured production query metrics"""
    
    __tablename__ = "production_queries"
    
    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    environment = Column(String(50), default="production", nullable=False)  # production, staging, etc
    
    # Query metadata
    sql_normalized = Column(Text, nullable=False)  # Normalized SQL for grouping
    sql_template = Column(String(500), nullable=False)  # First 500 chars of SQL
    duration_ms = Column(Float, nullable=False)
    slow = Column(Boolean, default=False, nullable=False)
    
    # Timing
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Indexing for common queries
    __table_args__ = (
        Index("idx_prod_queries_org_env_time", "org_id", "environment", "captured_at"),
        Index("idx_prod_queries_slow", "slow", "duration_ms"),
    )
    
    organization = relationship("Organization", back_populates="production_queries")


class QueryTrend(Base):
    """Aggregated query performance trends (updated hourly)"""
    
    __tablename__ = "query_trends"
    
    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    environment = Column(String(50), default="production", nullable=False)
    
    # Query identification
    sql_normalized = Column(Text, nullable=False)
    query_hash = Column(String(64), nullable=False)  # MD5 of normalized SQL for grouping
    
    # Aggregates for this hour
    hour_start = Column(DateTime(timezone=True), nullable=False)
    count = Column(Integer, default=1)
    duration_min = Column(Float)
    duration_max = Column(Float)
    duration_avg = Column(Float)
    duration_p95 = Column(Float)
    slow_count = Column(Integer, default=0)
    
    # Trend detection
    previous_avg = Column(Float, nullable=True)
    percent_change = Column(Float, nullable=True)  # % change from previous hour
    is_regression = Column(Boolean, default=False)  # If percent_change > 25%
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_query_trends_org_env_hash", "org_id", "environment", "query_hash"),
        Index("idx_query_trends_regression", "is_regression", "org_id"),
    )
    
    organization = relationship("Organization", back_populates="query_trends")


class AlertRule(Base):
    """Alert rules for production queries"""
    
    __tablename__ = "alert_rules"
    
    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Rule conditions
    rule_type = Column(String(50), nullable=False)  # slow_query, regression, budget_violation
    environment = Column(String(50), default="production")
    
    # Thresholds
    threshold_ms = Column(Float, nullable=True)  # For slow_query
    threshold_percent = Column(Float, nullable=True)  # For regression (default: 25%)
    
    # Actions
    slack_webhook = Column(String(500), nullable=True)  # Slack webhook URL
    slack_channel = Column(String(100), nullable=True)  # Channel override
    email_recipients = Column(JSON, default=list)  # List of emails
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    organization = relationship("Organization", back_populates="alert_rules")
    alerts = relationship("Alert", back_populates="rule")


class Alert(Base):
    """Fired alerts"""
    
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey("alert_rules.id"), nullable=False)
    
    # Alert metadata
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(20), default="info")  # info, warning, critical
    
    # Context
    query_hash = Column(String(64), nullable=True)
    metric_value = Column(Float, nullable=True)
    metric_previous = Column(Float, nullable=True)
    
    # Status
    fired_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Delivery
    slack_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_alerts_org_active", "org_id", "is_active"),
        Index("idx_alerts_fired_at", "fired_at"),
    )
    
    organization = relationship("Organization", back_populates="alerts")
    rule = relationship("AlertRule", back_populates="alerts")


class ProdVsTestComparison(Base):
    """Comparison data between production and test environments"""
    
    __tablename__ = "prod_vs_test_comparison"
    
    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Test metadata
    test_run_id = Column(String(36), ForeignKey("test_runs.id"), nullable=True)
    test_name = Column(String(255), nullable=False)
    
    # Production metrics (aggregate)
    prod_query_count = Column(Integer, default=0)
    prod_avg_duration = Column(Float, default=0)
    prod_queries = Column(JSON, default=list)  # List of {sql, avg_ms, count}
    
    # Test metrics
    test_query_count = Column(Integer, default=0)
    test_avg_duration = Column(Float, default=0)
    test_queries = Column(JSON, default=list)
    
    # Analysis
    discrepancy = Column(Text)  # Analysis of differences
    regression_detected = Column(Boolean, default=False)
    
    # Timestamps
    comparison_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index("idx_prod_vs_test_org", "org_id"),
    )
    
    organization = relationship("Organization", back_populates="prod_vs_test_comparisons")
