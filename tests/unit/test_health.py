"""Smoke tests for the health check endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.api.main import create_app
    app = create_app()
    return TestClient(app)


class TestHealth:
    def test_health_returns_200(self, client):
        """/health returns HTTP 200."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        """/health response body is {"status": "ok"}."""
        resp = client.get("/health")
        data = resp.json()
        assert data == {"status": "ok"}

    def test_health_requires_no_auth(self, client):
        """/health is accessible without Authorization header."""
        resp = client.get("/health")
        # Must NOT return 401 or 403
        assert resp.status_code not in (401, 403)

    def test_health_no_db_check(self, client):
        """/health works even without any DB configuration (DB is removed)."""
        # If this test completes without error, no DB import was attempted
        resp = client.get("/health")
        assert resp.status_code == 200
