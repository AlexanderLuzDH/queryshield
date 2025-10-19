import json
import os
import sys
from typing import Any, Dict, Optional


_warned_explain = False


def explain_query(conn, sql: str, params, timeout_ms: int = 500) -> Optional[Dict[str, Any]]:
    """Run EXPLAIN (FORMAT JSON) if vendor is PostgreSQL with a statement timeout.

    Returns the parsed plan dict (root node) or None if unsupported or on error.
    """
    if getattr(conn, "vendor", "") != "postgresql":
        return None
    try:
        # EXPLAIN FORMAT JSON returns a single row with a JSON array
        with conn.cursor() as cur:
            prev = None
            try:
                cur.execute("SHOW statement_timeout")
                prev = cur.fetchone()[0]
            except Exception:
                prev = None
            try:
                local_set = False
                try:
                    cur.execute(f"SET LOCAL statement_timeout = {int(timeout_ms)}")
                    local_set = True
                except Exception:
                    # Fallback to session-level set if LOCAL not allowed
                    cur.execute(f"SET statement_timeout TO {int(timeout_ms)}")
                cur.execute("EXPLAIN (FORMAT JSON) " + sql, params)
                row = cur.fetchone()
            finally:
                try:
                    if not local_set:
                        if prev is not None:
                            cur.execute(f"SET statement_timeout TO {prev}")
                        else:
                            cur.execute("SET statement_timeout TO DEFAULT")
                except Exception:
                    pass
        if not row:
            return None
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        plan = data[0].get("Plan") if isinstance(data, list) else data.get("Plan")
        return plan
    except Exception:  # pragma: no cover - defensive
        global _warned_explain
        if not _warned_explain and os.getenv("QUERYSHIELD_DEBUG"):
            print("QueryShield: EXPLAIN not permitted or failed; continuing without plans", file=sys.stderr)
        _warned_explain = True
        return None


def plan_has_seq_scan_with_filter(plan: Dict[str, Any]) -> bool:
    node_type = plan.get("Node Type")
    if node_type == "Seq Scan" and plan.get("Filter"):
        return True
    for child in plan.get("Plans", []) or []:
        if plan_has_seq_scan_with_filter(child):
            return True
    return False


def plan_has_sort_without_index(plan: Dict[str, Any]) -> bool:
    node_type = plan.get("Node Type")
    if node_type == "Sort" and not _has_index_scan_on_sort_key(plan):
        return True
    for child in plan.get("Plans", []) or []:
        if plan_has_sort_without_index(child):
            return True
    return False


def _has_index_scan_on_sort_key(plan: Dict[str, Any]) -> bool:
    node_type = plan.get("Node Type")
    if node_type in {"Index Scan", "Index Only Scan"}:
        return True
    for child in plan.get("Plans", []) or []:
        if _has_index_scan_on_sort_key(child):
            return True
    return False
