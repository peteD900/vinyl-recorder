"""Tests for admin authentication and web API endpoints."""

import pytest
from fastapi.testclient import TestClient
from vinyl_recorder.web_app import app, get_admin_token
from vinyl_recorder.config import Config


@pytest.fixture
def client(tmp_path):
    """Test client with a temporary test database per test."""
    # Point test database to a temp file so each test is isolated
    Config.APP_ENV = "test"
    Config.ADMIN_PASSWORD = "test-secret-password"
    Config.SECRET_KEY = "test-secret-key"
    Config.DB_PATH_TEST = tmp_path / "vinyl_collection_test.db"

    with TestClient(app) as test_client:
        yield test_client


def test_public_home(client):
    """Public home is open to all visitors."""
    res = client.get("/")
    assert res.status_code == 200
    assert "Katie's Vinyl Collection" in res.text


def test_admin_redirects_unauthenticated(client):
    """Visiting /admin without login redirects to /login."""
    res = client.get("/admin", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/login"


def test_login_incorrect_password(client):
    """Logging in with bad password returns 401."""
    res = client.post("/api/login", json={"password": "wrong-password"})
    assert res.status_code == 401


def test_login_success(client):
    """Logging in with correct password sets admin_session cookie."""
    res = client.post("/api/login", json={"password": "test-secret-password"})
    assert res.status_code == 200
    assert "admin_session" in res.cookies


def test_admin_accessible_with_cookie(client):
    """Visiting /admin with valid cookie succeeds."""
    token = get_admin_token()
    client.cookies.set("admin_session", token)
    res = client.get("/admin")
    assert res.status_code == 200
    assert "Studio" in res.text


def test_protected_endpoints_reject_unauthenticated(client):
    """Protected API endpoints must reject calls without admin auth."""
    # Identify endpoint
    res = client.post("/api/identify", json={"image": "dummy"})
    assert res.status_code == 401

    # Add album endpoint
    res = client.post("/api/albums", json={"artist": "A", "album_title": "B"})
    assert res.status_code == 401

    # Recommend endpoint
    res = client.post("/api/recommend", json={"taste_distance": 5})
    assert res.status_code == 401

    # Wishlist modification
    res = client.post("/api/to-buy", json={"artist": "A", "album_title": "B"})
    assert res.status_code == 401


def test_add_and_delete_album_authenticated(client):
    """Authenticated admin can add and delete an album via the API."""
    token = get_admin_token()
    client.cookies.set("admin_session", token)

    payload = {
        "artist": "Led Zeppelin",
        "album_title": "Physical Graffiti",
        "album_year": "1975",
        "cover_image_url": "https://example.com/cover.jpg",
        "tracklist": ["1 Custard Pie", "2 The Rover"],
    }
    res = client.post("/api/albums", json=payload)
    assert res.status_code == 200
    album_id = res.json()["id"]

    # Verify album shows up in albums API
    albums_res = client.get("/api/albums")
    albums = albums_res.json()["albums"]
    assert any(a["id"] == album_id for a in albums)

    # Delete album
    del_res = client.delete(f"/api/albums/{album_id}")
    assert del_res.status_code == 200

    # Verify deleted
    albums_res2 = client.get("/api/albums")
    assert not any(a["id"] == album_id for a in albums_res2.json()["albums"])


def test_duplicate_prevention_and_deduplicate(client):
    """Adding an album twice without force returns 409, and deduplicate cleans existing duplicates."""
    token = get_admin_token()
    client.cookies.set("admin_session", token)

    payload = {
        "artist": "Daft Punk",
        "album_title": "Random Access Memories",
    }

    # First add: succeeds
    res1 = client.post("/api/albums", json=payload)
    assert res1.status_code == 200

    # Second add without force: blocked with 409 Conflict
    res2 = client.post("/api/albums", json=payload)
    assert res2.status_code == 409
    assert res2.json()["is_duplicate"] is True

    # Second add with force: allowed
    payload_force = {**payload, "force": True}
    res3 = client.post("/api/albums", json=payload_force)
    assert res3.status_code == 200

    # Clean duplicates endpoint removes the redundant one
    dedupe_res = client.post("/api/deduplicate")
    assert dedupe_res.status_code == 200
    assert dedupe_res.json()["count"] >= 1
