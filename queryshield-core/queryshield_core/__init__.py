"""QueryShield Core Analysis Library

Shared analysis logic for all QueryShield probe packages (Django, SQLAlchemy, FastAPI, etc.)

This package contains reusable components:
- Query analysis (N+1 detection, EXPLAIN parsing, cost calculation)
- Report generation
- Budget checking
- Utility functions
"""

__version__ = "0.2.0"
__author__ = "QueryShield"
__email__ = "dev@queryshield.io"

# Analysis engines
from queryshield_core.analysis.classify import classify_n_plus_one, classify_all
from queryshield_core.analysis.explain_checks import explain_classify

# TODO: These modules need to be created
# from queryshield_core.analysis.explain_pg import (
#     explain_query as explain_query_postgres,
#     plan_has_seq_scan_with_filter,
#     plan_has_sort_without_index,
# )
# from queryshield_core.analysis.explain_mysql import explain_query as explain_query_mysql
# from queryshield_core.analysis.explain_checks import (
#     analyze_plan_missing_index,
#     analyze_plan_sort_without_index,
#     analyze_select_star_large,
# )
# from queryshield_core.analysis.cost_analysis import (
#     calculate_monthly_cost,
#     estimate_fix_time,
#     calculate_problem_cost,
#     rank_problems_by_roi,
#     generate_cost_summary,
# )

# Budget checking
# from queryshield_core.budgets import load_budgets, check_budgets

# Utilities
# from queryshield_core.utils import normalize_sql, redact_params

__all__ = [
    # Analysis
    "classify_n_plus_one",
    "classify_all",
    "explain_classify",
    # TODO: Add back when modules exist
    # "explain_query_postgres",
    # "explain_query_mysql",
    # "plan_has_seq_scan_with_filter",
    # "plan_has_sort_without_index",
    # "analyze_plan_missing_index",
    # "analyze_plan_sort_without_index",
    # "analyze_select_star_large",
    # # Cost
    # "calculate_monthly_cost",
    # "estimate_fix_time",
    # "calculate_problem_cost",
    # "rank_problems_by_roi",
    # "generate_cost_summary",
    # # Budgets
    # "load_budgets",
    # "check_budgets",
    # # Utils
    # "normalize_sql",
    # "redact_params",
]
