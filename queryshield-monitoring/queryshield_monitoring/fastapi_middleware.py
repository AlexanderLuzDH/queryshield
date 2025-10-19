"""FastAPI middleware for production query monitoring"""

import time
import logging
from typing import Callable, Any
from sqlalchemy import event
from sqlalchemy.engine import Engine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .middleware import MonitoringConfig, ProductionMonitor

logger = logging.getLogger(__name__)


class QueryShieldFastAPIMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that captures and monitors database queries.
    
    Usage:
        from queryshield_monitoring import QueryShieldFastAPIMiddleware, MonitoringConfig
        
        config = MonitoringConfig.from_env()
        app.add_middleware(QueryShieldFastAPIMiddleware, config=config, engine=db_engine)
    """
    
    def __init__(self, app: Any, config: MonitoringConfig, engine: Engine):
        super().__init__(app)
        self.config = config
        self.monitor = ProductionMonitor(config)
        self._setup_engine_hooks(engine)
    
    def _setup_engine_hooks(self, engine: Engine) -> None:
        """Setup SQLAlchemy event hooks to capture queries"""
        
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Store query start time
            conn.info.setdefault("query_start_time", {})
            conn.info["query_start_time"][id(cursor)] = time.time()
        
        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Calculate duration and record
            start_time = conn.info.get("query_start_time", {}).pop(id(cursor), None)
            if start_time is not None:
                duration_ms = (time.time() - start_time) * 1000
                self.monitor.record_query(statement, duration_ms)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Middleware dispatch - pass through with monitoring active"""
        response = await call_next(request)
        return response


def install_queryshield_fastapi(app: Any, engine: Engine, config: MonitoringConfig = None) -> None:
    """
    Install QueryShield monitoring on a FastAPI app.
    
    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine to monitor
        config: MonitoringConfig instance (loaded from env if not provided)
    """
    if config is None:
        config = MonitoringConfig.from_env()
    
    if not config.api_key:
        logger.warning("QUERYSHIELD_API_KEY not set - production monitoring disabled")
    
    app.add_middleware(QueryShieldFastAPIMiddleware, config=config, engine=engine)
    
    # Store reference for cleanup
    app.queryshield_monitor = ProductionMonitor(config)
    
    @app.on_event("shutdown")
    async def shutdown_queryshield():
        """Cleanup on app shutdown"""
        if hasattr(app, "queryshield_monitor"):
            app.queryshield_monitor.shutdown()
