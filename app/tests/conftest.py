"""
Shared test fixtures for backend tests.
Creates a temporary PostgreSQL test database for the session.
"""
import os
import sys
import pytest

# Ensure app directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Postgres connection details (same server as production) ──
PG_USER = os.getenv("TEST_PG_USER", "postgres")
PG_PASS = os.getenv("TEST_PG_PASS", "postgres")
PG_HOST = os.getenv("TEST_PG_HOST", "localhost")
PG_PORT = os.getenv("TEST_PG_PORT", "5432")
TEST_DB_NAME = "attendance_test"

ADMIN_URL = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/postgres"
TEST_DB_URL = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB_NAME}"

# Set test environment variables BEFORE any app imports
os.environ.update({
    "environment": "test",
    "secret_key": "test-secret-key-for-testing-only",
    "algorithm": "HS256",
    "access_token_expire_minutes": "30",
    "twilio_account_sid": "placeholder_twilio_sid",
    "twilio_auth_token": "placeholder_twilio_token",
    "twilio_verify_service_sid": "placeholder_verify_sid",
    "twilio_phone_number": "+10000000000",
    "firebase_credentials_path": "placeholder_firebase_path",
    "database_url": TEST_DB_URL,
    "cors_origins": "",
})

from settings import settings
settings.twilio_account_sid = "placeholder_twilio_sid"
settings.twilio_auth_token = "placeholder_twilio_token"
settings.twilio_verify_service_sid = "placeholder_verify_sid"
settings.twilio_phone_number = "+10000000000"
settings.sendgrid_api_key = "placeholder_sendgrid_key"
settings.firebase_credentials_path = "placeholder_firebase_path"

from server import app

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from core.database import Base, get_db
import models
from services.twilio import send_sms_verification
from core.auth import get_password_hash, get_current_user


def _create_test_db():
    """Create the test database if it doesn't exist."""
    engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).fetchone()
        if not existing:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    engine.dispose()


def _drop_test_db():
    """Drop the test database."""
    engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        # Terminate active connections
        conn.execute(text(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{TEST_DB_NAME}' AND pid <> pg_backend_pid()"
        ))
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
    engine.dispose()


# ── Session-scoped: create / destroy the test database once ──
TEST_ENGINE = None
TestSession = None


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Create the test Postgres database once per test session."""
    global TEST_ENGINE, TestSession
    _create_test_db()
    TEST_ENGINE = create_engine(TEST_DB_URL)
    TestSession = sessionmaker(bind=TEST_ENGINE)
    yield
    TEST_ENGINE.dispose()
    _drop_test_db()


@pytest.fixture(autouse=True)
def setup_db(create_test_database):
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    # Seed permissions needed by the member create endpoint
    session = TestSession()
    for name in ["member", "admin"]:
        session.add(models.Permission(name=name))
    session.commit()
    session.close()
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    session = TestSession()
    yield session
    session.close()


def _fake_current_user():
    """Stub for get_current_user — returns a test email."""
    return "test@example.com"


@pytest.fixture
def client(db_session):
    """Create an authenticated FastAPI test client with overridden DB and auth."""
    # Create the test user in the DB so get_current_active_member works
    admin_perm = db_session.query(models.Permission).filter_by(name="admin").first()
    if not admin_perm:
        admin_perm = models.Permission(name="admin")
        db_session.add(admin_perm)
    
    test_user = models.Member(
        first_name="Test",
        last_name="Admin",
        email="test@example.com",
        permissions=[admin_perm]
    )
    db_session.add(test_user)
    db_session.commit() # Commit to get ID and make available to other sessions if needed?
    # Note: db_session is same session used by override_get_db, so it's visible.

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _fake_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(db_session):
    """Create an unauthenticated test client (no auth override)."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_member_data():
    """Sample member creation data."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone_number": "+1234567890",
        "password": "testpassword123",
    }


@pytest.fixture
def created_member(client, sample_member_data):
    """Create a member and return the response data."""
    response = client.post("/members/", json=sample_member_data)
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def sample_session_data():
    """Sample session creation data."""
    return {
        "title": "Sunday Rehearsal",
        "type": "rehearsal",
        "status": "active",
        "start_time": "2026-02-15T10:00:00",
    }


@pytest.fixture
def created_session(client, sample_session_data):
    """Create a session and return the response data."""
    response = client.post("/sessions/", json=sample_session_data)
    assert response.status_code == 200
    return response.json()

