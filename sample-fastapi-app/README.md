# QueryShield Sample: FastAPI + SQLAlchemy

Reference implementation demonstrating database query optimization with QueryShield and FastAPI + SQLAlchemy.

## Overview

This sample application shows:
- **N+1 Query Problem** - How to accidentally fetch 101 queries instead of 1
- **Optimization Patterns** - 3 different ways to fix the problem
- **QueryShield Integration** - Automatic detection via the SQLAlchemy probe

## Quick Start

### Prerequisites

```bash
# PostgreSQL running locally
psql -U postgres -c "CREATE DATABASE queryshield_sample;"
psql -U postgres -c "CREATE DATABASE queryshield_sample_test;"

# Python 3.9+
pip install -e .
```

### Run the FastAPI Server

```bash
uvicorn app.main:app --reload
```

Server runs at http://localhost:8000

API endpoints:
- GET `/` - Overview of all endpoints
- GET `/books-nplus1` - ❌ N+1 query problem (101 queries)
- GET `/books-optimized` - ✅ Optimized with joinedload (1 query)
- GET `/books-modern` - ✅ SQLAlchemy 2.0 style (1 query)
- GET `/books-bulk` - ✅ Bulk loading (2 queries)
- GET `/health` - Health check
- GET `/docs` - Swagger documentation

### Run Tests with QueryShield Analysis

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests with QueryShield probe
pytest tests/test_nplus1.py \
    -p queryshield_sqlalchemy.runners.pytest_plugin \
    --queryshield-engine "postgresql://postgres:postgres@localhost/queryshield_sample_test" \
    --queryshield-report ".queryshield/report.json"
```

This generates `.queryshield/report.json` with query analysis.

View results:

```bash
cat .queryshield/report.json | python -m json.tool
```

## Key Demonstrations

### ❌ N+1 Problem: `/books-nplus1`

```python
books = db.query(Book).all()
for book in books:
    print(book.author.name)  # ← Triggers 1 query per book!
```

**Query Count:** N+1 (101 queries for 100 books)

**QueryShield Output:**
```json
{
  "type": "N+1",
  "cluster_count": 100,
  "suggestion": {
    "kind": "joinedload",
    "message": "Use .options(joinedload(Book.author))"
  }
}
```

### ✅ Optimization 1: Joinedload (Eager Loading)

```python
from sqlalchemy import joinedload

books = db.query(Book).options(joinedload(Book.author)).all()
for book in books:
    print(book.author.name)  # ← No additional queries
```

**Query Count:** 1 (single JOIN)

**Performance:** 100x faster

### ✅ Optimization 2: SQLAlchemy 2.0 Style

```python
from sqlalchemy import select, joinedload

stmt = select(Book).options(joinedload(Book.author))
books = db.scalars(stmt).unique().all()
```

**Query Count:** 1 (single JOIN)

**Modern API:** Cleaner syntax

### ✅ Optimization 3: Bulk Loading

```python
books = db.query(Book).all()
author_ids = [b.author_id for b in books]
authors = {a.id: a for a in db.query(Author).filter(Author.id.in_(author_ids)).all()}

for book in books:
    print(authors[book.author_id].name)  # ← From map, no queries
```

**Query Count:** 2 (books + authors with IN clause)

**Useful when:** Processing books and authors separately

## QueryShield Integration

### Automatic Detection

The SQLAlchemy probe automatically intercepts all database queries and detects:

1. **N+1 Patterns** - Repeated queries from the same code location
2. **Performance Issues** - Slow queries
3. **Cost Impact** - Database cost estimation

### Test Output

```bash
$ pytest tests/test_nplus1.py -p queryshield_sqlalchemy.runners.pytest_plugin ...

queryshield_sample_test/test_nplus1.py::test_books_nplus1_problem ........ [33%]
queryshield_sample_test/test_nplus1.py::test_books_optimized_query ...... [67%]
queryshield_sample_test/test_nplus1.py::test_books_bulk_load ........... [100%]

QueryShield report saved to .queryshield/report.json
```

### Report Analysis

```python
import json

with open(".queryshield/report.json") as f:
    report = json.load(f)

for test in report["tests"]:
    print(f"Test: {test['name']}")
    print(f"  Queries: {test['queries_total']}")
    print(f"  Problems: {len(test['problems'])}")
    for problem in test["problems"]:
        print(f"    - {problem['type']}: {problem.get('id')}")
```

## Docker Setup

Run with Docker Compose:

```bash
docker-compose up
```

Services:
- FastAPI: http://localhost:8000
- PostgreSQL: localhost:5432
- pgAdmin: http://localhost:5050

## Architecture

```
FastAPI Application
    ↓
SQLAlchemy ORM
    ↓
PostgreSQL Database
    ↓
QueryShield Probe (detects issues)
    ↓
QueryShield Report (JSON analysis)
```

## Common Patterns

### Wrong: Loop with FK access

```python
for book in books:
    print(book.author.name)  # N+1 problem!
```

### Right: Eager load before loop

```python
books = db.query(Book).options(joinedload(Book.author)).all()
for book in books:
    print(book.author.name)  # OK, already loaded
```

### Right: Bulk fetch

```python
author_ids = [b.author_id for b in books]
authors = db.query(Author).filter(Author.id.in_(author_ids)).all()
```

## QueryShield Commands

```bash
# Analyze with report
queryshield analyze --runner sqlalchemy --output report.json

# Check budgets
queryshield budget-check --budgets queryshield.yml --report report.json

# View suggestions
python -c "import json; r=json.load(open('report.json')); [print(p['suggestion']) for t in r['tests'] for p in t['problems']]"
```

## Further Reading

- [QueryShield Documentation](https://queryshield.io/docs)
- [SQLAlchemy Eager Loading](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html)
- [N+1 Query Problem](https://en.wikipedia.org/wiki/N%2B1_problem)

## License

MIT - See LICENSE file
