# Attendance Server

A FastAPI backend for managing church/organization attendance, scheduling, and member management. Provides REST APIs for QR-code-based check-in, role-based calendar scheduling, session management, and multi-channel OTP authentication.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) 0.128 |
| Language | Python 3.14 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 ORM |
| Migrations | Alembic |
| Auth | JWT (PyJWT) with OTP verification |
| Email | SendGrid (primary) / Mailgun (alt) |
| SMS & Verify | Twilio Messaging + Verify APIs |
| Push | Firebase Cloud Messaging |
| Scheduling | APScheduler (24-hr reminders) |
| Realtime | WebSockets (attendance broadcasts) |
| CI | GitHub Actions (lint → test w/ coverage) |

## Project Structure

```
app/
├── server.py              # FastAPI app, CORS, lifespan, routers
├── settings.py            # Pydantic BaseSettings (all env vars)
├── core/
│   ├── auth.py            # JWT creation/validation, password hashing
│   ├── database.py        # SQLAlchemy engine & session factory
│   ├── logging_config.py  # Structured JSON logging setup
│   ├── scheduler.py       # APScheduler: 24-hr reminder jobs
│   ├── utils.py           # Haversine distance (geofencing)
│   └── websocket.py       # Attendance WS manager
├── models/                # SQLAlchemy ORM models
│   ├── member.py          # Member, Permission, Role
│   ├── session.py         # Session (rehearsal/program/etc.)
│   ├── attendance.py      # Attendance records
│   ├── assignment.py      # Role-based session assignments
│   ├── availability.py    # Member availability declarations
│   ├── day_off.py         # Approved days off
│   ├── session_template.py# Reusable session templates
│   └── associations.py    # M2M association tables
├── schemas/               # Pydantic request/response models
├── routers/               # API route handlers
│   ├── auth.py            # Login, OTP verify, password reset
│   ├── google_auth.py     # Google OAuth2 flow
│   ├── members.py         # Member CRUD + role management
│   ├── sessions.py        # Session CRUD
│   ├── session_templates.py # Template CRUD
│   ├── attendance.py      # Manual attendance marking
│   ├── qr_attendance.py   # QR token generation & scan marking
│   ├── calendar.py        # Calendar views, assignments, availability
│   └── statistics.py      # Member attendance stats
├── services/
│   ├── attendance.py      # Anti-fraud validation (device lock, geofence)
│   ├── comm.py            # Email & SMS sending (SendGrid/Mailgun/Twilio)
│   ├── local_otp.py       # In-memory OTP store + send
│   ├── twilio.py          # Twilio Verify API wrapper
│   ├── verification.py    # Pluggable verification provider facade
│   ├── rate_limiter.py    # IP-based rate limiting
│   ├── recaptcha.py       # Google reCAPTCHA v2 verification
│   ├── email_providers/   # SendGrid, Mailgun adapters
│   ├── sms_providers/     # Twilio SMS adapter
│   └── verification_providers/  # Twilio Verify / Local OTP adapters
├── scripts/
│   └── create_db.py       # Bootstrap database creation
tests/
├── conftest.py            # Shared fixtures (client, DB, members, sessions)
├── test_auth.py           # Login, OTP, password reset
├── test_members.py        # Member CRUD
├── test_sessions.py       # Session CRUD
├── test_attendance.py     # Manual attendance
├── test_qr_attendance.py  # QR flow
├── test_fraud_prevention.py  # Device lock, geofencing
├── test_rate_limiter.py   # Rate limiting + admin geofence bypass
├── test_calendar.py       # Calendar endpoints
├── test_scheduler.py      # Reminder scheduling
├── test_twilio.py         # Twilio Verify + convenience functions
├── test_local_otp.py      # Local OTP store
├── test_websocket.py      # WS manager + broadcast
├── test_password_reset.py # Admin + public password reset
├── test_auth_protection.py # 401 on unauthed endpoints
├── test_models.py         # ORM model unit tests
└── test_statistics.py     # Stats endpoint
```

## Getting Started

### Prerequisites

- Python 3.14+
- PostgreSQL 16+
- A virtual environment (`.venv`)

### 1. Clone & Install

```bash
git clone <repo-url> && cd Attendance-Server
python -m venv .venv
source .venv/bin/activate
make install
```

### 2. Configure Environment

Copy the example and fill in your values:

```bash
cp .env.example .env   # or edit .env directly
```

**Required environment variables:**

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/attendance` |
| `SECRET_KEY` | JWT signing secret | `your-random-secret` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `30` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | `xxxxxxxxx` |
| `TWILIO_VERIFY_SERVICE_SID` | Twilio Verify Service SID | `VAxxxxxxx` |
| `TWILIO_PHONE_NUMBER` | Twilio sender number | `+1234567890` |

**Optional environment variables:**

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `local` | `local` / `dev` / `ci` / `production` / `test` |
| `APP_TIMEZONE` | `America/Chicago` | Timezone for session times & reminders |
| `VERIFICATION_PROVIDER` | `twilio_verify` | `twilio_verify` or `local` (in-memory OTP) |
| `OTP_EXPIRY_SECONDS` | `300` | OTP code validity window |
| `EMAIL_PROVIDER` | `sendgrid` | `sendgrid` / `mailgun` / `mock` |
| `SENDGRID_API_KEY` | placeholder | SendGrid API key |
| `MAILGUN_API_KEY` | placeholder | Mailgun API key |
| `MAILGUN_DOMAIN` | (empty) | Mailgun sending domain |
| `EMAIL_FROM_ADDRESS` | `noreply@example.com` | Sender email address |
| `FIREBASE_CREDENTIALS_PATH` | placeholder | Path to Firebase service account JSON |
| `CORS_ORIGINS` | (empty) | Comma-separated extra CORS origins |
| `GOOGLE_CLIENT_ID` | (none) | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | (none) | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | (none) | Google OAuth redirect URI |
| `ALLOWED_REDIRECT_ORIGINS` | `http://localhost:5173` | Comma-separated trusted redirect origins |
| `RECAPTCHA_SECRET_KEY` | (none) | Google reCAPTCHA v2 secret key |
| `RECAPTCHA_ENABLED` | `true` | Enable/disable reCAPTCHA enforcement |
| `DEVICE_ID_MODE` | `fingerprint` | `fingerprint` or `localStorage` — controls anti-fraud device lock behavior |

### 3. Database Setup

```bash
# Create the database
source .venv/bin/activate && python app/scripts/create_db.py

# Run migrations
make migrate
```

### 4. Run

```bash
# Development (auto-reload)
make dev

# Production
make run
```

The server starts on `http://localhost:8002` by default. Override with `PORT=XXXX make run`.

## API Overview

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/login` | Email/phone login → returns token or triggers OTP |
| `POST` | `/auth/verify-otp` | Verify OTP code → returns JWT |
| `POST` | `/auth/forgot-password` | Initiate password reset OTP |
| `POST` | `/auth/reset-password` | Reset password with OTP |
| `GET`  | `/auth/google` | Start Google OAuth flow |
| `GET`  | `/auth/google/callback` | Google OAuth callback |

### Members

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/members/` | List all members (sorted by first name) |
| `POST` | `/members/` | Create a member |
| `GET` | `/members/{id}` | Get member by ID |
| `PUT` | `/members/{id}` | Update member fields |
| `DELETE` | `/members/{id}` | Delete a member |
| `POST` | `/members/{id}/reset-password` | Admin password reset |

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/sessions/` | List all sessions |
| `POST` | `/sessions/` | Create a session |
| `PUT` | `/sessions/{id}` | Update a session |
| `DELETE` | `/sessions/{id}` | Delete a session |
| `POST` | `/sessions/bulk-delete` | Bulk delete sessions |

### Attendance

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/attendance/` | Mark attendance (admin/manual) |
| `GET` | `/attendance/qr/token/{session_id}` | Generate QR token |
| `POST` | `/attendance/qr/mark` | Mark via QR scan |

### Calendar

Full calendar management with role assignments, availability, day-off requests, and Google Sheets import. See `app/routers/calendar.py` for the complete API.

### Real-time

| Protocol | Endpoint | Description |
|---|---|---|
| `WebSocket` | `/ws/attendance/{session_id}` | Live attendance updates |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET/HEAD` | `/health` | Returns `OK` |

## Anti-Fraud System

The attendance system includes multiple layers of fraud prevention:

### 1. Device Lock (Anti-Buddy Punching)
Prevents the same device from marking attendance for multiple members in a single session.

- **Fingerprint mode** (`DEVICE_ID_MODE=fingerprint`, default): Uses browser fingerprinting. Collisions are **logged as warnings** but allowed through, since identical hardware can produce false positives.
- **localStorage mode** (`DEVICE_ID_MODE=localStorage`): Uses a persistent UUID per browser. Collisions are **hard-blocked** (403), since IDs are unique per installation.

### 2. Geofencing
Sessions can be configured with `latitude`, `longitude`, and `radius` (meters). Self-check-in requires the member's location to be within the radius. Admin overrides bypass geofencing.

### 3. Duplicate Prevention
A member cannot mark attendance twice for the same session (409 Conflict).

### 4. Rate Limiting
IP-based rate limiting on login and forgot-password endpoints to prevent brute-force attacks.

### 5. reCAPTCHA
Optional Google reCAPTCHA v2 verification on web login (mobile clients skip via token omission).

## Testing

```bash
# Run all tests (148 tests)
make test

# Run with coverage report
make coverage
```

Tests use a dedicated `attendance_test` PostgreSQL database (auto-created by `conftest.py`). All email and SMS sends are mocked — no real messages are sent during testing.

## Database Migrations

```bash
# Create a new migration
make migrations m="Add new column to members"

# Apply migrations
make migrate

# Custom alembic commands
make migrate cmd="downgrade -1"
```

## CI/CD

GitHub Actions runs on push/PR to `main`/`master`:

1. **Lint** — `flake8` for syntax errors and undefined names
2. **Test** — Full pytest suite with PostgreSQL 16 service container + coverage report

## License

Private — all rights reserved.
