# queryshield-sqlalchemy

SQLAlchemy database query performance probe for QueryShield.

Detect and analyze N+1 queries, missing indexes, slow queries, and other performance issues in SQLAlchemy applications.

## Features

- N+1 query detection
- EXPLAIN plan analysis
- Missing index detection
- Query budget enforcement
- Integration with pytest
- Integration with FastAPI
- Multi-database support (PostgreSQL, MySQL, SQLite)

## Installation

```bash
pip install queryshield-sqlalchemy
```

## Usage

### Pytest Integration

```python
from queryshield_sqlalchemy import QueryShieldProbe

def test_user_queries(session):
    probe = QueryShieldProbe(session)
    
    users = session.query(User).all()
    for user in users:
        print(user.email)
    
    report = probe.finalize()
```

### FastAPI Integration

```python
from queryshield_sqlalchemy import FastAPIProbe

app = FastAPI()
probe = FastAPIProbe()

@app.get("/users")
def get_users(session: Session):
    users = session.query(User).all()
    return users
```

## Documentation

See the main [QueryShield documentation](https://queryshield.app/docs) for more information.
