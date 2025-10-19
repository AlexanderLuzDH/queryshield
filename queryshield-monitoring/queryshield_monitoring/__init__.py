"""QueryShield production monitoring - capture queries from running apps"""

from .middleware import (
    QueryMetric,
    QuerySampler,
    QueryBatcher,
    SaaSUploader,
    MonitoringConfig,
    ProductionMonitor,
)
from .fastapi_middleware import QueryShieldFastAPIMiddleware, install_queryshield_fastapi
from .django_middleware import QueryShieldDjangoMiddleware, install_queryshield_django

__version__ = "0.2.0"

__all__ = [
    # Core classes
    "QueryMetric",
    "QuerySampler",
    "QueryBatcher",
    "SaaSUploader",
    "MonitoringConfig",
    "ProductionMonitor",
    # FastAPI
    "QueryShieldFastAPIMiddleware",
    "install_queryshield_fastapi",
    # Django
    "QueryShieldDjangoMiddleware",
    "install_queryshield_django",
]
