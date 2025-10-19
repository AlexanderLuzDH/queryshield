import os
import unittest
from typing import Any, Dict

from django.conf import settings as dj_settings
from django.test.runner import DiscoverRunner

from ..capture import Recorder, install_probe
from ..report import build_report


class _InstrumentedResult(unittest.TextTestResult):
    def __init__(self, *args, recorder: Recorder, **kwargs):
        super().__init__(*args, **kwargs)
        self._recorder = recorder

    def startTest(self, test):  # noqa: N802
        name = getattr(test, "id", lambda: str(test))()
        self._recorder.start_test(name)
        super().startTest(test)

    def stopTest(self, test):  # noqa: N802
        try:
            super().stopTest(test)
        finally:
            self._recorder.end_test(getattr(test, "id", lambda: str(test))())


def _ensure_django_setup():
    import django

    if not dj_settings.configured:
        settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
        if not settings_module:
            raise RuntimeError("DJANGO_SETTINGS_MODULE is not set")
    django.setup()


def run_django_tests(
    explain: bool | None = None,
    budgets_file: str = "queryshield.yml",
    explain_timeout_ms: int = 500,
    explain_max_plans: int = 50,
    nplus1_threshold: int = 5,
) -> Dict[str, Any]:
    _ensure_django_setup()
    recorder = Recorder()
    runner = DiscoverRunner(verbosity=1)
    runner.setup_test_environment()
    old_config = runner.setup_databases()
    try:
        import time
        start = time.perf_counter()
        suite = runner.build_suite()
        test_runner = runner.test_runner(  # type: ignore[call-arg]
            verbosity=1,
            resultclass=lambda *a, **kw: _InstrumentedResult(*a, recorder=recorder, **kw),
        )
        with install_probe(recorder):
            test_runner.run(suite)
        run_duration_ms = (time.perf_counter() - start) * 1000.0
    finally:
        runner.teardown_databases(old_config)
        runner.teardown_test_environment()
    # Decide on explain default based on DB vendor
    from django.db import connection

    do_explain = explain
    if do_explain is None:
        do_explain = getattr(connection, "vendor", "") == "postgresql"
    # Build machine-readable report structure
    return build_report(
        recorder,
        mode="tests",
        budgets_file=budgets_file,
        explain=bool(do_explain),
        explain_timeout_ms=explain_timeout_ms,
        explain_max_plans=explain_max_plans,
        nplus1_threshold=nplus1_threshold,
        run_duration_ms=run_duration_ms,
    )
