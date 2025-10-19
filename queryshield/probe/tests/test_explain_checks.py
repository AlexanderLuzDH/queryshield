import unittest

from queryshield_probe.explain_checks import (
    analyze_plan_missing_index,
    analyze_plan_sort_without_index,
    analyze_select_star_large,
)
from queryshield_probe.report import _get_explain_handler


class ExplainChecksTest(unittest.TestCase):
    def test_missing_index(self):
        plan = {
            "Node Type": "Seq Scan",
            "Relation Name": "books",
            "Filter": "(author_id = $1)",
            "Plan Rows": 20000,
        }
        p = analyze_plan_missing_index("SELECT * FROM books WHERE author_id = $1", plan)
        assert p and p["type"] == "MISSING_INDEX"
        assert p["suggestion"]["kind"] == "create_index"

    def test_sort_without_index(self):
        plan = {
            "Node Type": "Sort",
            "Sort Key": ["created_at DESC"],
            "Plans": [
                {"Node Type": "Seq Scan", "Relation Name": "books", "Filter": "(author_id = $1)", "Plan Rows": 5000}
            ],
        }
        p = analyze_plan_sort_without_index("SELECT * FROM books WHERE author_id=$1 ORDER BY created_at DESC", plan)
        assert p and p["type"] == "SORT_WITHOUT_INDEX"
        assert p["suggestion"]["kind"] == "create_index"

    def test_select_star_large(self):
        plan = {"Node Type": "Seq Scan", "Relation Name": "books", "Plan Rows": 20000}
        p = analyze_select_star_large("SELECT * FROM books", plan)
        assert p and p["type"] == "SELECT_STAR_LARGE"
        assert p["suggestion"]["kind"] == "avoid_select_star"


class VendorDetectionTest(unittest.TestCase):
    def test_get_explain_handler_postgresql(self):
        handler = _get_explain_handler("postgresql")
        assert handler is not None
        assert handler.__module__.endswith("explain_pg")

    def test_get_explain_handler_mysql(self):
        handler = _get_explain_handler("mysql")
        assert handler is not None
        assert handler.__module__.endswith("explain_mysql")

    def test_get_explain_handler_sqlite(self):
        handler = _get_explain_handler("sqlite")
        assert handler is None

    def test_get_explain_handler_unknown(self):
        handler = _get_explain_handler("unknown")
        assert handler is None


if __name__ == "__main__":
    unittest.main()

