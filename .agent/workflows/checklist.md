---
description: Checklist to follow before completing any code change
---

## Pre-Completion Checklist

Before considering any code change complete, **always** run through these steps:

### 1. Tests
- **Did you add or modify an endpoint?** → Add or update tests in `tests/test_*.py`
- **Did you fix a bug?** → Add a regression test that would have caught it
- **Did you change permissions/auth?** → Test both authorized (200) and unauthorized (401/403) access
- **Did you add a new model/migration?** → Ensure test fixtures cover the new fields
- Run `/testing` to verify all tests pass

### 2. Verification
- Run `.venv/bin/python -m pytest tests/ -x -q` and confirm all tests pass
- If a migration was added, verify it applies cleanly

### 3. Schema Validation
- If you changed request/response schemas, verify OpenAPI docs still generate correctly
- Ensure Pydantic models match the SQLAlchemy models

This workflow is **automatically applicable** to every code change. You do not need to be asked to follow it.
