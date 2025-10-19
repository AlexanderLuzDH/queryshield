import re
from typing import Any


_re_multispace = re.compile(r"\s+")
_re_string_sq = re.compile(r"'([^']|''|\\')*'")
_re_string_dq = re.compile(r'"([^"]|\"|"")*"')
_re_numeric = re.compile(r"\b\d+(?:\.\d+)?\b")
_re_in_list = re.compile(r"IN\s*\((\s*\?(?:\s*,\s*\?)+\s*)\)", re.IGNORECASE)


def normalize_sql(sql: str) -> str:
    """Normalize SQL query for comparison and grouping.
    
    Removes dynamic values (strings, numbers) and whitespace to identify
    query patterns regardless of parameter values.
    
    Args:
        sql: Raw SQL query string
        
    Returns:
        Normalized SQL suitable for grouping
    """
    s = sql.strip()
    s = _re_string_sq.sub("?", s)
    s = _re_string_dq.sub("?", s)
    s = _re_numeric.sub("?", s)
    s = _re_in_list.sub("IN (?)", s)
    s = _re_multispace.sub(" ", s)
    return s


def _shape(v: Any) -> Any:
    """Recursively get type shape of a value (for parameter redaction)."""
    t = type(v).__name__
    if isinstance(v, (list, tuple)):
        return [_shape(x) for x in list(v)[:5]] + (["..."] if len(v) > 5 else [])
    if isinstance(v, dict):
        return {str(k): _shape(v[k]) for k in list(v.keys())[:10]}
    if v is None:
        return "None"
    return t


def redact_params(params: Any) -> Any:
    """Redact query parameters for safe logging.
    
    Replaces actual parameter values with type information only,
    removing sensitive data like passwords, tokens, etc.
    
    Args:
        params: Query parameters (dict, list, tuple, or single value)
        
    Returns:
        Type-only representation of parameters
    """
    return _shape(params)
