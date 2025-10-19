from fnmatch import fnmatch
from typing import Any, Dict, List

import yaml


def load_budgets(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _rules_for_test(budgets: Dict[str, Any], test_name: str) -> Dict[str, Any]:
    rules = dict(budgets.get("defaults", {}))
    tests = budgets.get("tests", {}) or {}
    if test_name in tests:
        rules.update(tests[test_name] or {})
    return rules


def _problem_ignored(p: Dict[str, Any], ignore_rules: List[str]) -> bool:
    pid = p.get("id") or ""
    ptype = p.get("type") or ""
    for pat in ignore_rules or []:
        if fnmatch(pid, pat) or fnmatch(ptype, pat):
            return True
    return False


def check_budgets(budgets: Dict[str, Any], report: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    forb_types = set(
        [(x.get("type") if isinstance(x, dict) else x) for x in (budgets.get("defaults", {}).get("forbid", []) or [])]
    )
    for t in report.get("tests", []) or []:
        name = t.get("name", "<unknown>")
        rules = _rules_for_test(budgets, name)
        ignore_rules = rules.get("ignore", []) or []
        if "max_queries" in rules and t.get("queries_total", 0) > rules["max_queries"]:
            violations.append(f"{name}: queries_total {t.get('queries_total')} > max_queries {rules['max_queries']}")
        if "max_total_db_time_ms" in rules and t.get("duration_ms", 0) > rules["max_total_db_time_ms"]:
            violations.append(
                f"{name}: duration_ms {t.get('duration_ms')} > max_total_db_time_ms {rules['max_total_db_time_ms']}"
            )
        if forb_types:
            for p in t.get("problems", []) or []:
                if _problem_ignored(p, ignore_rules):
                    continue
                if p.get("type") in forb_types:
                    violations.append(f"{name}: forbidden problem {p.get('type')} detected (id={p.get('id')})")
    return violations
