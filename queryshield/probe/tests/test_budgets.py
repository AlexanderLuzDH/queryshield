import json
import os
import tempfile
import unittest

from queryshield_probe.budgets import check_budgets
from queryshield_probe.cost_analysis import (
    calculate_monthly_cost,
    estimate_fix_time,
    generate_cost_summary,
)
from queryshield_probe.capture import QueryEvent


class BudgetsTests(unittest.TestCase):
    def test_ignore_by_type_and_id(self):
        budgets = {
            "defaults": {"forbid": [{"type": "N+1"}]},
            "tests": {
                "t": {"ignore": ["N+1", "explain:select_star_large:*"]}
            },
        }
        report = {"tests": [{"name": "t", "queries_total": 1, "problems": [
            {"id": "explain:select_star_large:abc", "type": "SELECT_STAR_LARGE"},
            {"id": "n+1:file.py:10", "type": "N+1"}
        ]}]}
        violations = check_budgets(budgets, report)
        assert not violations

    def test_caps_truncate_queries(self):
        # Indirectly validate by constructing a report via private function
        from queryshield_probe.report import _test_report
        from queryshield_probe.capture import QueryEvent
        evs = []
        for i in range(600):
            e = QueryEvent()
            e.sql = f"SELECT {i}"
            e.duration_ms = 1.0
            evs.append(e)
        rep = _test_report("t", evs, nplus1_threshold=999, plan_map=None)
        assert rep["queries_total"] == 600
        assert len(rep["queries"]) == 500


class ExitCodesTests(unittest.TestCase):
    def test_budget_check_invalid_config_exit_3(self):
        from typer.testing import CliRunner
        from queryshield_cli.main import app
        runner = CliRunner()
        r = runner.invoke(app, ["budget-check", "--budgets", "no-such.yml"])  # type: ignore
        assert r.exit_code == 3

    def test_budget_check_violations_exit_2(self):
        from typer.testing import CliRunner
        from queryshield_cli.main import app
        with tempfile.TemporaryDirectory() as td:
            budgets = os.path.join(td, "b.yml")
            report = os.path.join(td, "r.json")
            with open(budgets, "w") as f:
                f.write("defaults:\n  max_queries: 0\n")
            with open(report, "w") as f:
                json.dump({"tests": [{"name": "t", "queries_total": 1, "problems": []}]}, f)
            runner = CliRunner()
            r = runner.invoke(app, ["budget-check", "--budgets", budgets, "--report", report])  # type: ignore
            assert r.exit_code == 2

    def test_budget_check_ok_exit_0(self):
        from typer.testing import CliRunner
        from queryshield_cli.main import app
        import tempfile, os, json
        with tempfile.TemporaryDirectory() as td:
            budgets = os.path.join(td, "b.yml")
            report = os.path.join(td, "r.json")
            with open(budgets, "w") as f:
                f.write("defaults:\n  max_queries: 5\n")
            with open(report, "w") as f:
                json.dump({"tests": [{"name": "t", "queries_total": 1, "duration_ms": 1, "problems": []}]}, f)
            runner = CliRunner()
            r = runner.invoke(app, ["budget-check", "--budgets", budgets, "--report", report])
            assert r.exit_code == 0

    def test_analyze_runtime_error_exit_1(self):
        # No DJANGO_SETTINGS_MODULE -> runtime error -> exit 1
        from typer.testing import CliRunner
        from queryshield_cli.main import app
        runner = CliRunner()
        r = runner.invoke(app, ["analyze"])  # type: ignore
        assert r.exit_code == 1 or r.exit_code == 2  # In CI w/o Django tests, 1 expected


class CostAnalysisTests(unittest.TestCase):
    def test_calculate_monthly_cost_basic(self):
        events = [QueryEvent() for _ in range(100)]
        cost = calculate_monthly_cost(events, provider="aws_rds_postgres")
        # 100 queries in test -> 4.32M queries/month at $0.25 per million + $25 base
        assert cost > 25.0  # At least base cost
        assert cost < 50.0  # Shouldn't be huge for 100 queries

    def test_estimate_fix_time_n_plus_one(self):
        time_low = estimate_fix_time("N+1", "low")
        time_high = estimate_fix_time("N+1", "high")
        assert time_high > time_low
        assert time_low == 0.25  # 0.5 * 0.5
        assert time_high == 1.0  # 0.5 * 2.0

    def test_estimate_fix_time_missing_index(self):
        time = estimate_fix_time("MISSING_INDEX", "medium")
        assert time == 0.25

    def test_generate_cost_summary(self):
        test_report = {
            "queries_total": 50,
            "problems": [
                {"type": "N+1", "id": "n+1:1"}
            ]
        }
        summary = generate_cost_summary(test_report, provider="aws_rds_postgres")
        assert summary["provider"] == "aws_rds_postgres"
        assert summary["estimated_monthly_cost"] > 0
        assert summary["total_savings_potential"] > 0


if __name__ == "__main__":
    unittest.main()
