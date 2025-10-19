from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class User(Base):
    """User account"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    api_key = Column(String(64), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="members")
    reports = relationship("Report", back_populates="created_by")

    __table_args__ = (
        Index("ix_users_organization_id", "organization_id"),
    )


class Organization(Base):
    """Team/Organization"""
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    plan = Column(String(50), default="free")  # free, pro, enterprise
    query_budget = Column(Integer, default=50)
    time_budget_ms = Column(Integer, default=5000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="organization", cascade="all, delete-orphan")
    alert_configs = relationship("AlertConfig", back_populates="organization", cascade="all, delete-orphan")


class Report(Base):
    """QueryShield analysis report"""
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Report metadata
    version = Column(String(10), default="1")
    project_root = Column(String(1024))
    framework = Column(JSON)  # {"name": "django", "version": "4.2.0"}
    db_vendor = Column(String(50))  # postgresql, mysql, sqlite
    
    # Analysis results
    tests_total = Column(Integer, default=0)
    queries_total = Column(Integer, default=0)
    duration_ms = Column(Float, default=0.0)
    problems_count = Column(Integer, default=0)
    
    # Cost analysis
    estimated_monthly_cost = Column(Float, nullable=True)
    total_savings_potential = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), default="complete")  # complete, processing, failed
    run_duration_ms = Column(Float, nullable=True)
    
    # Full report JSON
    report_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="reports")
    created_by = relationship("User", back_populates="reports")
    problems = relationship("Problem", back_populates="report", cascade="all, delete-orphan")
    comparisons = relationship("ReportComparison", back_populates="current_report", foreign_keys="ReportComparison.current_report_id", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reports_organization_id_created_at", "organization_id", "created_at"),
        Index("ix_reports_organization_id_status", "organization_id", "status"),
    )


class Problem(Base):
    """Database problem detected in a report"""
    __tablename__ = "problems"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False, index=True)
    
    type = Column(String(100), nullable=False)  # N+1, MISSING_INDEX, etc
    problem_id = Column(String(255), nullable=False)  # Unique problem ID from analysis
    test_name = Column(String(255))
    severity = Column(String(50), default="medium")  # low, medium, high
    
    evidence = Column(JSON)  # Problem-specific evidence
    suggestion = Column(JSON)  # Recommended fix
    estimated_savings = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="problems")

    __table_args__ = (
        Index("ix_problems_report_id_type", "report_id", "type"),
    )


class ReportComparison(Base):
    """Comparison between two reports (for regression detection)"""
    __tablename__ = "report_comparisons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    baseline_report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    current_report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    
    queries_delta = Column(Integer)  # +5, -3, etc
    cost_delta = Column(Float)  # +$1.50, -$0.25, etc
    duration_delta_ms = Column(Float)
    problems_added = Column(Integer, default=0)
    problems_fixed = Column(Integer, default=0)
    
    regression_detected = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    current_report = relationship("Report", foreign_keys=[current_report_id], back_populates="comparisons")

    __table_args__ = (
        Index("ix_report_comparisons_organization_id", "organization_id"),
    )


class AlertConfig(Base):
    """Alert configuration for organizations"""
    __tablename__ = "alert_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    
    type = Column(String(50), nullable=False)  # slack, github, pagerduty, webhook
    enabled = Column(Boolean, default=True)
    
    # Configuration (varies by type)
    config = Column(JSON)  # slack_webhook_url, github_token, etc
    
    # Alert triggers
    alert_on_violation = Column(Boolean, default=True)
    alert_on_regression = Column(Boolean, default=True)
    alert_on_slow_query = Column(Boolean, default=False)
    slow_query_threshold_ms = Column(Integer, default=500)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="alert_configs")

    __table_args__ = (
        Index("ix_alert_configs_organization_id_type", "organization_id", "type"),
    )
