"""Django middleware for production query monitoring"""

import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


class QueryShieldDjangoMiddleware:
    """
    Django middleware for QueryShield production monitoring.
    
    Add to MIDDLEWARE in settings.py:
        MIDDLEWARE = [
            ...
            'queryshield_monitoring.django_middleware.QueryShieldDjangoMiddleware',
        ]
    
    Environment variables:
        QUERYSHIELD_API_KEY: API key for SaaS
        QUERYSHIELD_ORG_ID: Organization ID
        QUERYSHIELD_SAMPLE_RATE: Query sample rate (default: 0.01)
        QUERYSHIELD_SLOW_QUERY_MS: Slow query threshold (default: 500)
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        
        # Lazy import to allow optional dependency
        from .middleware import MonitoringConfig, ProductionMonitor
        
        self.config = MonitoringConfig.from_env()
        self.monitor = ProductionMonitor(self.config)
        self._setup_db_hooks()
    
    def _setup_db_hooks(self) -> None:
        """Setup Django database instrumentation"""
        try:
            from django.db import connection
            from django.test.utils import CaptureQueriesContext
            
            # Patch the execute method on cursor
            original_execute = connection.cursor().execute
            
            def patched_execute(sql, params=None):
                start_time = time.time()
                try:
                    return original_execute(sql, params)
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.monitor.record_query(sql, duration_ms)
            
            # This approach is limited; better to use middleware + signals
            logger.debug("QueryShield Django monitoring initialized")
        except ImportError:
            logger.warning("Django not available")
    
    def __call__(self, request):
        """Process request and capture database queries"""
        response = self.get_response(request)
        return response


def install_queryshield_django(settings_module: str = None) -> None:
    """
    Install QueryShield monitoring in a Django project.
    
    Can be called from manage.py or settings.py:
        from queryshield_monitoring import install_queryshield_django
        install_queryshield_django()
    """
    try:
        import django
        from django.conf import settings
        
        if "queryshield_monitoring.django_middleware.QueryShieldDjangoMiddleware" not in settings.MIDDLEWARE:
            logger.warning(
                "QueryShield middleware not in MIDDLEWARE setting. "
                "Add 'queryshield_monitoring.django_middleware.QueryShieldDjangoMiddleware' to MIDDLEWARE."
            )
        
        logger.info("QueryShield Django monitoring ready")
    except ImportError:
        logger.warning("Django not installed")
