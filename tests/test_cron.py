"""
Tests for the /cron endpoints — auth, routing, and job execution.
"""
from unittest.mock import patch


CRON_SECRET = "test-cron-secret-12345"


class TestCronAuth:
    """Tests for cron endpoint authentication."""

    @patch("app.routers.cron.settings")
    def test_rejects_request_without_secret(self, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.get("/cron/all")
        assert response.status_code == 401

    @patch("app.routers.cron.settings")
    def test_rejects_request_with_wrong_secret(self, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.get("/cron/all?secret=wrong-secret")
        assert response.status_code == 401

    @patch("app.routers.cron.settings")
    def test_returns_503_when_cron_secret_not_configured(self, mock_settings, client):
        mock_settings.cron_secret = None
        response = client.get("/cron/all?secret=anything")
        assert response.status_code == 503

    @patch("app.routers.cron.settings")
    def test_accepts_secret_via_query_param(self, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        with patch("app.routers.cron.update_session_statuses"), \
             patch("app.routers.cron.dispatch_24hr_reminders"):
            response = client.get(f"/cron/all?secret={CRON_SECRET}")
        assert response.status_code == 200

    @patch("app.routers.cron.settings")
    def test_accepts_secret_via_bearer_header(self, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        with patch("app.routers.cron.update_session_statuses"), \
             patch("app.routers.cron.dispatch_24hr_reminders"):
            response = client.get(
                "/cron/all",
                headers={"Authorization": f"Bearer {CRON_SECRET}"},
            )
        assert response.status_code == 200


class TestCronEndpoints:
    """Tests for individual cron endpoints."""

    @patch("app.routers.cron.settings")
    @patch("app.routers.cron.update_session_statuses")
    def test_update_statuses_endpoint(self, mock_update, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.get(f"/cron/update-statuses?secret={CRON_SECRET}")
        assert response.status_code == 200
        assert response.json()["job"] == "update_statuses"
        mock_update.assert_called_once()

    @patch("app.routers.cron.settings")
    @patch("app.routers.cron.dispatch_24hr_reminders")
    def test_reminders_endpoint_without_session_id(self, mock_dispatch, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.get(f"/cron/reminders?secret={CRON_SECRET}")
        assert response.status_code == 200
        assert response.json()["job"] == "reminders"
        assert response.json()["session_id"] is None
        mock_dispatch.assert_called_once_with(session_id=None)

    @patch("app.routers.cron.settings")
    @patch("app.routers.cron.dispatch_24hr_reminders")
    def test_reminders_endpoint_with_session_id(self, mock_dispatch, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.get(f"/cron/reminders?secret={CRON_SECRET}&session_id=42")
        assert response.status_code == 200
        assert response.json()["session_id"] == 42
        mock_dispatch.assert_called_once_with(session_id=42)

    @patch("app.routers.cron.settings")
    @patch("app.routers.cron.dispatch_availability_reminders")
    def test_availability_reminders_endpoint(self, mock_dispatch, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.get(f"/cron/availability-reminders?secret={CRON_SECRET}")
        assert response.status_code == 200
        assert response.json()["job"] == "availability_reminders"
        mock_dispatch.assert_called_once()

    @patch("app.routers.cron.settings")
    @patch("app.routers.cron.dispatch_24hr_reminders")
    @patch("app.routers.cron.update_session_statuses")
    def test_all_endpoint_runs_all_jobs(self, mock_update, mock_dispatch, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.get(f"/cron/all?secret={CRON_SECRET}")
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"]["update_statuses"] == "ok"
        assert data["jobs"]["reminders"] == "ok"
        mock_update.assert_called_once()
        mock_dispatch.assert_called_once()

    @patch("app.routers.cron.settings")
    @patch("app.routers.cron.dispatch_24hr_reminders")
    @patch("app.routers.cron.update_session_statuses")
    def test_all_endpoint_reports_partial_failures(self, mock_update, mock_dispatch, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        mock_update.side_effect = Exception("DB down")
        response = client.get(f"/cron/all?secret={CRON_SECRET}")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data["jobs"]["update_statuses"]
        assert data["jobs"]["reminders"] == "ok"

    @patch("app.routers.cron.settings")
    @patch("app.routers.cron.update_session_statuses")
    def test_supports_post_method(self, mock_update, mock_settings, client):
        mock_settings.cron_secret = CRON_SECRET
        response = client.post(
            "/cron/update-statuses",
            headers={"Authorization": f"Bearer {CRON_SECRET}"},
        )
        assert response.status_code == 200
        mock_update.assert_called_once()

