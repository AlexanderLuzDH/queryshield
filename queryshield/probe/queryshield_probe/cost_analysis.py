from typing import Any, Dict, List, Optional, Tuple

from .capture import QueryEvent


# Cloud provider pricing (as of 2025)
# Prices are per million requests, per month
CLOUD_PRICING = {
    "aws_rds_postgres": {
        "description": "AWS RDS PostgreSQL (db.t4g.micro)",
        "read_cost_per_1m_queries": 0.25,  # ~$0.25 per million queries
        "monthly_base": 25.0,  # Base instance cost
    },
    "aws_rds_mysql": {
        "description": "AWS RDS MySQL (db.t4g.micro)",
        "read_cost_per_1m_queries": 0.20,
        "monthly_base": 25.0,
    },
    "gcp_cloudsql": {
        "description": "GCP Cloud SQL (db-n1-standard-1)",
        "read_cost_per_1m_queries": 0.18,
        "monthly_base": 30.0,
    },
    "digitalocean": {
        "description": "DigitalOcean Managed PostgreSQL (Basic)",
        "read_cost_per_1m_queries": 0.12,
        "monthly_base": 12.0,
    },
}

# Cost of developer time (per hour, for ROI calculation)
DEVELOPER_HOURLY_RATE = 100.0  # $100/hour


def calculate_monthly_cost(
    events: List[QueryEvent],
    provider: str = "aws_rds_postgres",
    queries_per_month: Optional[int] = None,
) -> float:
    """Calculate estimated monthly database cost based on query metrics.
    
    Args:
        events: List of QueryEvent objects from a test run
        provider: Cloud provider key (aws_rds_postgres, aws_rds_mysql, gcp_cloudsql, digitalocean)
        queries_per_month: Optional override for monthly query volume (default: extrapolate from test)
    
    Returns:
        Estimated monthly cost in USD
    """
    if provider not in CLOUD_PRICING:
        provider = "aws_rds_postgres"
    
    pricing = CLOUD_PRICING[provider]
    
    # If not provided, estimate monthly queries from test events
    # Assumption: test represents 1 minute of production traffic
    if queries_per_month is None:
        queries_in_test = len(events)
        queries_per_month = queries_in_test * 60 * 24 * 30  # Scale up to monthly
    
    # Calculate variable cost based on query volume
    variable_cost = (queries_per_month / 1_000_000) * pricing["read_cost_per_1m_queries"]
    
    # Add base infrastructure cost
    total_cost = variable_cost + pricing["monthly_base"]
    
    return round(total_cost, 2)


def estimate_fix_time(
    problem_type: str,
    problem_severity: str = "medium",
) -> float:
    """Estimate developer time needed to fix a problem (in hours).
    
    Args:
        problem_type: Type of problem (N+1, MISSING_INDEX, SORT_WITHOUT_INDEX, SELECT_STAR_LARGE)
        problem_severity: Severity level (low, medium, high)
    
    Returns:
        Estimated hours of developer time
    """
    base_times = {
        "N+1": 0.5,  # Usually quick fix: add select_related/prefetch_related
        "MISSING_INDEX": 0.25,  # Index creation is usually straightforward
        "SORT_WITHOUT_INDEX": 0.5,  # Requires understanding of query pattern
        "SELECT_STAR_LARGE": 0.25,  # Usually just narrowing column selection
        "SLOW_QUERY": 1.0,  # May require investigation
    }
    
    base_time = base_times.get(problem_type, 1.0)
    
    # Adjust based on severity
    severity_multiplier = {
        "low": 0.5,
        "medium": 1.0,
        "high": 2.0,
    }
    
    multiplier = severity_multiplier.get(problem_severity, 1.0)
    
    return base_time * multiplier


def calculate_problem_cost(
    problem: Dict[str, Any],
    events: List[QueryEvent],
    provider: str = "aws_rds_postgres",
) -> Dict[str, Any]:
    """Calculate cost impact and ROI for fixing a specific problem.
    
    Args:
        problem: Problem dict from classify_all()
        events: List of QueryEvent objects
        provider: Cloud provider
    
    Returns:
        Dict with cost_impact, fix_cost, and roi_multiplier
    """
    problem_type = problem.get("type", "UNKNOWN")
    evidence = problem.get("evidence", {})
    
    # Estimate improvement based on problem type
    improvement_estimates = {
        "N+1": 0.8,  # 80% reduction (test-specific)
        "MISSING_INDEX": 0.6,  # 60% reduction
        "SORT_WITHOUT_INDEX": 0.5,  # 50% reduction
        "SELECT_STAR_LARGE": 0.3,  # 30% reduction (smaller impact)
    }
    
    improvement_factor = improvement_estimates.get(problem_type, 0.3)
    
    # Detect severity: N+1 with 50+ queries is high severity
    severity = "medium"
    if problem_type == "N+1" and evidence.get("cluster_count", 0) > 50:
        severity = "high"
    elif evidence.get("estimated_rows", 0) > 100_000:
        severity = "high"
    
    # Calculate costs
    current_monthly_cost = calculate_monthly_cost(events, provider)
    estimated_savings = current_monthly_cost * improvement_factor
    fix_time_hours = estimate_fix_time(problem_type, severity)
    fix_cost_dollars = fix_time_hours * DEVELOPER_HOURLY_RATE
    
    # Calculate ROI
    roi_multiplier = estimated_savings / fix_cost_dollars if fix_cost_dollars > 0 else 0
    breakeven_months = (fix_cost_dollars / estimated_savings) if estimated_savings > 0 else float('inf')
    
    return {
        "problem_type": problem_type,
        "severity": severity,
        "estimated_monthly_savings": round(estimated_savings, 2),
        "estimated_fix_cost": round(fix_cost_dollars, 2),
        "roi_multiplier": round(roi_multiplier, 1),
        "breakeven_months": round(breakeven_months, 1),
        "improvement_factor": f"{int(improvement_factor * 100)}%",
    }


def rank_problems_by_roi(
    problems: List[Dict[str, Any]],
    events: List[QueryEvent],
    provider: str = "aws_rds_postgres",
    top_n: int = 10,
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Rank problems by ROI (return on investment) for fixing them.
    
    Args:
        problems: List of problem dicts from classify_all()
        events: List of QueryEvent objects
        provider: Cloud provider
        top_n: Return top N problems by ROI
    
    Returns:
        List of (problem, cost_info) tuples sorted by ROI multiplier descending
    """
    problems_with_cost = []
    
    for problem in problems:
        cost_info = calculate_problem_cost(problem, events, provider)
        problems_with_cost.append((problem, cost_info))
    
    # Sort by ROI multiplier descending, then by savings descending
    problems_with_cost.sort(
        key=lambda x: (
            -x[1]["roi_multiplier"],
            -x[1]["estimated_monthly_savings"],
        )
    )
    
    return problems_with_cost[:top_n]


def generate_cost_summary(
    test_report: Dict[str, Any],
    provider: str = "aws_rds_postgres",
) -> Dict[str, Any]:
    """Generate a cost analysis summary for a test report.
    
    Args:
        test_report: Report dict from _test_report()
        provider: Cloud provider
    
    Returns:
        Summary dict with total cost, problem costs, and top recommendations
    """
    # Recreate events from report for cost calculation
    # (In real usage, we'd pass events directly, but for the report we work with data)
    queries_total = test_report.get("queries_total", 0)
    
    # Estimate monthly cost based on query count
    estimated_monthly_cost = (queries_total / 1000) * CLOUD_PRICING[provider]["read_cost_per_1m_queries"]
    estimated_monthly_cost += CLOUD_PRICING[provider]["monthly_base"]
    
    problems = test_report.get("problems", [])
    
    # Calculate savings potential
    total_savings_potential = 0.0
    high_roi_problems = []
    
    for problem in problems:
        problem_type = problem.get("type", "UNKNOWN")
        improvement = {"N+1": 0.8, "MISSING_INDEX": 0.6, "SORT_WITHOUT_INDEX": 0.5}.get(problem_type, 0.3)
        savings = estimated_monthly_cost * improvement
        total_savings_potential += savings
        
        if savings > 5:  # Only include if >$5/month savings
            high_roi_problems.append({
                "type": problem_type,
                "monthly_savings": round(savings, 2),
                "id": problem.get("id"),
            })
    
    high_roi_problems.sort(key=lambda x: -x["monthly_savings"])
    
    return {
        "provider": provider,
        "estimated_monthly_cost": round(estimated_monthly_cost, 2),
        "total_savings_potential": round(total_savings_potential, 2),
        "payback_months": round(total_savings_potential / 100, 1) if total_savings_potential > 0 else 0,  # Assume $100/hr dev time
        "top_problems_by_savings": high_roi_problems[:5],
    }
