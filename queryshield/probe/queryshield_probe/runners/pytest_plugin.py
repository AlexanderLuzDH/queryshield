"""Optional pytest plugin hook for installing the probe.

Activate with: pytest -p queryshield_probe.runners.pytest_plugin
"""
from typing import Any

from ..capture import Recorder, install_probe


def pytest_sessionstart(session: Any) -> None:  # pragma: no cover - optional runtime
    recorder = Recorder()
    session.config._queryshield_recorder = recorder  # type: ignore[attr-defined]
    session.config._queryshield_cm = install_probe(recorder)  # type: ignore[attr-defined]
    session.config._queryshield_cm.__enter__()  # type: ignore[attr-defined]


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:  # pragma: no cover - optional runtime
    cm = getattr(session.config, "_queryshield_cm", None)
    if cm is not None:
        cm.__exit__(None, None, None)

