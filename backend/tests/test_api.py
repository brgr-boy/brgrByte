from app.database import SessionLocal
from app.models import AuditEvent, User
from app.security import hash_password


def create_admin():
    with SessionLocal.begin() as db:
        db.add(
            User(
                username="test-admin",
                password_hash=hash_password("correct-password"),
                role="admin",
            )
        )


def test_health_endpoints(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_bootstrap_admin_can_sign_in(client):
    response = client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "test-password-long-enough"},
    )
    assert response.status_code == 200
    identity = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert identity.json()["role"] == "admin"


def test_inventory_is_protected_and_empty_overview_is_correct(client):
    assert client.get("/api/v1/overview").status_code == 401
    create_admin()
    response = client.post(
        "/api/v1/auth/token",
        json={"username": "test-admin", "password": "correct-password"},
    )
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    assert client.get("/api/v1/overview", headers=headers).json() == {
        "total_sites": 0,
        "total_agents": 0,
        "online_agents": 0,
        "active_tests": 0,
    }


def test_site_creation_and_overview(client):
    create_admin()
    token = client.post(
        "/api/v1/auth/token",
        json={"username": "test-admin", "password": "correct-password"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/sites",
        json={"name": "DC Lab", "region": "West", "category": "datacenter"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "DC Lab"
    assert client.get("/api/v1/sites", headers=headers).json()[0]["name"] == "DC Lab"
    duplicate = client.post(
        "/api/v1/sites",
        json={"name": "DC Lab"},
        headers=headers,
    )
    assert duplicate.status_code == 409
    with SessionLocal() as db:
        event = db.query(AuditEvent).one()
        assert event.event_type == "site.created"
        assert event.entity_id is not None


def test_viewer_cannot_create_sites(client):
    with SessionLocal.begin() as db:
        db.add(
            User(
                username="viewer",
                password_hash=hash_password("correct-password"),
                role="viewer",
            )
        )
    token = client.post(
        "/api/v1/auth/token",
        json={"username": "viewer", "password": "correct-password"},
    ).json()["access_token"]
    assert (
        client.post(
            "/api/v1/sites",
            json={"name": "Blocked"},
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 403
    )
