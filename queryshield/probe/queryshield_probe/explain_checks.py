from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .explain_pg import plan_has_seq_scan_with_filter, plan_has_sort_without_index
from .utils import normalize_sql

try:
    from django.apps import apps as _django_apps  # type: ignore
except Exception:  # pragma: no cover - optional
    _django_apps = None


LARGE_ROWS_THRESHOLD = 10_000


_re_where_eq = re.compile(r"\b([A-Za-z_][A-Za-z0-9_\.\"]*)\s*=\s*\$?\d+|\?")
_re_select_star = re.compile(r"^\s*SELECT\s+\*\s+FROM\s", re.IGNORECASE)


def _hash_id(*parts: str) -> str:
    h = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:8]
    return h


def _collect_nodes(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = [plan]
    for ch in plan.get("Plans", []) or []:
        out.extend(_collect_nodes(ch))
    return out


def _estimated_rows(plan: Dict[str, Any]) -> int:
    # EXPLAIN JSON uses 'Plan Rows' for estimates
    return int(plan.get("Plan Rows") or plan.get("Rows") or 0)


def _filter_columns_text(filter_text: Optional[str]) -> List[str]:
    if not filter_text:
        return []
    cols = []
    for m in _re_where_eq.finditer(filter_text):
        col = m.group(1)
        if col:
            # normalize potential quoted names
            cols.append(col.strip('"'))
    return cols


def _qident(name: str) -> str:
    q = name.replace('"', '""')
    return f'"{q}"'


def _qpath(parts: List[str]) -> str:
    return ".".join(_qident(p) for p in parts if p)


def _quote_colspec(spec: str) -> str:
    s = spec.strip()
    if not s:
        return s
    parts = s.split()
    head = parts[0]
    rest = " ".join(parts[1:])
    if "." in head:
        head_q = _qpath([p for p in head.split(".") if p])
    else:
        head_q = _qident(head)
    return f"{head_q}{(' ' + rest) if rest else ''}"


def _orm_fields_for_table(table: Optional[str]) -> Optional[List[str]]:
    if not table or _django_apps is None:
        return None
    try:
        for model in _django_apps.get_models():
            if getattr(model._meta, "db_table", None) == table:
                names = [f.attname for f in model._meta.concrete_fields]
                return names
    except Exception:
        return None
    return None


def analyze_plan_missing_index(sql: str, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not plan_has_seq_scan_with_filter(plan):
        return None
    nodes = _collect_nodes(plan)
    # Find first Seq Scan with Filter and large estimate
    for n in nodes:
        if n.get("Node Type") == "Seq Scan" and n.get("Filter"):
            rows = _estimated_rows(n)
            if rows >= LARGE_ROWS_THRESHOLD:
                relation = n.get("Relation Name") or n.get("Alias") or "<table>"
                schema = n.get("Schema") or "public"
                cols = _filter_columns_text(n.get("Filter"))
                columns = cols or ["<column>"]
                ddl_cols = ", ".join(_quote_colspec(c) for c in columns)
                idx_name = f"idx_{relation}_{_hash_id(''.join(columns))}"
                ddl = (
                    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_qident(idx_name)} "
                    f"ON {_qpath([schema, relation])}({ddl_cols});"
                )
                suggestion = {
                    "kind": "create_index",
                    "args": {"schema": schema, "table": relation, "columns": columns},
                    "ddl": ddl,
                }
                pid = f"explain:missing_index:{_hash_id(normalize_sql(sql))}"
                return {
                    "id": pid,
                    "type": "MISSING_INDEX",
                    "evidence": {
                        "schema": schema,
                        "relation": relation,
                        "estimated_rows": rows,
                        "filter": n.get("Filter"),
                    },
                    "suggestion": suggestion,
                    "explain": {"node": "Seq Scan"},
                }
    return None


def analyze_plan_sort_without_index(sql: str, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not plan_has_sort_without_index(plan):
        return None
    # Find Sort node and propose composite index
    nodes = _collect_nodes(plan)
    for n in nodes:
        if n.get("Node Type") == "Sort":
            keys = n.get("Sort Key") or []
            # naive: prefix with equality filters extracted from a sibling/child node if any
            eq_cols: List[str] = []
            # Walk children for Filter columns
            for ch in n.get("Plans", []) or []:
                eq_cols.extend(_filter_columns_text(ch.get("Filter")))
            cols = eq_cols + keys
            ddl_cols = ", ".join(_quote_colspec(c) for c in (cols or ["<columns>"]))
            idx_name = f"idx_sort_{_hash_id(''.join(cols))}"
            # Try to find the underlying relation name from descendants
            rel = None
            schema = None
            for ch in _collect_nodes(n):
                rel = ch.get("Relation Name") or ch.get("Alias") or rel
                schema = ch.get("Schema") or schema
            table = rel or "<table>"
            schema = schema or "public"
            ddl = (
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_qident(idx_name)} "
                f"ON {_qpath([schema, table])}({ddl_cols});"
            )
            pid = f"explain:sort_without_index:{_hash_id(normalize_sql(sql))}"
            return {
                "id": pid,
                "type": "SORT_WITHOUT_INDEX",
                "evidence": {"sort_keys": keys},
                "suggestion": {
                    "kind": "create_index",
                    "args": {"schema": schema, "table": table, "columns": cols or ["<columns>"]},
                    "ddl": ddl,
                },
                "explain": {"node": "Sort"},
            }
    return None


def analyze_select_star_large(sql: str, plan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not _re_select_star.search(sql):
        return None
    est_rows = 0
    relation = None
    if plan:
        nodes = _collect_nodes(plan)
        for n in nodes:
            if n.get("Node Type") in ("Seq Scan", "Index Scan", "Index Only Scan", "Bitmap Heap Scan"):
                est_rows = max(est_rows, _estimated_rows(n))
                relation = relation or n.get("Relation Name")
    if est_rows >= LARGE_ROWS_THRESHOLD:
        pid = f"explain:select_star_large:{_hash_id(normalize_sql(sql))}"
        fields = _orm_fields_for_table(relation)
        snippet = None
        if fields:
            small = fields[:6]
            snippet = f".only({', '.join(repr(f) for f in small)})"
        return {
            "id": pid,
            "type": "SELECT_STAR_LARGE",
            "evidence": {"estimated_rows": est_rows, "relation": relation},
            "suggestion": {"kind": "avoid_select_star", "args": {"use": snippet or ".only() or explicit fields"}},
            "explain": {"node": "*"},
        }
    return None


def explain_classify(sql: str, plan: Optional[Dict[str, Any]], db_alias: Optional[str] = None) -> List[Dict[str, Any]]:
    problems: List[Dict[str, Any]] = []
    if not plan:
        # still allow select * detection even without plan
        p = analyze_select_star_large(sql, plan)
        if p:
            if db_alias:
                p["db_alias"] = db_alias
            problems.append(p)
        return problems
    for fn in (analyze_plan_missing_index, analyze_plan_sort_without_index):
        p = fn(sql, plan)
        if p:
            if db_alias:
                p["db_alias"] = db_alias
            problems.append(p)
    p3 = analyze_select_star_large(sql, plan)
    if p3:
        if db_alias:
            p3["db_alias"] = db_alias
        problems.append(p3)
    return problems
