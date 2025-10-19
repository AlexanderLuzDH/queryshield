# queryshield-core

Shared core logic for QueryShield - query analysis, EXPLAIN parsing, cost calculation, and budget checking.

This package contains the shared analysis engine used by all QueryShield probes (Django, SQLAlchemy, etc.).

## Features

- N+1 query detection
- EXPLAIN plan analysis (PostgreSQL, MySQL, SQLite)
- Cloud cost calculation (AWS, GCP, DigitalOcean)
- Budget enforcement and tracking
- AI-powered root cause analysis

## Installation

```bash
pip install queryshield-core
```

## Usage

```python
from queryshield_core.analysis import classify_problems
from queryshield_core.budgets import check_budget

# Analyze queries
problems = classify_problems(queries)

# Check budget
violations = check_budget(queries, budget_config)
```

## Documentation

See the main [QueryShield documentation](https://queryshield.app/docs) for more information.
