import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from django import get_version as django_version
from django.db import connection, connections

from .capture import QueryEvent, Recorder
from .classify import classify_all
from .explain_pg import explain_query as explain_query_pg
from .explain_mysql import explain_query as explain_query_mysql
from .explain_checks import explain_classify
from .cost_analysis import generate_cost_summary
from .utils import normalize_sql, redact_params


def _get_explain_handler(vendor: str):
    """Route explain queries to the appropriate handler based on DB vendor."""
    if vendor == "postgresql":
        return explain_query_pg
    elif vendor == "mysql":
        return explain_query_mysql
    return None


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, int(0.95 * (len(s) - 1)))
    return float(s[k])


MAX_QUERIES_PER_TEST = 500
MAX_SQL_LEN = 2048


def _test_report(
    name: str,
    events: List[QueryEvent],
    *,
    nplus1_threshold: int,
    plan_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    probs, tags = classify_all(events, nplus1_threshold=nplus1_threshold)
    durations = [e.duration_ms for e in events]
    items: List[Dict[str, Any]] = []
    for i, e in enumerate(events[:MAX_QUERIES_PER_TEST]):
        items.append(
            {
                "normalized_sql": normalize_sql(e.sql)[:MAX_SQL_LEN],
                "duration_ms": e.duration_ms,
                "stack": e.stack,
                "error": e.error,
                "params": redact_params(e.params),
                "tags": tags.get(i, []),
                "db_alias": getattr(e, "db_alias", "default"),
            }
        )
    # EXPLAIN-driven problems: group by normalized SQL and attach unique problems
    if plan_map:
        seen_ids = set(p.get("id") for p in probs if isinstance(p, dict))
        for norm_sql, plan in plan_map.items():
            db_alias = None
            if events:
                db_alias = getattr(events[0], "db_alias", None)
            for p in explain_classify(norm_sql, plan, db_alias=db_alias):
                if p.get("id") not in seen_ids:
                    probs.append(p)
                    seen_ids.add(p.get("id"))
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
    *,
    mode: str = "tests",
    budgets_file: str = "queryshield.yml",
    explain: bool = False,
    explain_timeout_ms: int = 500,
    explain_max_plans: int = 50,
    nplus1_threshold: int = 5,
    run_duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = []
    vendor = getattr(connection, "vendor", "unknown")
    
    # Determine if we should run EXPLAIN based on vendor support
    do_explain = explain and vendor in ("postgresql", "mysql")
    explain_handler = _get_explain_handler(vendor) if do_explain else None
    
    # Build a plan cache keyed by (db_alias, normalized SQL), bounded by explain_max_plans
    plan_cache: Dict[Tuple[str, str], Any] = {}
    explain_elapsed_ms = 0.0
    consec_null = 0
    
    if do_explain and explain_handler:
        import time as _t
        for _tname, events in recorder.events_by_test.items():
            for e in events:
                if len(plan_cache) >= explain_max_plans:
                    break
                sql_up = e.sql.strip().upper()
                if not sql_up.startswith("SELECT"):
                    continue
                norm = normalize_sql(e.sql)
                key = (getattr(e, "db_alias", "default"), norm)
                if key in plan_cache:
                    continue
                t0 = _t.perf_counter()
                conn = connections[getattr(e, "db_alias", "default")]
                plan = explain_handler(conn, e.sql, e.params, timeout_ms=explain_timeout_ms)
                explain_elapsed_ms += (_t.perf_counter() - t0) * 1000.0
                plan_cache[key] = plan
                if plan is None:
                    consec_null += 1
                    if consec_null >= 5:
                        break
                else:
                    consec_null = 0
            if len(plan_cache) >= explain_max_plans:
                break
    
    for name, events in recorder.events_by_test.items():
        # Restrict plan_map to the normalized SQLs present in this test
        plan_map = None
        if do_explain and explain_handler:
            plan_map = {}
            for e in events:
                norm = normalize_sql(e.sql)
                key = (getattr(e, "db_alias", "default"), norm)
                if key in plan_cache:
                    plan_map[norm] = plan_cache[key]
        tests.append(
            _test_report(
                name,
                events,
                nplus1_threshold=nplus1_threshold,
                plan_map=plan_map,
            )
        )
    report = {
        "version": "1",
        "project_root": os.path.abspath(os.getcwd()),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "framework": {"name": "django", "version": django_version()},
        "db": {"vendor": getattr(connection, "vendor", "unknown"), "version": ""},
        "run": {
            "mode": mode,
            "budgets_file": budgets_file,
            "explain": do_explain,
            "explain_timeout_ms": explain_timeout_ms,
            "explain_max_plans": explain_max_plans,
            "nplus1_threshold": nplus1_threshold,
            "duration_ms": run_duration_ms,
            "explain_runtime_ms": explain_elapsed_ms,
        },
        "tests": tests,
    }
    
    # Add cost analysis to each test
    for test_report in tests:
        cost_summary = generate_cost_summary(test_report, provider="aws_rds_postgres")
        test_report["cost_analysis"] = cost_summary
    
    # Add aggregate cost analysis
    total_queries = sum(t.get("queries_total", 0) for t in tests)
    total_duration_ms = sum(t.get("duration_ms", 0) for t in tests)
    
    report["cost_analysis"] = {
        "total_queries": total_queries,
        "total_duration_ms": total_duration_ms,
        "provider": "aws_rds_postgres",
        "estimated_monthly_cost": round(
            (total_queries / 1000) * 0.25 + 25.0, 2
        ),  # AWS RDS estimate
    }
    
    return report


def write_report(report: Dict[str, Any], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
