import inspect
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

from django.db import connection


_local = threading.local()


class QueryEvent:
    __slots__ = (
        "sql",
        "params",
        "duration_ms",
        "many",
        "stack",
        "error",
        "db_alias",
        "db_vendor",
    )

    def __init__(self) -> None:
        self.sql: str = ""
        self.params = None
        self.duration_ms: float = 0.0
        self.many: bool = False
        self.stack: List[Tuple[str, str, int]] = []
        self.error: Optional[str] = None
        self.db_alias: str = "default"
        self.db_vendor: str = "unknown"


def _stack_signature(skip: int = 0, depth: int = 8) -> List[Tuple[str, str, int]]:
    frames = inspect.stack()[skip + 1 : skip + 1 + depth]
    out: List[Tuple[str, str, int]] = []
    for f in frames:
        fn = f.filename.replace("\\", "/")
        if "/site-packages/" in fn or "python" in fn and "lib" in fn:
            continue
        out.append((fn, f.function, f.lineno))
    return out


class Recorder:
    def __init__(self) -> None:
        self._events_by_test: Dict[str, List[QueryEvent]] = {}

    def current_test(self) -> str:
        name = getattr(_local, "current_test", None)
        if not name:
            return "_run"
        return name

    def start_test(self, name: str) -> None:
        _local.current_test = name
        self._events_by_test.setdefault(name, [])

    def end_test(self, name: Optional[str] = None) -> None:
        if name is None:
            name = getattr(_local, "current_test", None)
        _local.current_test = None

    def record(self, ev: QueryEvent) -> None:
        name = self.current_test()
        self._events_by_test.setdefault(name, []).append(ev)

    @property
    def events_by_test(self) -> Dict[str, List[QueryEvent]]:
        return self._events_by_test


class ProbeWrapper:
    def __init__(self, recorder: Recorder):
        self.recorder = recorder

    def __call__(self, execute, sql, params, many, context):
        start = time.perf_counter()
        err = None
        try:
            return execute(sql, params, many, context)
        except Exception as e:  # pragma: no cover - pass-through
            err = repr(e)
            raise
        finally:
            ev = QueryEvent()
            ev.sql = sql
            ev.params = params
            ev.duration_ms = (time.perf_counter() - start) * 1000.0
            ev.many = bool(many)
            ev.stack = _stack_signature(skip=1)
            ev.error = err
            # Attempt to capture DB alias/vendor from context
            conn = None
            try:
                if isinstance(context, dict):
                    conn = context.get("connection")
                else:
                    conn = getattr(context, "connection", None)
            except Exception:
                conn = None
            if conn is not None:
                ev.db_alias = getattr(conn, "alias", ev.db_alias)
                ev.db_vendor = getattr(conn, "vendor", ev.db_vendor)
            self.recorder.record(ev)


@contextmanager
def install_probe(recorder: Recorder):
    """Install the Django execute_wrapper probe for the current thread.

    Usage:
        with install_probe(recorder):
            ... run code/tests ...
    """
    with connection.execute_wrapper(ProbeWrapper(recorder)):
        yield
