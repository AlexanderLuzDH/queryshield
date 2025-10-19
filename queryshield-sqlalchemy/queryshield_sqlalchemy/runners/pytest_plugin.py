"""Pytest plugin for QueryShield SQLAlchemy probe

Activate with: pytest -p queryshield_sqlalchemy.runners.pytest_plugin
"""

from typing import Any

from queryshield_sqlalchemy.probe import Recorder, install_probe


def pytest_addoption(parser):
    """Add pytest command line options"""
    parser.addoption(
        "--queryshield-engine",
        action="store",
        default=None,
        help="SQLAlchemy engine for QueryShield probe",
    )
    parser.addoption(
        "--queryshield-report",
        action="store",
        default=".queryshield/queryshield_report.json",
        help="Output path for QueryShield report",
    )


def pytest_configure(config: Any) -> None:
    """Configure pytest plugin"""
    # Store recorder in config for use in hooks
    config._queryshield_recorder = Recorder()
    config._queryshield_engine = config.getoption("--queryshield-engine")
    config._queryshield_report = config.getoption("--queryshield-report")
    
    # Start probe if engine is provided
    if config._queryshield_engine:
        config._queryshield_cm = install_probe(
            config._queryshield_engine,
            config._queryshield_recorder,
        )
        config._queryshield_cm.__enter__()


def pytest_runtest_setup(item: Any) -> None:
    """Setup for each test"""
    recorder = item.config._queryshield_recorder
    test_name = item.nodeid
    recorder.start_test(test_name)


def pytest_runtest_teardown(item: Any) -> None:
    """Teardown for each test"""
    recorder = item.config._queryshield_recorder
    test_name = item.nodeid
    recorder.end_test(test_name)


def pytest_sessionfinish(session: Any) -> None:
    """Generate report at end of session"""
    from queryshield_sqlalchemy.report import build_report, write_report
    
    recorder = session.config._queryshield_recorder
    engine = session.config._queryshield_engine
    
    if engine:
        report = build_report(recorder, engine)
        report_path = session.config._queryshield_report
        write_report(report, report_path)
        print(f"\nQueryShield report saved to {report_path}")
    
    # Clean up probe
    cm = getattr(session.config, "_queryshield_cm", None)
    if cm:
        cm.__exit__(None, None, None)
