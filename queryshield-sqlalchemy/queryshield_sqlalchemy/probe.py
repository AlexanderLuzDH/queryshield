"""SQLAlchemy query interception and recording"""

import time
import inspect
import threading
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.engine import Engine

_local = threading.local()


class QueryEvent:
    """Represents a single query execution"""
    
    def __init__(self):
        self.sql: str = ""
        self.params: Optional[Dict[str, Any]] = None
        self.duration_ms: float = 0.0
        self.stack: List[Tuple[str, str, int]] = []
        self.error: Optional[str] = None
        self.db_vendor: str = "unknown"


def _stack_signature(skip: int = 0, depth: int = 8) -> List[Tuple[str, str, int]]:
    """Extract stack trace for query origin tracking"""
    frames = inspect.stack()[skip + 1 : skip + 1 + depth]
    out: List[Tuple[str, str, int]] = []
    for f in frames:
        fn = f.filename.replace("\\", "/")
        # Skip SQLAlchemy and site-packages
        if "/site-packages/" in fn or "sqlalchemy" in fn.lower():
            continue
        out.append((fn, f.function, f.lineno))
    return out


class Recorder:
    """Records query events organized by test"""
    
    def __init__(self):
        self._events_by_test: Dict[str, List[QueryEvent]] = {}
    
    def current_test(self) -> str:
        """Get current test name"""
        name = getattr(_local, "current_test", None)
        if not name:
            return "_run"
        return name
    
    def start_test(self, name: str) -> None:
        """Mark start of test"""
        _local.current_test = name
        self._events_by_test.setdefault(name, [])
    
    def end_test(self, name: Optional[str] = None) -> None:
        """Mark end of test"""
        if name is None:
            name = getattr(_local, "current_test", None)
        _local.current_test = None
    
    def record(self, event: QueryEvent) -> None:
        """Record a query event"""
        test_name = self.current_test()
        self._events_by_test.setdefault(test_name, []).append(event)
    
    @property
    def events_by_test(self) -> Dict[str, List[QueryEvent]]:
        """Get all recorded events organized by test"""
        return self._events_by_test


class ProbeListener:
    """SQLAlchemy event listener for query interception"""
    
    def __init__(self, recorder: Recorder):
        self.recorder = recorder
    
    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Called before query execution"""
        # Store start time on connection
        if not hasattr(cursor, "_qs_start_time"):
            cursor._qs_start_time = time.perf_counter()
    
    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Called after query execution"""
        try:
            start_time = getattr(cursor, "_qs_start_time", time.perf_counter())
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            event = QueryEvent()
            event.sql = statement
            event.params = dict(parameters) if isinstance(parameters, dict) else parameters
            event.duration_ms = duration_ms
            event.stack = _stack_signature(skip=2)
            event.db_vendor = conn.dialect.name
            
            self.recorder.record(event)
        except Exception:
            # Silently ignore recording errors
            pass
        finally:
            if hasattr(cursor, "_qs_start_time"):
                delattr(cursor, "_qs_start_time")
    
    def handle_error(self, conn, cursor, statement, parameters, context, err):
        """Called on query error"""
        try:
            event = QueryEvent()
            event.sql = statement
            event.params = dict(parameters) if isinstance(parameters, dict) else parameters
            event.duration_ms = 0.0
            event.stack = _stack_signature(skip=2)
            event.error = repr(err)
            event.db_vendor = conn.dialect.name
            
            self.recorder.record(event)
        except Exception:
            pass


@contextmanager
def install_probe(engine: Engine, recorder: Recorder):
    """Install QueryShield probe on SQLAlchemy engine.
    
    Usage:
        engine = create_engine("postgresql://...")
        recorder = Recorder()
        with install_probe(engine, recorder):
            # Run queries...
            pass
    """
    listener = ProbeListener(recorder)
    
    # Register listeners
    event.listen(engine, "before_cursor_execute", listener.before_cursor_execute)
    event.listen(engine, "after_cursor_execute", listener.after_cursor_execute)
    event.listen(engine, "dbapi_error", listener.handle_error)
    
    try:
        yield
    finally:
        # Clean up listeners
        event.remove(engine, "before_cursor_execute", listener.before_cursor_execute)
        event.remove(engine, "after_cursor_execute", listener.after_cursor_execute)
        event.remove(engine, "dbapi_error", listener.handle_error)
