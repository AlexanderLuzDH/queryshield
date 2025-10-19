"""Report generation from recorded SQLAlchemy queries"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.engine import Engine
from queryshield_core.analysis.classify import classify_all
from queryshield_core.analysis.cost_analysis import generate_cost_summary
from queryshield_core.utils import normalize_sql, redact_params

from queryshield_sqlalchemy.probe import Recorder


def _p95(values: List[float]) -> float:
    """Calculate 95th percentile"""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, int(0.95 * (len(s) - 1)))
    return float(s[k])


MAX_QUERIES_PER_TEST = 500
MAX_SQL_LEN = 2048


def _test_report(
    name: str,
    events: List[Dict[str, Any]],
    *,
    nplus1_threshold: int,
) -> Dict[str, Any]:
    """Generate report for a single test"""
    probs, tags = classify_all(events, nplus1_threshold=nplus1_threshold)
    durations = [e.get("duration_ms", 0) for e in events]
    
    items: List[Dict[str, Any]] = []
    for i, e in enumerate(events[:MAX_QUERIES_PER_TEST]):
        items.append(
            {
                "normalized_sql": normalize_sql(e.get("sql", ""))[:MAX_SQL_LEN],
                "duration_ms": e.get("duration_ms", 0),
                "stack": e.get("stack", []),
                "error": e.get("error"),
                "params": redact_params(e.get("params")),
                "tags": tags.get(i, []),
                "db_vendor": e.get("db_vendor", "unknown"),
            }
        )
    
    return {
        "name": name,
        "duration_ms": sum(durations),
        "queries_total": len(events),
        "queries_p95_ms": _p95(durations),
        "problems": probs,
        "queries": items,
    }


def build_report(
    recorder: Recorder,
    engine: Engine,
    *,
    mode: str = "tests",
    nplus1_threshold: int = 5,
    run_duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Build comprehensive report from recorded events"""
    
    tests: List[Dict[str, Any]] = []
    vendor = engine.dialect.name
    
    for name, raw_events in recorder.events_by_test.items():
        # Convert QueryEvent objects to dicts
        events = [
            {
                "sql": e.sql,
                "params": e.params,
                "duration_ms": e.duration_ms,
                "stack": e.stack,
                "error": e.error,
                "db_vendor": e.db_vendor,
            }
            for e in raw_events
        ]
        
        test_report = _test_report(name, events, nplus1_threshold=nplus1_threshold)
        
        # Add cost analysis
        test_report["cost_analysis"] = generate_cost_summary(test_report, provider="aws_rds_postgres")
        
        tests.append(test_report)
    
    # Build report structure
    total_queries = sum(t.get("queries_total", 0) for t in tests)
    total_duration_ms = sum(t.get("duration_ms", 0) for t in tests)
    
    report = {
        "version": "1",
        "project_root": os.path.abspath(os.getcwd()),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "framework": {"name": "sqlalchemy", "version": "2.0+"},
        "db": {"vendor": vendor, "version": ""},
        "run": {
            "mode": mode,
            "explain": False,  # SQLAlchemy doesn't have built-in EXPLAIN support yet
            "nplus1_threshold": nplus1_threshold,
            "duration_ms": run_duration_ms,
        },
        "tests": tests,
        "cost_analysis": {
            "total_queries": total_queries,
            "total_duration_ms": total_duration_ms,
            "provider": "aws_rds_postgres",
            "estimated_monthly_cost": round((total_queries / 1000) * 0.25 + 25.0, 2),
        },
    }
    
    return report


def write_report(report: Dict[str, Any], output_path: str) -> None:
    """Write report to JSON file"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
