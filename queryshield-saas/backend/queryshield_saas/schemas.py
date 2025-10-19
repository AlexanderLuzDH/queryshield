from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# Authentication
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    organization_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    organization_id: str
    api_key: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Organization
class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    query_budget: int
    time_budget_ms: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Report
class ProblemDetail(BaseModel):
    id: str
    type: str
    problem_id: str
    test_name: Optional[str] = None
    severity: str
    evidence: Optional[Dict[str, Any]] = None
    suggestion: Optional[Dict[str, Any]] = None
    estimated_savings: Optional[float] = None

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    id: str
    organization_id: str
    framework: Optional[Dict[str, Any]] = None
    db_vendor: Optional[str] = None
    tests_total: int
    queries_total: int
    duration_ms: float
    problems_count: int
    estimated_monthly_cost: Optional[float] = None
    total_savings_potential: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportDetailResponse(ReportResponse):
    problems: List[ProblemDetail] = []
    report_data: Optional[Dict[str, Any]] = None


class ReportCreateRequest(BaseModel):
    """Create a new report from QueryShield analysis"""
    version: str = "1"
    project_root: Optional[str] = None
    framework: Optional[Dict[str, Any]] = None
    db_vendor: Optional[str] = None
    tests: List[Dict[str, Any]] = []
    cost_analysis: Optional[Dict[str, Any]] = None
    run_duration_ms: Optional[float] = None


class ReportListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    reports: List[ReportResponse]


# Comparison
class ReportComparisonResponse(BaseModel):
    id: str
    baseline_report_id: str
    current_report_id: str
    queries_delta: int
    cost_delta: Optional[float] = None
    duration_delta_ms: Optional[float] = None
    problems_added: int
    problems_fixed: int
    regression_detected: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CompareReportsRequest(BaseModel):
    baseline_report_id: str
    current_report_id: str


# Alert Configuration
class AlertConfigRequest(BaseModel):
    type: str  # slack, github, pagerduty, webhook
    enabled: bool = True
    config: Dict[str, Any]  # Type-specific config
    alert_on_violation: bool = True
    alert_on_regression: bool = True
    alert_on_slow_query: bool = False
    slow_query_threshold_ms: int = 500


class AlertConfigResponse(BaseModel):
    id: str
    organization_id: str
    type: str
    enabled: bool
    alert_on_violation: bool
    alert_on_regression: bool
    alert_on_slow_query: bool
    slow_query_threshold_ms: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Dashboard Summary
class TestSummary(BaseModel):
    name: str
    queries_count: int
    duration_ms: float
    problems: List[str]  # Problem types
    estimated_cost: Optional[float] = None


class DashboardSummary(BaseModel):
    organization: OrganizationResponse
    latest_report: Optional[ReportResponse] = None
    total_reports: int
    total_queries_trend: Optional[List[int]] = None
    top_problems: List[ProblemDetail] = []
    recent_reports: List[ReportResponse] = []


# Health check
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


# Error response
class ErrorResponse(BaseModel):
    detail: str
    code: str
    timestamp: datetime
