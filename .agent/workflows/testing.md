---
description: How to run tests and linting for the backend
---

## Test Requirements

**When making code changes, always add or update tests:**

- **New endpoint** → Add test cases in the relevant `tests/test_*.py` file covering success, validation errors, and permission denials
- **Modified endpoint** → Update existing tests to match the new behavior
- **Bug fix** → Add a regression test that would have caught the bug
- **Permission-gated routes** → Test both authorized and unauthorized access (403/401)
- **Database model changes** → Ensure tests cover the migration and new fields

### Test Conventions
- All tests are in the `tests/` directory
- Fixtures are defined in `tests/conftest.py` — reuse existing ones before creating new
- Use `client.get/post/put/delete` from the test client fixture
- Always check the response status code AND body content
- For auth-required endpoints, use the `admin_token` or `member_token` fixtures
- Always verify tests pass before committing: `.venv/bin/python -m pytest tests/ -x -q`

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
