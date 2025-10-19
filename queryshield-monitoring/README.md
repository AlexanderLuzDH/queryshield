# queryshield-monitoring

Production database query monitoring middleware for QueryShield.

Monitor real-world database query performance in FastAPI and Django applications with minimal overhead.

## Features

- Low-overhead query sampling (configurable rate)
- Batch upload to SaaS backend
- Performance regression detection
- Slow query alerting
- Integration with FastAPI middleware
- Integration with Django middleware
- Slack notifications

## Installation

```bash
pip install queryshield-monitoring
```

## Usage

### FastAPI

```python
from fastapi import FastAPI
from queryshield_monitoring import QueryShieldMiddleware

app = FastAPI()

app.add_middleware(
    QueryShieldMiddleware,
    api_key="sk_...",
    sample_rate=0.01,
    slow_query_threshold_ms=500
)
```

### Django

```python
# settings.py
MIDDLEWARE = [
    'queryshield_monitoring.middleware.QueryShieldMiddleware',
]

QUERYSHIELD = {
    'API_KEY': 'sk_...',
    'SAMPLE_RATE': 0.01,
    'SLOW_QUERY_THRESHOLD_MS': 500,
}
```

## Documentation

See the main [QueryShield documentation](https://queryshield.app/docs) for more information.
