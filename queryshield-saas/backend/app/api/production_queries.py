"""Production query endpoints for SaaS backend"""

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.production_queries import (
    ProductionQuery,
    QueryTrend,
    AlertRule,
    Alert,
    ProdVsTestComparison,
)
from app.models.organization import Organization
from app.auth import get_current_user

router = APIRouter(prefix="/api/production", tags=["production-queries"])


# ============ Schemas ============

class ProductionQueryCreate(BaseModel):
    """Production query submission"""
    org_id: str
    environment: str = "production"
    sql_normalized: str
    sql_template: str
    duration_ms: float
    slow: bool = False


class ProductionQueryResponse(BaseModel):
    """Production query response"""
    id: str
    sql_template: str
    duration_ms: float
    slow: bool
    captured_at: datetime
    
    class Config:
        from_attributes = True


class QueryTrendResponse(BaseModel):
    """Query trend response"""
    id: str
    query_hash: str
    count: int
    duration_avg: Optional[float]
    duration_p95: Optional[float]
    slow_count: int
    is_regression: bool
    percent_change: Optional[float]
    
    class Config:
        from_attributes = True


class AlertRuleCreate(BaseModel):
    """Alert rule creation"""
    name: str
    description: Optional[str] = None
    rule_type: str  # slow_query, regression, budget_violation
    environment: str = "production"
    threshold_ms: Optional[float] = None
    threshold_percent: Optional[float] = 25.0
    slack_webhook: Optional[str] = None
    slack_channel: Optional[str] = None
    email_recipients: Optional[List[str]] = None


class AlertRuleResponse(BaseModel):
    """Alert rule response"""
    id: str
    name: str
    rule_type: str
    enabled: bool
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """Alert response"""
    id: str
    title: str
    severity: str
    is_active: bool
    fired_at: datetime
    
    class Config:
        from_attributes = True


class ProdVsTestComparisonResponse(BaseModel):
    """Production vs test comparison"""
    id: str
    test_name: str
    prod_query_count: int
    test_query_count: int
    regression_detected: bool
    discrepancy: Optional[str]
    
    class Config:
        from_attributes = True


# ============ Production Queries ============

@router.post("/queries", response_model=dict)
def submit_production_queries(
    queries: List[ProductionQueryCreate],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit batch of production queries"""
    
    if not queries:
        return {"count": 0}
    
    # Validate org access
    org_id = queries[0].org_id
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    created_queries = []
    for query_data in queries:
        pq = ProductionQuery(
            id=str(uuid.uuid4()),
            org_id=org_id,
            environment=query_data.environment,
            sql_normalized=query_data.sql_normalized,
            sql_template=query_data.sql_template,
            duration_ms=query_data.duration_ms,
            slow=query_data.slow,
        )
        db.add(pq)
        created_queries.append(pq)
    
    db.commit()
    return {"count": len(created_queries)}


@router.get("/queries", response_model=List[ProductionQueryResponse])
def list_production_queries(
    org_id: str,
    environment: str = "production",
    slow_only: bool = False,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List production queries for organization"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    query = db.query(ProductionQuery).filter(
        ProductionQuery.org_id == org_id,
        ProductionQuery.environment == environment,
    )
    
    if slow_only:
        query = query.filter_by(slow=True)
    
    return query.order_by(desc(ProductionQuery.captured_at)).limit(limit).all()


# ============ Query Trends ============

@router.get("/trends", response_model=List[QueryTrendResponse])
def get_query_trends(
    org_id: str,
    environment: str = "production",
    regression_only: bool = False,
    limit: int = 50,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get query trends for organization"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    query = db.query(QueryTrend).filter(
        QueryTrend.org_id == org_id,
        QueryTrend.environment == environment,
    )
    
    if regression_only:
        query = query.filter_by(is_regression=True)
    
    return query.order_by(desc(QueryTrend.updated_at)).limit(limit).all()


@router.post("/trends/calculate", response_model=dict)
def calculate_trends(
    org_id: str,
    environment: str = "production",
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger trend calculation (usually done hourly)"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Get queries from last hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    queries = db.query(ProductionQuery).filter(
        ProductionQuery.org_id == org_id,
        ProductionQuery.environment == environment,
        ProductionQuery.captured_at >= one_hour_ago,
    ).all()
    
    trends_created = 0
    for normalized_sql in set(q.sql_normalized for q in queries):
        hour_queries = [q for q in queries if q.sql_normalized == normalized_sql]
        
        query_hash = hashlib.md5(normalized_sql.encode()).hexdigest()
        
        durations = [q.duration_ms for q in hour_queries]
        durations.sort()
        
        trend = QueryTrend(
            id=str(uuid.uuid4()),
            org_id=org_id,
            environment=environment,
            sql_normalized=normalized_sql,
            query_hash=query_hash,
            hour_start=one_hour_ago,
            count=len(hour_queries),
            duration_min=min(durations),
            duration_max=max(durations),
            duration_avg=sum(durations) / len(durations),
            duration_p95=durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
            slow_count=len([q for q in hour_queries if q.slow]),
        )
        
        db.add(trend)
        trends_created += 1
    
    db.commit()
    return {"trends_created": trends_created}


# ============ Alert Rules ============

@router.post("/alert-rules", response_model=AlertRuleCreate)
def create_alert_rule(
    rule: AlertRuleCreate,
    org_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create alert rule"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    alert_rule = AlertRule(
        id=str(uuid.uuid4()),
        org_id=org_id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        environment=rule.environment,
        threshold_ms=rule.threshold_ms,
        threshold_percent=rule.threshold_percent,
        slack_webhook=rule.slack_webhook,
        slack_channel=rule.slack_channel,
        email_recipients=rule.email_recipients or [],
    )
    
    db.add(alert_rule)
    db.commit()
    return alert_rule


@router.get("/alert-rules", response_model=List[AlertRuleResponse])
def list_alert_rules(
    org_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List alert rules for organization"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    return db.query(AlertRule).filter_by(org_id=org_id).all()


# ============ Alerts ============

@router.get("/alerts", response_model=List[AlertResponse])
def list_alerts(
    org_id: str,
    active_only: bool = True,
    limit: int = 50,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List alerts for organization"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    query = db.query(Alert).filter_by(org_id=org_id)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    return query.order_by(desc(Alert.fired_at)).limit(limit).all()


# ============ Prod vs Test ============

@router.get("/prod-vs-test", response_model=List[ProdVsTestComparisonResponse])
def list_prod_vs_test_comparisons(
    org_id: str,
    regression_only: bool = False,
    limit: int = 20,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get production vs test comparisons"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    query = db.query(ProdVsTestComparison).filter_by(org_id=org_id)
    
    if regression_only:
        query = query.filter_by(regression_detected=True)
    
    return query.order_by(desc(ProdVsTestComparison.comparison_date)).limit(limit).all()


@router.post("/prod-vs-test/analyze", response_model=dict)
def analyze_prod_vs_test(
    org_id: str,
    test_name: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze production vs test metrics for a test"""
    
    org = db.query(Organization).filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Get production trends
    prod_trends = db.query(QueryTrend).filter(
        QueryTrend.org_id == org_id,
        QueryTrend.environment == "production",
    ).all()
    
    # Aggregate production data
    prod_queries_data = []
    if prod_trends:
        prod_total = sum(t.count for t in prod_trends)
        prod_avg_duration = sum(t.duration_avg * t.count for t in prod_trends) / prod_total if prod_total > 0 else 0
    else:
        prod_total = 0
        prod_avg_duration = 0
    
    # Create comparison record
    comparison = ProdVsTestComparison(
        id=str(uuid.uuid4()),
        org_id=org_id,
        test_name=test_name,
        prod_query_count=prod_total,
        prod_avg_duration=prod_avg_duration,
        prod_queries=prod_queries_data,
        test_query_count=0,  # Would be filled from test data
        test_avg_duration=0,
        discrepancy="Comparison pending test data",
    )
    
    db.add(comparison)
    db.commit()
    
    return {"comparison_id": comparison.id, "status": "created"}
