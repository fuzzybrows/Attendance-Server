"""
Tests for WebSocket live attendance updates.
Covers: WebSocket manager, WS endpoint, and broadcast on QR mark.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.core.websocket import AttendanceWSManager
from app.core.auth import create_access_token


class TestAttendanceWSManager:
    """Unit tests for the WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_connect_adds_websocket_to_session(self):
        manager = AttendanceWSManager()
        ws = AsyncMock()
        await manager.connect(ws, session_id=1)
        assert 1 in manager._connections
        assert ws in manager._connections[1]
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_websocket(self):
        manager = AttendanceWSManager()
        ws = AsyncMock()
        await manager.connect(ws, session_id=1)
        manager.disconnect(ws, session_id=1)
        assert 1 not in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_only_removes_target_websocket(self):
        manager = AttendanceWSManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1, session_id=1)
        await manager.connect(ws2, session_id=1)
        manager.disconnect(ws1, session_id=1)
        assert ws2 in manager._connections[1]
        assert ws1 not in manager._connections[1]

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self):
        manager = AttendanceWSManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1, session_id=5)
        await manager.connect(ws2, session_id=5)

        data = {"event": "attendance_marked", "member_id": 1}
        await manager.broadcast(5, data)

        ws1.send_json.assert_awaited_once_with(data)
        ws2.send_json.assert_awaited_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast_does_nothing_for_unknown_session(self):
        manager = AttendanceWSManager()
        # Should not raise
        await manager.broadcast(999, {"event": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        manager = AttendanceWSManager()
        alive = AsyncMock()
        dead = AsyncMock()
        dead.send_json.side_effect = Exception("Connection closed")

        await manager.connect(alive, session_id=3)
        await manager.connect(dead, session_id=3)

        await manager.broadcast(3, {"event": "test"})

        # Dead connection should be removed
        assert dead not in manager._connections[3]
        assert alive in manager._connections[3]

    @pytest.mark.asyncio
    async def test_multiple_sessions_are_independent(self):
        manager = AttendanceWSManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1, session_id=1)
        await manager.connect(ws2, session_id=2)

        await manager.broadcast(1, {"event": "test"})

        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_not_awaited()


class TestWebSocketEndpoint:
    """Integration tests for the /ws/attendance/{session_id} endpoint."""

    def test_websocket_connects_and_accepts(self, client):
        with client.websocket_connect("/ws/attendance/1") as ws:
            # Connection accepted — just disconnect
            pass

    def test_websocket_receives_broadcast(self, client, created_session):
        """Simulate a broadcast while a client is connected."""
        from app.core.websocket import attendance_ws
        import asyncio

        session_id = created_session["id"]

        with client.websocket_connect(f"/ws/attendance/{session_id}") as ws:
            # Broadcast from a background thread
            loop = asyncio.new_event_loop()
            loop.run_until_complete(attendance_ws.broadcast(session_id, {
                "event": "attendance_marked",
                "member_id": 42
            }))
            loop.close()

            data = ws.receive_json()
            assert data["event"] == "attendance_marked"
            assert data["member_id"] == 42


class TestQRMarkBroadcasts:
    """Verify that marking QR attendance triggers a WebSocket broadcast."""

    def test_qr_mark_triggers_broadcast(self, client, created_member, created_session):
        with patch("app.routers.qr_attendance.attendance_ws") as mock_ws:
            mock_ws.broadcast = AsyncMock()

            qr_resp = client.get(f"/attendance/qr/token/{created_session['id']}")
            qr_token = qr_resp.json()["token"]
            auth_token = create_access_token(data={"sub": created_member["email"]})

            response = client.post(
                "/attendance/qr/mark",
                params={"session_id": created_session["id"], "qr_token": qr_token},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code == 200

            # Verify broadcast was scheduled
            mock_ws.broadcast.assert_awaited_once()
            call_args = mock_ws.broadcast.call_args
            assert call_args[0][0] == created_session["id"]
            assert call_args[0][1]["event"] == "attendance_marked"
            assert call_args[0][1]["member_id"] == created_member["id"]
