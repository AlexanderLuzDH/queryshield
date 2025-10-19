import json
from typing import Any, Dict, Optional


def explain_query(conn, sql: str, params, timeout_ms: int = 500) -> Optional[Dict[str, Any]]:
    """Run EXPLAIN FORMAT JSON for MySQL queries.
    
    Requires MySQL 8.0+ with JSON support.
    Returns the parsed plan dict or None if unsupported or on error.
    """
    if getattr(conn, "vendor", "") != "mysql":
        return None
    
    try:
        with conn.cursor() as cur:
            try:
                # MySQL doesn't support per-statement timeout directly,
                # but we can use max_execution_time optimizer hint (MySQL 5.7.7+)
                explain_sql = f"/*+ MAX_EXECUTION_TIME({int(timeout_ms)}) */ EXPLAIN FORMAT=JSON {sql}"
                cur.execute(explain_sql, params)
                row = cur.fetchone()
            except Exception:
                # Fallback: try without timeout hint if not supported
                explain_sql = f"EXPLAIN FORMAT=JSON {sql}"
                cur.execute(explain_sql, params)
                row = cur.fetchone()
        
        if not row:
            return None
        
        # MySQL EXPLAIN FORMAT=JSON returns a single string column
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        
        # MySQL structure: {"query_block": {...}} at top level
        plan = data.get("query_block") or data
        return plan
    except Exception:
        return None
