# QueryShield GitHub Action

Automatically analyze your Django test suite's database query performance on every pull request. Detect N+1 queries, missing indexes, and cost regressions before they hit production.

## Features

- **Automatic Query Analysis** - Runs QueryShield on your Django test suite
- **PR Comments** - Posts detailed analysis and cost estimates as PR comments
- **Regression Detection** - Compares current query metrics to your main branch
- **Budget Enforcement** - Fails the build if query budgets are exceeded
- **Dashboard Integration** - Optional upload to QueryShield dashboard for history and trends

## Usage

### Basic Setup

Add to `.github/workflows/queryshield.yml`:

```yaml
name: QueryShield Analysis

on:
  pull_request:
    branches: [main, develop]

jobs:
  queryshield:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install -e .
          python -m pip install queryshield queryshield-probe

      - name: Run QueryShield
        uses: queryshield/action@v1
        with:
          budgets-file: queryshield.yml
          compare-to: main
          runner: django
          explain: 'true'
          fail-on-violations: 'true'
```

### With Dashboard Integration

```yaml
      - name: Run QueryShield
        uses: queryshield/action@v1
        with:
          budgets-file: queryshield.yml
          compare-to: main
          runner: django
          api-key: ${{ secrets.QUERYSHIELD_API_KEY }}
```

## Inputs

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `budgets-file` | Path to queryshield.yml config | `queryshield.yml` | No |
| `compare-to` | Git branch to compare against | `main` | No |
| `runner` | Test runner (django or pytest) | `django` | No |
| `explain` | Enable EXPLAIN analysis on PostgreSQL | `true` | No |
| `api-key` | QueryShield API key for dashboard upload | N/A | No |
| `fail-on-violations` | Fail build on budget violations | `true` | No |

## Outputs

| Output | Description |
|--------|-------------|
| `report-url` | URL to full report on QueryShield dashboard |
| `violations-count` | Number of budget violations detected |
| `queries-delta` | Change in query count vs. baseline |

## Configuration

Create a `queryshield.yml` file in your repository:

```yaml
defaults:
  max_queries: 50
  max_total_db_time_ms: 5000
  forbid:
    - type: "N+1"
    - type: "MISSING_INDEX"

tests:
  "app.tests.test_api.APITest.test_list_books":
    max_queries: 10
    max_total_db_time_ms: 500
```

## Example PR Comment

```
## 📊 QueryShield Analysis

| Test | Queries | p95 (ms) | Problems | Cost |
|------|---------|---------|----------|------|
| app.tests.test_books | 12 | 45.3 | N+1 | $0.03/mo |

### 📈 Comparison to main

⚠️ Query count increased by **5** (+41.7%)

### ⚠️ Budget Violations

- app.tests.test_books: queries_total 12 > max_queries 10

📤 [View full report on QueryShield Dashboard](https://queryshield.app/reports)
```

## How It Works

1. Checks out your code
2. Installs QueryShield and runs `queryshield analyze`
3. Fetches baseline report from your configured branch
4. Compares current metrics to baseline
5. Posts summary as PR comment
6. Optionally uploads to QueryShield dashboard
7. Fails build if violations are detected

## Dashboard Integration

For historical trends, regression alerts, and team analytics, connect to the QueryShield dashboard:

1. Create a free account at https://queryshield.app
2. Generate an API key in Settings
3. Add to GitHub Secrets: `QUERYSHIELD_API_KEY`
4. Use `api-key` input in workflow

## Troubleshooting

### "No baseline report found"

The action looks for `.queryshield/queryshield_report.json` in your baseline branch. On first run, this file won't exist. Just merge the PR and it will be available for future comparisons.

### "Budget violations detected"

Review your `queryshield.yml` config and either:
- Fix the query performance issues (recommended)
- Increase the budget if appropriate
- Use `ignore` rules to suppress specific problems

### Tests not being found

Make sure your Django `DJANGO_SETTINGS_MODULE` environment variable is set and your test database is accessible.

## License

MIT - See LICENSE file
