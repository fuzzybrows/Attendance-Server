---
description: How to run tests and linting for the backend
---

## Running Tests

// turbo
1. Run the full test suite:
```bash
.venv/bin/python -m pytest tests/ -x -q
```

2. Run a specific test file:
```bash
.venv/bin/python -m pytest tests/test_websocket.py -v
```

3. Run tests with coverage:
```bash
.venv/bin/python -m pytest tests/ --cov=app --cov-report=term-missing
```

## Running Linting

There is no dedicated linter configured for the backend. Pyrefly is used via IDE integration.

## Notes

- Tests use a local PostgreSQL database (`attendance_test`), created automatically by `conftest.py`
- The test DB is dropped after each session
- `pytest-asyncio` is required for WebSocket manager tests
- All test fixtures are in `tests/conftest.py`
