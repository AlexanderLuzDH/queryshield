# queryshield-probe

Django database query performance probe for QueryShield.

Detect and analyze N+1 queries, missing indexes, slow queries, and other performance issues in Django tests and applications.

## Features

- N+1 query detection
- Missing index detection
- Query budget enforcement
- Performance regression detection
- Integration with pytest
- Integration with Django test runner
- Cloud cost estimation

## Installation

```bash
pip install queryshield-probe
```

## Usage

### Pytest Integration

```python
import pytest
from queryshield_probe import queryshield_pytest_plugin

@pytest.mark.queryshield
def test_user_queries(db):
    users = User.objects.all()
    for user in users:
        print(user.email)
```

### Django Settings

```python
INSTALLED_APPS = [
    'queryshield_probe',
]
```

## Documentation

See the main [QueryShield documentation](https://queryshield.app/docs) for more information.
