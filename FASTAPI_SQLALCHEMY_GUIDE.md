# QueryShield FastAPI + SQLAlchemy Guide

Complete guide to using QueryShield with FastAPI and SQLAlchemy ORM.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Basic Setup](#basic-setup)
4. [Analyzing Tests](#analyzing-tests)
5. [Detecting N+1 Queries](#detecting-n1-queries)
6. [Common Patterns](#common-patterns)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

## Overview

QueryShield provides **automatic query performance analysis** for FastAPI applications using SQLAlchemy. Detect N+1 queries, missing indexes, and performance regressions before they hit production.

### Key Features

✅ **Automatic Detection** - Captures all queries during tests  
✅ **N+1 Query Identification** - Detects repeated patterns  
✅ **Multi-Database Support** - PostgreSQL, MySQL, SQLite  
✅ **Cost Analysis** - Estimates cloud database costs  
✅ **SaaS Integration** - Track performance over time  
✅ **Zero Configuration** - Works out of the box  

### Supported ORM

- **SQLAlchemy** 2.0+ (async + sync)
- Works with FastAPI, Starlette, or standalone

## Installation

### 1. Install Package

```bash
pip install queryshield-sqlalchemy
```

### 2. Install Test Dependencies

```bash
pip install pytest pytest-asyncio
```

### 3. Create pytest.ini

```ini
[pytest]
asyncio_mode = auto
```

## Basic Setup

### Step 1: Create SQLAlchemy Models

```python
# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from datetime import datetime

Base = declarative_base()

class Author(Base):
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    
    # Relationship
    books = relationship("Book", back_populates="author")

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    author = relationship("Author", back_populates="books")

# Database
def get_engine():
    return create_engine("sqlite:///test.db")

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
```

### Step 2: Create FastAPI App

```python
# app.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from models import Author, Book, get_engine, Base

app = FastAPI()

# Initialize database
def get_db():
    engine = get_engine()
    with Session(engine) as session:
        yield session

@app.get("/books")
def list_books(db: Session = Depends(get_db)):
    # This will trigger N+1 query!
    books = db.query(Book).all()
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author.name  # N+1 query here
        }
        for b in books
    ]
```

### Step 3: Create Test File

```python
# tests/test_books.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app import app, Base, Book, Author
from fastapi.testclient import TestClient

@pytest.fixture
def test_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(test_engine):
    with Session(test_engine) as s:
        yield s

@pytest.fixture
def client(session):
    # Override dependency
    def override_get_db():
        yield session
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture(autouse=True)
def setup_data(session):
    # Create test data
    author = Author(id=1, name="John Doe", email="john@example.com")
    session.add(author)
    session.flush()
    
    for i in range(5):
        book = Book(id=i+1, title=f"Book {i+1}", author_id=author.id)
        session.add(book)
    
    session.commit()
    yield
    session.rollback()

def test_list_books(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert len(response.json()) == 5
```

### Step 4: Run QueryShield Analysis

```bash
pytest tests/test_books.py -p queryshield_sqlalchemy.runners.pytest_plugin --queryshield-engine "sqlite:///:memory:"
```

Output:
```
Test Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query Count: 6 (budget: ∞)
Total Duration: 12.3ms
Slow Queries: 0
N+1 Detected: 1

Problems Found
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 N+1: SELECT * FROM books (books.py:42)
   5 repeated queries from same location
   Suggestion: Use joinedload() or select_related()
```

## Detecting N+1 Queries

### Problem: N+1 Pattern

```python
# ❌ BAD: N+1 queries
@app.get("/books")
def list_books(db: Session = Depends(get_db)):
    books = db.query(Book).all()  # 1 query
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author.name  # N queries (one per book)
        }
        for b in books
    ]
```

**Queries executed:**
```sql
SELECT * FROM books;  -- 1 query
SELECT * FROM authors WHERE id = 1;  -- N queries
SELECT * FROM authors WHERE id = 2;
SELECT * FROM authors WHERE id = 3;
-- ... (one per book)
```

### Solution 1: Use joinedload()

```python
# ✅ GOOD: Use joinedload()
from sqlalchemy.orm import joinedload

@app.get("/books")
def list_books(db: Session = Depends(get_db)):
    books = db.query(Book).options(joinedload(Book.author)).all()
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author.name
        }
        for b in books
    ]
```

**Queries executed:**
```sql
SELECT books.*, authors.*
FROM books
LEFT JOIN authors ON books.author_id = authors.id;  -- 1 query
```

### Solution 2: Use select_related() (SQLAlchemy 2.0 style)

```python
# ✅ GOOD: Modern SQLAlchemy 2.0
from sqlalchemy import select

@app.get("/books")
def list_books(db: Session = Depends(get_db)):
    stmt = select(Book).options(joinedload(Book.author))
    books = db.scalars(stmt).unique().all()
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author.name
        }
        for b in books
    ]
```

### Solution 3: Bulk Loading

```python
# ✅ GOOD: Bulk load authors
from sqlalchemy import select

@app.get("/books")
def list_books(db: Session = Depends(get_db)):
    books = db.query(Book).all()
    
    # Bulk load all authors at once
    author_ids = [b.author_id for b in books]
    authors = db.query(Author).filter(Author.id.in_(author_ids)).all()
    author_map = {a.id: a for a in authors}
    
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": author_map[b.author_id].name
        }
        for b in books
    ]
```

**Queries executed:**
```sql
SELECT * FROM books;  -- 1 query
SELECT * FROM authors WHERE id IN (1, 2, 3, ...);  -- 1 query
```

## Common Patterns

### Pattern 1: Multiple Relationships

```python
class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    author_id = Column(Integer, ForeignKey("authors.id"))
    publisher_id = Column(Integer, ForeignKey("publishers.id"))
    
    author = relationship("Author")
    publisher = relationship("Publisher")

# ❌ BAD: 3 queries per book (1 for books + N for authors + N for publishers)
books = db.query(Book).all()
for book in books:
    print(book.author.name, book.publisher.name)

# ✅ GOOD: 1 query with multiple joins
books = db.query(Book).options(
    joinedload(Book.author),
    joinedload(Book.publisher)
).all()
```

### Pattern 2: Nested Relationships

```python
class Publisher(Base):
    __tablename__ = "publishers"
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey("countries.id"))
    country = relationship("Country")

# ❌ BAD: N+1 on both levels
for book in books:
    print(book.publisher.country.name)

# ✅ GOOD: Use nested joinedload
books = db.query(Book).options(
    joinedload(Book.publisher).joinedload(Publisher.country)
).all()
```

### Pattern 3: Reverse Relationships (One-to-Many)

```python
# ❌ BAD: Access collection triggers N queries
author = db.query(Author).filter_by(id=1).first()
for book in author.books:  # N query
    print(book.title)

# ✅ GOOD: Use joinedload for collections
author = db.query(Author).options(
    joinedload(Author.books)
).filter_by(id=1).first()
for book in author.books:
    print(book.title)
```

## Advanced Configuration

### Custom Query Budget

```python
# conftest.py
import pytest

def pytest_configure(config):
    config.option.queryshield_nplus1_threshold = 10  # Alert on 10+ repeated queries

def pytest_addoption(parser):
    parser.addoption(
        "--queryshield-nplus1-threshold",
        action="store",
        default=5,
        type=int,
    )
```

### Per-Test Configuration

```python
from queryshield_sqlalchemy import Recorder

@pytest.fixture
def queryshield_recorder():
    return Recorder(nplus1_threshold=3)  # Stricter for this test

def test_critical_path(queryshield_recorder):
    # This test uses custom recorder with threshold=3
    pass
```

### Generate JSON Reports

```bash
pytest tests/test_books.py \
    -p queryshield_sqlalchemy.runners.pytest_plugin \
    --queryshield-report reports/test_results.json
```

### Integration with CI/CD

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - run: pip install -e . queryshield-sqlalchemy pytest
      
      - run: pytest tests/ -p queryshield_sqlalchemy.runners.pytest_plugin
      
      - name: Upload QueryShield Report
        if: always()
        uses: queryshield/queryshield-action@v1
        with:
          api-key: ${{ secrets.QUERYSHIELD_API_KEY }}
```

## Troubleshooting

### Issue: "No queries captured"

**Cause**: Fixture not using QueryShield session

**Solution**: Ensure session is created with proper dependency injection:

```python
@pytest.fixture
def session(test_engine):
    with Session(test_engine) as s:
        yield s  # QueryShield will hook into this

@pytest.fixture
def client(session):
    def override_get_db():
        yield session  # Override app dependency
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

### Issue: "Async queries not captured"

**For async SQLAlchemy:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# QueryShield supports async engines
engine = create_async_engine("postgresql+asyncpg://...")

async def get_db():
    async with AsyncSession(engine) as session:
        yield session
```

### Issue: "All queries grouped as N+1"

**Cause**: Similar queries from different locations

**Solution**: Check stack traces in report:

```json
{
  "problems": [
    {
      "type": "N+1",
      "sql": "SELECT * FROM authors WHERE id = ?",
      "locations": [
        "app.py:42",
        "app.py:45",
        "app.py:48"
      ]
    }
  ]
}
```

## Best Practices

### 1. Use Relationships Carefully

```python
# ✅ Define relationships clearly
class Book(Base):
    author = relationship("Author", lazy="joined")  # Default eager load

# ❌ Avoid circular references
class Author(Base):
    books = relationship("Book", back_populates="author")

class Book(Base):
    author = relationship("Author", back_populates="books")
```

### 2. Set Query Budgets

```python
# conftest.py
@pytest.fixture
def budget():
    return {
        "max_queries": 50,
        "max_duration_ms": 5000,
    }
```

### 3. Test Different Scenarios

```python
def test_list_small_dataset(session):
    # 5 books: should use 1-2 queries
    pass

def test_list_large_dataset(session):
    # 5000 books: should optimize joins
    pass

def test_nested_relationships(session):
    # Books → Authors → Countries: check for N+1 on each level
    pass
```

### 4. Monitor Production Metrics

```bash
# Check if test patterns match production
queryshield production-monitor status
```

## Examples

### Complete FastAPI + SQLAlchemy App

See `sample-fastapi-app/` in QueryShield repository for full working example with:
- Models with relationships
- 4 endpoints (N+1 problem + 3 solutions)
- Docker setup for testing
- QueryShield test integration

## API Reference

### Recorder

```python
from queryshield_sqlalchemy import Recorder

recorder = Recorder(
    nplus1_threshold=5,        # Queries to flag as N+1
    capture_stack_trace=True,  # Include call stack
    capture_params=False,      # Avoid sensitive data
)

# Get captured queries
events = recorder.get_events()
```

### Report Generation

```python
from queryshield_sqlalchemy import build_report, write_report

report = build_report(
    recorder=recorder,
    engine=engine,
    mode="tests",
    nplus1_threshold=5,
)

write_report(report, "report.json")
```

## Support & Resources

- **GitHub**: https://github.com/queryshield/queryshield
- **Documentation**: https://docs.queryshield.io
- **Issues**: https://github.com/queryshield/queryshield/issues
- **Discord**: https://discord.gg/queryshield
- **Email**: support@queryshield.io
