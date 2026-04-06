---
name: attendance-server-standards
description: Coding standards and architectural conventions for the Attendance Server (FastAPI/Python backend). Apply these rules whenever adding, editing, or refactoring any backend code in this project.
---

# Attendance Server — Coding Standards

## Project Structure

```
Attendance Server/
├── alembic/          # Database migrations (project root, NOT inside app/)
├── alembic.ini       # Alembic config (project root)
├── tests/            # Test suite (project root, NOT inside app/)
├── app/
│   ├── __init__.py   # Makes app a proper package — must remain EMPTY
│   ├── core/
│   ├── models/       # Models must be imported explicitly (e.g., app.models.member)
│   ├── routers/
│   ├── schemas/      # Schemas must be imported explicitly (e.g., app.schemas.auth)
│   ├── services/
│   ├── server.py
│   └── settings.py
├── Makefile
├── pyproject.toml
└── requirements.txt
```

**Key rule**: `alembic/` and `tests/` live at the **project root**, not inside `app/`.

---

## Running the Server

Always run from the **project root**, never `cd app` first:

```bash
# Development
uvicorn app.server:app --reload

# Production
uvicorn app.server:app --host 0.0.0.0 --port 8001

# Via Makefile
make dev
make run
```

The uvicorn entry point is `app.server:app`, not `server:app`.

---

## Python Import Standards

### Rule: All internal imports must use the full `app.` prefix

```python
# ✅ Correct — Explicit submodule imports
from app.models.member import Member
from app.models.session import Session, SessionStatus
from app.schemas.auth import MemberLogin, ResetPasswordRequest
from app.schemas.member import Member as MemberSchema
from app.services.twilio import send_sms_verification

# ❌ Wrong — Import from unified package (REMOVED)
from app.models import Member
from app.schemas import MemberCreate
```

### Rule: Use explicit named imports, not module aliases

```python
# ✅ Correct
from app.models.member import Member, Session, Attendance
from app.schemas.member import MemberCreate, MemberUpdate

# ❌ Wrong — Module aliases or unified package imports
import app.models as models
import app.schemas as schemas
from app.models import Member
```

### Rule: When model and schema share the same name, alias the schema

Both `app.models` and `app.schemas` export classes like `Member`, `Session`, and `Attendance`.
When a file uses **both** the DB model and the schema of the same name, alias the schema:

```python
# ✅ Correct — clear distinction between DB model and schema
from app.models.member import Member
from app.schemas.member import Member as MemberSchema, MemberCreate, MemberUpdate

# ✅ Correct — session example
from app.models.session import Session as SessionModel
from app.schemas.session import Session as SessionSchema, SessionCreate
```

**Naming convention for aliases:**
- Schema aliases: `{Name}Schema` (e.g., `MemberSchema`, `SessionSchema`, `AttendanceSchema`)
- DB model aliases when needed: `{Name}Model` (e.g., `SessionModel`, `AttendanceModel`)

> [!CAUTION]
> When aliasing `from app.schemas import Member as MemberSchema`, only the bare `schemas.Member` reference becomes `MemberSchema`.
> Other schema names that share the `Member` prefix — like `MemberLogin`, `MemberCreate`, `MemberUpdate` — must remain unchanged.
> For example: `schemas.MemberLogin` → `MemberLogin` (NOT `MemberSchemaLogin`).

### Rule: No `sys.path` manipulation

Never use `sys.path.insert` or `sys.path.append` — proper package structure via `app/__init__.py` makes it unnecessary.

```python
# ❌ Never do this
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
```

---

## Security & API Patterns

### Rule: Sensitive data in Request Body, NOT Query Parameters

Sensitive data (passwords, tokens, OTPs) must never be passed in the URL (query string). This prevents exposure in server logs, browser history, and intermediate proxies.

```python
# ✅ Correct — Pydantic schema used for body (POST/PATCH)
class ResetPasswordRequest(BaseModel):
    new_password: str

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest):
    ...

# ❌ Wrong — New password in query parameter
@router.post("/reset-password")
def reset_password(new_password: str): # INSECURE
    ...
```

### Rule: Existence checks in State-Modifying operations

Always verify a record exists in the database before attempting to modify it (Password Reset, Update, Delete).

---

## Settings & Configuration

### Rule: Parsing logic belongs in the Settings class

Never parse environment variables inline in router or service code. Add properties or methods to `Settings` in `app/settings.py`:

```python
# ✅ Correct — logic lives in Settings
class Settings(BaseSettings):
    allowed_redirect_origins: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list:
        return [o.strip() for o in self.allowed_redirect_origins.split(",") if o.strip()]

    @property
    def default_redirect_url(self) -> str:
        first_web = next((o for o in self.allowed_origins_list if o.startswith("http")), "http://localhost:5173")
        return f"{first_web}/calendar"

    def is_redirect_allowed(self, url: str) -> bool:
        return any(url.startswith(origin) for origin in self.allowed_origins_list)

# ❌ Wrong — parsing scattered across router code
allowed = [o.strip() for o in settings.allowed_redirect_origins.split(",") if o.strip()]
```

### Rule: Use Pydantic V2 style

```python
# ✅ Correct — Pydantic V2
from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

class MySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# ❌ Wrong — deprecated Pydantic V1 style
class Settings(BaseSettings):
    class Config:
        env_file = ".env"
```

### Rule: No hardcoded environment-specific values

All deployment-specific values (URLs, domains, secrets) must come from environment variables:

```python
# ✅ Correct
frontend_url: str = "http://localhost:5173"  # overridden by .env in production

# ❌ Wrong
FRONTEND_URL = "https://network.thetechlads.info"  # hardcoded
```

---

## Google OAuth Standards

### Architecture

The backend server handles the full OAuth exchange. The frontend UI only:
1. Calls `GET /auth/google/login?app_redirect=<absolute_url>` to get an auth URL
2. Redirects the browser to that URL
3. Handles the post-callback state (e.g., `?google_success=true`)

### Rule: All OAuth clients pass an absolute `app_redirect` URL

```js
// ✅ Correct — web frontend passes its own origin
const appRedirect = `${window.location.origin}/calendar`;
axios.get('/auth/google/login', { params: { app_redirect: appRedirect } });

// Android/iOS pass their deep link scheme
// attendanceapp://calendar
// com.app.ios://calendar
```

### Rule: Validate redirects against `ALLOWED_REDIRECT_ORIGINS`

```
# Server .env
ALLOWED_REDIRECT_ORIGINS=https://network.thetechlads.info,http://localhost:5173,attendanceapp://
GOOGLE_REDIRECT_URI=https://network-api.thetechlads.info:8000/auth/google/callback
```

```python
# Settings validates inbound redirect targets
if not settings.is_redirect_allowed(target_redirect):
    raise HTTPException(status_code=400, detail="Invalid redirect URI.")
```

### Rule: Google credentials belong on the backend ONLY

```
# ✅ Server .env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# ❌ UI .env — never put these here
GOOGLE_CLIENT_ID=...    # not needed, frontend never calls Google directly
GOOGLE_CLIENT_SECRET=... # dangerous — can be exposed in the bundle
```

---

## Alembic Migrations

Run from **project root** with the root-level `alembic.ini`:

```bash
# Create a migration
make migrations m="add column foo to members"

# Apply migrations
make migrate

# alembic/env.py must use app-prefixed imports
from app.settings import settings
from app.models import Base
```

---

## Testing

Tests live in `tests/` at the project root. Run via:

```bash
make test       # run tests
make coverage   # run with coverage report
```

`tests/conftest.py` must:
- Import the app as `from app.server import app`
- NOT manipulate `sys.path`
- Use `from app.X.Y import Z` style for all models and schemas.

### Rule: Major bug-fixes require corresponding tests

If a bug is found that would have been caught by an automated test, a new regression test must be added to the `tests/` directory (e.g., `tests/test_password_reset.py`).

---

## Alembic `env.py` Template

```python
# alembic/env.py — runs from project root
from app.settings import settings
from app.models import Base

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```
