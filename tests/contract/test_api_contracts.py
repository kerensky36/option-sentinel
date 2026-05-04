import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.data.database import get_db


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_get_dashboard_returns_200(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_get_partials_positions_returns_200(client):
    response = await client.get("/partials/positions")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_get_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "db" in data


# ── US6: Left Navigation Shell ────────────────────────────────────────────────

async def test_dashboard_contains_nav_items(client):
    response = await client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Thesis Monitor" in html
    assert "Covered Call Screener" in html


async def test_dashboard_nav_thesis_monitor_is_active(client):
    response = await client.get("/")
    html = response.text
    # Active nav item must carry the nav-active class
    assert 'nav-active' in html


async def test_screener_returns_200(client):
    response = await client.get("/screener")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_screener_nav_covered_call_screener_is_active(client):
    response = await client.get("/screener")
    html = response.text
    assert "Thesis Monitor" in html
    assert "Covered Call Screener" in html
    assert 'nav-active' in html


# ── US7: Thesis Monitor View ──────────────────────────────────────────────────

async def test_dashboard_contains_thesis_cards_container(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert 'id="thesis-cards"' in response.text


async def test_partials_thesis_cards_returns_200(client):
    response = await client.get("/partials/thesis-cards")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


# ── US8: Covered Call Screener ────────────────────────────────────────────────

async def test_screener_shows_setup_prompt_when_env_var_missing(client, monkeypatch):
    monkeypatch.delenv("SCHWAB_CC_ACCOUNT_ID", raising=False)
    response = await client.get("/screener")
    assert response.status_code == 200
    assert "SCHWAB_CC_ACCOUNT_ID" in response.text


async def test_screener_refresh_returns_200(client, monkeypatch):
    monkeypatch.setenv("SCHWAB_CC_ACCOUNT_ID", "TEST_ACCT_002")
    from unittest.mock import AsyncMock, patch
    with patch("src.api.routes.screener.run_screener", new_callable=AsyncMock) as mock_screen:
        mock_screen.return_value = []
        response = await client.post("/screener/refresh")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
