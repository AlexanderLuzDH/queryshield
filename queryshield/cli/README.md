# queryshield

Command-line tool for database query performance analysis.

Analyze Django, SQLAlchemy, and FastAPI applications for N+1 queries, missing indexes, slow queries, and other performance issues.

## Installation

```bash
pip install queryshield
```

## Quick Start

```bash
# Analyze Django tests
queryshield analyze --framework django

# With API key to upload to SaaS
queryshield analyze --framework django --api-key sk_xxx

# Monitor production queries
queryshield production-monitor
```

## Features

- Multi-framework support (Django, SQLAlchemy, FastAPI)
- N+1 query detection
- EXPLAIN plan analysis
- Query budget enforcement
- SaaS integration for report storage
- Production query monitoring
- Performance regression detection
- AI-powered root cause analysis

## Configuration

Create a `queryshield.yml` in your project root:

```yaml
version: 1

# Test mode configuration
test:
  budget:
    query_count: 50
    total_time_ms: 1000
  enabled: true

# Production monitoring configuration
production:
  sample_rate: 0.01
  slow_query_threshold_ms: 500
  api_key: sk_xxx
  enabled: true
```

## Commands

- `queryshield analyze` - Analyze test queries
- `queryshield production-monitor` - Start production monitoring daemon
- `queryshield config` - Show current configuration

## Documentation

See the main [QueryShield documentation](https://queryshield.app/docs) for more information.
