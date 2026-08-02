import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402

TEST_DB_URL = "sqlite:///./test_vulntracker.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_and_login(username="alice", email="alice@example.com", password="password123"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_user():
    resp = client.post("/auth/register", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "secret",
    })
    assert resp.status_code == 201
    assert resp.json()["username"] == "bob"


def test_register_duplicate_username():
    payload = {"username": "bob", "email": "bob@example.com", "password": "secret"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json={**payload, "email": "bob2@example.com"})
    assert resp.status_code == 400


def test_login_success():
    client.post("/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "pw"})
    resp = client.post("/auth/login", json={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    client.post("/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "pw"})
    resp = client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_create_scan():
    token = register_and_login()
    resp = client.post("/scans", json={
        "title": "Reflected XSS in search",
        "description": "User input is echoed without sanitisation",
        "severity": "high",
        "affected_component": "GET /search",
    }, headers=auth_headers(token))
    assert resp.status_code == 201
    assert resp.json()["title"] == "Reflected XSS in search"


def test_list_scans():
    token = register_and_login()
    client.post("/scans", json={
        "title": "Test finding",
        "severity": "low",
        "affected_component": "misc",
    }, headers=auth_headers(token))
    resp = client.get("/scans", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_scan():
    token = register_and_login()
    scan_id = client.post("/scans", json={
        "title": "Insecure deserialization",
        "severity": "high",
        "affected_component": "import handler",
    }, headers=auth_headers(token)).json()["id"]

    resp = client.get(f"/scans/{scan_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == scan_id


def test_get_scan_for_other_users_scan_not_found():
    owner_token = register_and_login(username="scanowner", email="scanowner@example.com")
    scan_id = create_scan(owner_token)

    other_token = register_and_login(username="scanintruder", email="scanintruder@example.com")
    resp = client.get(f"/scans/{scan_id}", headers=auth_headers(other_token))
    assert resp.status_code == 404


def test_search_scans():
    # TODO: add assertions for search results
    token = register_and_login()
    client.post("/scans", json={
        "title": "SQL Injection via login",
        "severity": "critical",
        "affected_component": "POST /auth/login",
    }, headers=auth_headers(token))
    resp = client.get("/scans/search?q=SQL", headers=auth_headers(token))
    assert resp.status_code == 200


def test_update_scan_status():
    token = register_and_login()
    scan_id = client.post("/scans", json={
        "title": "Open redirect",
        "severity": "medium",
        "affected_component": "redirect handler",
    }, headers=auth_headers(token)).json()["id"]

    resp = client.patch(f"/scans/{scan_id}", json={"status": "in_progress"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_delete_scan():
    token = register_and_login()
    scan_id = client.post("/scans", json={
        "title": "Stale finding",
        "severity": "low",
        "affected_component": "misc",
    }, headers=auth_headers(token)).json()["id"]

    resp = client.delete(f"/scans/{scan_id}", headers=auth_headers(token))
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Shared report link
# ---------------------------------------------------------------------------

def create_scan(token, title="Shared finding", severity="high"):
    resp = client.post("/scans", json={
        "title": title,
        "severity": severity,
        "affected_component": "misc",
    }, headers=auth_headers(token))
    return resp.json()["id"]


def test_create_share_link():
    token = register_and_login()
    scan_id = create_scan(token)

    resp = client.post(f"/scans/{scan_id}/share", json={}, headers=auth_headers(token))
    assert resp.status_code == 201
    body = resp.json()
    assert "token" in body
    assert body["share_url"] == f"/share/{body['token']}"


def test_create_share_link_requires_auth():
    token = register_and_login()
    scan_id = create_scan(token)

    resp = client.post(f"/scans/{scan_id}/share", json={})
    assert resp.status_code in (401, 403)


def test_create_share_link_for_other_users_scan_not_found():
    owner_token = register_and_login(username="owner", email="owner@example.com")
    scan_id = create_scan(owner_token)

    other_token = register_and_login(username="intruder", email="intruder@example.com")
    resp = client.post(f"/scans/{scan_id}/share", json={}, headers=auth_headers(other_token))
    assert resp.status_code == 404


def test_access_shared_scan_without_password():
    token = register_and_login()
    scan_id = create_scan(token)

    share_token = client.post(
        f"/scans/{scan_id}/share", json={}, headers=auth_headers(token)
    ).json()["token"]

    resp = client.get(f"/share/{share_token}")
    assert resp.status_code == 200
    assert resp.json()["id"] == scan_id


def test_access_shared_scan_with_password_missing():
    token = register_and_login()
    scan_id = create_scan(token)

    share_token = client.post(
        f"/scans/{scan_id}/share",
        json={"password": "hunter2"},
        headers=auth_headers(token),
    ).json()["token"]

    resp = client.get(f"/share/{share_token}")
    assert resp.status_code == 401


def test_access_shared_scan_with_wrong_password():
    token = register_and_login()
    scan_id = create_scan(token)

    share_token = client.post(
        f"/scans/{scan_id}/share",
        json={"password": "hunter2"},
        headers=auth_headers(token),
    ).json()["token"]

    resp = client.get(f"/share/{share_token}", params={"password": "wrong"})
    assert resp.status_code == 403


def test_access_shared_scan_with_correct_password():
    token = register_and_login()
    scan_id = create_scan(token)

    share_token = client.post(
        f"/scans/{scan_id}/share",
        json={"password": "hunter2"},
        headers=auth_headers(token),
    ).json()["token"]

    resp = client.get(f"/share/{share_token}", params={"password": "hunter2"})
    assert resp.status_code == 200
    assert resp.json()["id"] == scan_id


def test_access_shared_scan_expired_link():
    token = register_and_login()
    scan_id = create_scan(token)

    share_token = client.post(
        f"/scans/{scan_id}/share", json={}, headers=auth_headers(token)
    ).json()["token"]

    db = TestingSessionLocal()
    import models
    link = db.query(models.SharedLink).filter(models.SharedLink.token == share_token).first()
    link.expires_at = datetime.utcnow() - timedelta(hours=1)
    db.add(link)
    db.commit()
    db.close()

    resp = client.get(f"/share/{share_token}")
    assert resp.status_code == 410


def test_access_shared_scan_invalid_token():
    resp = client.get("/share/does-not-exist")
    assert resp.status_code == 404
