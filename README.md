# QueryShield

**Automated database query performance analysis for Django and FastAPI** - Detect N+1 queries, missing indexes, and cost regressions before they hit production.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/badge/pypi-v0.2.0--rc-orange.svg)](https://pypi.org/project/queryshield/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## ✨ Features

### 🔍 Query Analysis
- **N+1 Detection** - Automatically identifies repeated queries in loops
- **Missing Index Warnings** - PostgreSQL/MySQL EXPLAIN-based analysis
- **Cost Calculation** - Estimates monthly database infrastructure costs
- **Problem Ranking** - ROI scoring to prioritize fixes

### 📊 Multi-Database Support
- PostgreSQL (with EXPLAIN FORMAT JSON)
- MySQL 8.0+ (with EXPLAIN FORMAT JSON)
- SQLite (simplified analysis)

### 🚀 Integration Points
- **Django Test Suite** - Built-in pytest plugin
- **GitHub Actions** - PR comments with analysis and regression detection
- **SaaS Dashboard** - Cloud storage, history, team collaboration
- **IDE Plugins** - JetBrains (PyCharm, IntelliJ) and VS Code

### 💰 Cost & ROI
- Pricing profiles for AWS RDS, GCP Cloud SQL, DigitalOcean
- Estimated fix time and savings calculations
- Business case generation for optimization

## 🚀 Quick Start

### Installation

```bash
# Install core probe
pip install queryshield-probe

# Install CLI tool
pip install queryshield

# For Django projects
pip install queryshield[django]
```

### Usage: Django

1. **Configure budgets** (`queryshield.yml`):
```yaml
defaults:
  max_queries: 50
  max_total_db_time_ms: 5000
  forbid:
    - type: "N+1"

tests:
  "app.tests.test_books":
    max_queries: 10
```

2. **Run analysis**:
```bash
queryshield analyze --runner django --explain
```

3. **View results**:
```
Results saved to .queryshield/queryshield_report.json
```

### Usage: GitHub Actions

Add to `.github/workflows/queryshield.yml`:

```yaml
name: QueryShield Analysis
on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: queryshield/action@v1
        with:
          budgets-file: queryshield.yml
          runner: django
```

## 📋 CLI Commands

```bash
# Analyze test suite and generate report
queryshield analyze --runner django --output report.json

# Check if report violates budgets
queryshield budget-check --budgets queryshield.yml --report report.json

# Save current report as baseline for regression detection
queryshield record-baseline --report report.json --output baseline.json

# Compare PR changes to baseline
queryshield verify-patch --baseline baseline.json --report report.json
```

## 📊 Example Report

```json
{
  "version": "1",
  "tests": [
    {
      "name": "app.tests.test_books",
      "queries_total": 12,
      "duration_ms": 2500,
      "problems": [
        {
          "type": "N+1",
          "id": "n+1:views.py:45",
          "suggestion": {
            "kind": "select_related",
            "args": ["author"]
          }
        }
      ],
      "cost_analysis": {
        "estimated_monthly_cost": 45.00,
        "total_savings_potential": 38.50
      }
    }
  ]
}
```

## 🏗️ Architecture

### Packages

| Package | Purpose |
|---------|---------|
| `queryshield-probe` | Django query interception and analysis |
| `queryshield` | CLI tool for running analysis |
| `queryshield-sqlalchemy` | FastAPI/SQLAlchemy support *(Phase 2)* |
| `queryshield-saas` | Cloud dashboard and API |
| `queryshield-action` | GitHub Actions integration |

### Data Flow

```
Django Tests
    ↓
Query Interception (Probe)
    ↓
Analysis Engine (N+1, EXPLAIN, Cost)
    ↓
Report Generation (JSON)
    ↓
Budget Checking
    ↓
Dashboard / CLI Output
```

## 📈 Problem Types

| Problem | Detection | Solution |
|---------|-----------|----------|
| **N+1 Queries** | Repeated SQL from same code location | `select_related()`, `prefetch_related()` |
| **Missing Index** | Seq scans on large tables (PostgreSQL/MySQL) | `CREATE INDEX` with auto-generated DDL |
| **Sort Without Index** | Sort operations not using indexes | Composite index with sort columns |
| **SELECT * Large** | Selecting all columns from 10K+ row table | Explicit column selection |

## 🔧 Advanced Configuration

### Per-Test Budgets

```yaml
defaults:
  max_queries: 50

tests:
  "tests.test_api::list_users":
    max_queries: 5
    ignore:
      - "explain:select_star_large:*"
```

### Cost Profiles

```bash
queryshield analyze \
  --runner django \
  --cost-profile=aws_rds_postgres \
  --queries-per-month=10000000
```

### Production Monitoring *(Phase 2)*

```python
from queryshield.monitoring import QueryShieldMiddleware

app.add_middleware(QueryShieldMiddleware,
                   api_key="sk_...",
                   sample_rate=0.01)
```

## 📚 Documentation

- [Installation Guide](./docs/installation.md)
- [Django Integration](./docs/django.md)
- [FastAPI Integration](./docs/fastapi.md) *(Phase 2)*
- [GitHub Actions Setup](./docs/github-actions.md)
- [SaaS Dashboard](./docs/dashboard.md)
- [API Reference](./docs/api.md)
- [CLI Reference](./docs/cli.md)

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md)

## 💬 Community

- [GitHub Discussions](https://github.com/queryshield/queryshield/discussions)
- [Discord Server](https://discord.gg/queryshield)
- [Twitter](https://twitter.com/queryshieldapp)

## 📄 License

MIT - See [LICENSE](./LICENSE)

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Django](https://www.djangoproject.com/) - Web framework for Python
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Typer](https://typer.tiangolo.com/) - CLI framework

---

**Ready to optimize your database queries?**

```bash
pip install queryshield-probe queryshield
queryshield analyze --runner django
```

💡 Questions? [Open an issue](https://github.com/queryshield/queryshield/issues) or check our [FAQ](./docs/faq.md)

