# QueryShield Production Monitoring

Complete guide to monitoring database queries in your production applications.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [CLI Commands](#cli-commands)
5. [Deployment](#deployment)
6. [Examples](#examples)
7. [Troubleshooting](#troubleshooting)

## Overview

QueryShield Production Monitoring captures real-world database query performance from your running applications. With intelligent sampling (default 1%), you can monitor production without performance impact.

### Key Features

✅ **Zero Overhead** - 1% sampling captures statistical patterns  
✅ **Automatic Alerts** - Detect slow queries and regressions  
✅ **SaaS Dashboard** - Visualize production metrics over time  
✅ **Prod vs Test** - Compare production queries to test expectations  
✅ **Multi-Environment** - Monitor production, staging, dev separately  

### Architecture

```
Your Production App
    ↓
queryshield-monitoring middleware
    ↓ (1% of requests)
Query Sampler
    ↓ (every 100 queries or 30 seconds)
Query Batcher
    ↓
SaaS Backend
    ↓
Dashboard + Alerts
```

## Installation

### 1. Install Package

```bash
pip install queryshield-monitoring
```

### 2. Add to Your App

#### FastAPI

```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from queryshield_monitoring import install_queryshield_fastapi, MonitoringConfig

app = FastAPI()
engine = create_engine("postgresql://...")

# Load config from environment
config = MonitoringConfig.from_env()

# Install monitoring
install_queryshield_fastapi(app, engine, config)
```

#### Django

Add to `settings.py`:

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'queryshield_monitoring.django_middleware.QueryShieldDjangoMiddleware',
]

# Set environment variables:
# QUERYSHIELD_API_KEY=sk_xxx
# QUERYSHIELD_ORG_ID=org_123
```

## Configuration

### Environment Variables

Set these before starting your app:

```bash
# Required
export QUERYSHIELD_API_KEY=sk_live_xxx
export QUERYSHIELD_ORG_ID=org_123

# Optional (with defaults)
export QUERYSHIELD_API_URL=https://api.queryshield.app
export QUERYSHIELD_ENV=production
export QUERYSHIELD_SAMPLE_RATE=0.01           # 1%
export QUERYSHIELD_SLOW_QUERY_MS=500
export QUERYSHIELD_BATCH_SIZE=100
export QUERYSHIELD_BATCH_TIMEOUT=30
export QUERYSHIELD_ENABLED=true
```

### Configuration File (queryshield.yml)

```yaml
production:
  api_key: ${QUERYSHIELD_API_KEY}    # Use env var
  org_id: ${QUERYSHIELD_ORG_ID}
  environment: production
  
  # Sampling (1 query out of 100)
  sample_rate: 0.01
  
  # Flag queries slower than 500ms
  slow_query_threshold_ms: 500
  
  # Upload 100 queries or after 30 seconds
  batch_size: 100
  batch_timeout_seconds: 30
  
  enabled: true
```

### Configuration Priority

1. **Environment Variables** (highest priority)
2. **queryshield.yml** 
3. **Defaults** (lowest priority)

## CLI Commands

### Start Monitoring

Start the monitoring daemon:

```bash
queryshield production-monitor start
```

With custom config:

```bash
queryshield production-monitor start --config prod.yml
```

### Check Status

View current configuration:

```bash
queryshield production-monitor status
```

Output:
```
Production Monitoring Status

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting                     ┃ Value               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
┃ Enabled                     ┃ ✅ Yes              ┃
┃ API URL                     ┃ https://api...      ┃
┃ API Key                     ┃ sk_live_***         ┃
┃ Organization                ┃ org_123             ┃
┃ Sample Rate                 ┃ 1.0%                ┃
┃ Slow Query Threshold        ┃ 500ms               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━┛

✅ Connected to SaaS backend
```

### Test Configuration

Send test queries to verify setup:

```bash
queryshield production-monitor test
```

### Validate Configuration

Check for config errors:

```bash
queryshield production-monitor validate
```

### Show Example Config

Display template configuration:

```bash
queryshield production-monitor config-example
```

## Deployment

### Docker

Add to your Dockerfile:

```dockerfile
RUN pip install queryshield-monitoring

# Environment variables set via docker run or docker-compose
ENV QUERYSHIELD_API_KEY=sk_xxx
ENV QUERYSHIELD_ORG_ID=org_123
ENV QUERYSHIELD_SAMPLE_RATE=0.01
```

### Docker Compose

```yaml
services:
  app:
    build: .
    environment:
      QUERYSHIELD_API_KEY: ${QUERYSHIELD_API_KEY}
      QUERYSHIELD_ORG_ID: ${QUERYSHIELD_ORG_ID}
      QUERYSHIELD_SAMPLE_RATE: 0.01
      QUERYSHIELD_SLOW_QUERY_MS: 500
```

### Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: queryshield-config
data:
  QUERYSHIELD_SAMPLE_RATE: "0.01"
  QUERYSHIELD_SLOW_QUERY_MS: "500"
---
apiVersion: v1
kind: Secret
metadata:
  name: queryshield-secrets
type: Opaque
stringData:
  QUERYSHIELD_API_KEY: sk_live_xxx
  QUERYSHIELD_ORG_ID: org_123
```

### Systemd Service (Linux)

Create `/etc/systemd/system/queryshield.service`:

```ini
[Unit]
Description=QueryShield Production Monitoring
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/myapp
Environment="QUERYSHIELD_API_KEY=sk_live_xxx"
Environment="QUERYSHIELD_ORG_ID=org_123"
ExecStart=/usr/local/bin/queryshield production-monitor start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable queryshield
sudo systemctl start queryshield
sudo systemctl status queryshield
```

## Examples

### Example 1: FastAPI + PostgreSQL

```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from queryshield_monitoring import install_queryshield_fastapi

app = FastAPI()

# Create engine
engine = create_engine(
    "postgresql://user:pass@localhost/mydb"
)

# Install monitoring (reads QUERYSHIELD_* env vars)
install_queryshield_fastapi(app, engine)

@app.get("/users")
def get_users():
    # Queries here will be monitored
    pass
```

### Example 2: Django with queryshield.yml

```python
# settings.py
MIDDLEWARE = [
    'queryshield_monitoring.django_middleware.QueryShieldDjangoMiddleware',
]
```

```yaml
# queryshield.yml
production:
  api_key: ${QUERYSHIELD_API_KEY}
  org_id: ${QUERYSHIELD_ORG_ID}
  sample_rate: 0.01
  slow_query_threshold_ms: 500
```

### Example 3: High-Traffic App (0.1% sampling)

For apps with >1M queries/hour, reduce overhead:

```bash
export QUERYSHIELD_SAMPLE_RATE=0.001   # 0.1%
export QUERYSHIELD_BATCH_SIZE=1000     # Larger batches
export QUERYSHIELD_BATCH_TIMEOUT=60    # Longer timeouts
```

### Example 4: Staging Environment with Prod Comparison

```yaml
production:
  api_key: ${QUERYSHIELD_API_KEY}
  org_id: ${QUERYSHIELD_ORG_ID}
  environment: staging          # Different from production
  sample_rate: 0.1              # 10% on staging (higher for testing)
  slow_query_threshold_ms: 1000
```

## Troubleshooting

### Queries Not Being Captured

**Problem**: No queries showing in SaaS dashboard

**Solution**:

1. Check credentials:
```bash
queryshield production-monitor validate
```

2. Enable debug logging:
```bash
queryshield production-monitor start --log-level debug
```

3. Test with sample queries:
```bash
queryshield production-monitor test
```

### High Upload Failures

**Problem**: "Connection failed" errors in logs

**Causes**:
- Network connectivity issue
- Invalid API key
- SaaS backend down

**Solution**:
```bash
# Check connectivity
queryshield production-monitor status

# Verify API key
echo $QUERYSHIELD_API_KEY

# Check SaaS status
curl https://api.queryshield.app/api/health
```

### High Memory Usage

**Problem**: Memory usage increases over time

**Solution**:
- Reduce batch timeout: `QUERYSHIELD_BATCH_TIMEOUT=15` (flush more often)
- Reduce batch size: `QUERYSHIELD_BATCH_SIZE=50` (smaller batches)
- Reduce sample rate: `QUERYSHIELD_SAMPLE_RATE=0.001` (fewer queries)

### Performance Impact

**Problem**: App latency increased after enabling monitoring

**Possible causes**:
- Sample rate too high
- SaaS API slow/unreachable
- Batch processing blocking

**Solution**:
- Reduce sample rate: `QUERYSHIELD_SAMPLE_RATE=0.001`
- Increase batch timeout: `QUERYSHIELD_BATCH_TIMEOUT=60`
- Check SaaS connectivity

## Best Practices

### 1. Start with 1% Sampling

```bash
export QUERYSHIELD_SAMPLE_RATE=0.01
```

Monitor for a week, then adjust based on data quality.

### 2. Set Appropriate Slow Query Threshold

For typical APIs:
- **Fast endpoints**: 50-100ms
- **Medium endpoints**: 200-500ms
- **Heavy endpoints**: 1000-5000ms

```bash
export QUERYSHIELD_SLOW_QUERY_MS=500
```

### 3. Use Environment Variables for Secrets

Never hardcode API keys:

```bash
# ✅ Good
export QUERYSHIELD_API_KEY=sk_live_xxx

# ❌ Bad
api_key: sk_live_xxx  # in queryshield.yml
```

### 4. Monitor Multiple Environments

Create separate configs for each environment:

```yaml
# production.yml
production:
  environment: production
  sample_rate: 0.01

# staging.yml  
production:
  environment: staging
  sample_rate: 0.1    # Higher for testing

# development.yml
production:
  environment: development
  sample_rate: 1.0    # 100% for local
```

### 5. Regular Batch Flushes

Set batch timeout to flush regularly:

```bash
export QUERYSHIELD_BATCH_TIMEOUT=30   # Flush every 30 seconds
```

This prevents stale data in the dashboard.

## API Reference

### MonitoringConfig

```python
from queryshield_monitoring import MonitoringConfig

config = MonitoringConfig(
    api_url="https://api.queryshield.app",
    api_key="sk_live_xxx",
    org_id="org_123",
    environment="production",
    sample_rate=0.01,
    slow_query_threshold_ms=500,
    batch_size=100,
    batch_timeout_seconds=30,
    enabled=True,
)

# Or load from environment
config = MonitoringConfig.from_env()
```

### ProductionMonitor

```python
from queryshield_monitoring import ProductionMonitor

monitor = ProductionMonitor(config)

# Record a query (called automatically by middleware)
monitor.record_query(
    sql="SELECT * FROM users WHERE id = ?",
    duration_ms=45.2
)

# Shutdown (flushes remaining batch)
monitor.shutdown()
```

## Support

- Documentation: https://docs.queryshield.io
- Issues: https://github.com/queryshield/queryshield/issues
- Email: support@queryshield.io

