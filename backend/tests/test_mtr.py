from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.database import SessionLocal
from app.models import Agent, User
from app.models import TestSession as SessionModel
from app.security import hash_password


def headers(client, username="admin", password="test-password-long-enough"):
    token = client.post(
        "/api/v1/auth/token", json={"username": username, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def agent_headers(client):
    created = client.post("/api/v1/agents", headers=headers(client), json={"name": "branch"})
    assert created.status_code == 201
    data = created.json()
    return data["id"], {"Authorization": f"Bearer {data['credential']}"}


def poll(client, auth, available=True):
    return client.post(
        "/api/v1/agent/poll",
        headers=auth,
        json={
            "hostname": "pi",
            "os_name": "Linux",
            "architecture": "aarch64",
            "mtr_available": available,
        },
    )


def test_mtr_job_lifecycle_and_report(client):
    agent_id, agent_auth = agent_headers(client)
    assert poll(client, agent_auth).json() == {"job": None}
    user_auth = headers(client)
    created = client.post(
        "/api/v1/tests/mtr",
        headers=user_auth,
        json={"source_agent_id": agent_id, "target": "example.com", "cycles": 5},
    )
    assert created.status_code == 201
    job = poll(client, agent_auth).json()["job"]
    assert job["id"] == created.json()["id"]
    assert job["target"] == "example.com"
    assert poll(client, agent_auth).json() == {"job": None}
    result = {"success": True, "report": {"report": {"hubs": [{"host": "192.0.2.1"}]}}}
    assert (
        client.post(
            f"/api/v1/agent/jobs/{job['id']}/result", headers=agent_auth, json=result
        ).status_code
        == 204
    )
    assert (
        client.post(
            f"/api/v1/agent/jobs/{job['id']}/result", headers=agent_auth, json=result
        ).status_code
        == 409
    )
    report = client.get("/api/v1/tests", headers=user_auth).json()[0]
    assert report["status"] == "COMPLETED"
    assert report["results"][0]["metrics"]["report"] == result["report"]


def test_auth_roles_validation_and_unavailable_agent(client):
    agent_id, agent_auth = agent_headers(client)
    assert poll(client, {"Authorization": f"Bearer {agent_id}.wrong"}).status_code == 401
    assert poll(client, agent_auth, available=False).status_code == 200
    user_auth = headers(client)
    base = {"source_agent_id": agent_id, "target": "example.com"}
    assert client.post("/api/v1/tests/mtr", headers=user_auth, json=base).status_code == 409
    for bad in ["-help", "example.com;id", "example.com/path"]:
        assert (
            client.post(
                "/api/v1/tests/mtr", headers=user_auth, json={**base, "target": bad}
            ).status_code
            == 422
        )
    with SessionLocal.begin() as db:
        db.add(User(username="viewer", role="viewer", password_hash=hash_password("test-password")))
    viewer = headers(client, "viewer", "test-password")
    assert client.post("/api/v1/agents", headers=viewer, json={"name": "denied"}).status_code == 403
    assert client.post("/api/v1/tests/mtr", headers=viewer, json=base).status_code == 403


def test_agent_cannot_submit_other_agents_job_and_stale_jobs_timeout(client):
    agent_id, auth = agent_headers(client)
    other = client.post("/api/v1/agents", headers=headers(client), json={"name": "other"}).json()
    other_auth = {"Authorization": f"Bearer {other['credential']}"}
    poll(client, auth)
    user_auth = headers(client)
    job = client.post(
        "/api/v1/tests/mtr",
        headers=user_auth,
        json={"source_agent_id": agent_id, "target": "192.0.2.1"},
    ).json()
    poll(client, auth)
    result = {"success": False, "error": "failed"}
    assert (
        client.post(
            f"/api/v1/agent/jobs/{job['id']}/result", headers=other_auth, json=result
        ).status_code
        == 409
    )
    with SessionLocal.begin() as db:
        session = db.get(SessionModel, UUID(job["id"]))
        session.started_at = datetime.now(UTC) - timedelta(seconds=151)
        agent = db.get(Agent, UUID(agent_id))
        agent.last_seen_at = datetime.now(UTC) - timedelta(seconds=121)
    assert client.get("/api/v1/tests", headers=user_auth).json()[0]["status"] == "TIMEOUT"
    assert client.get("/api/v1/agents", headers=user_auth).json()[0]["status"] == "offline"
    assert (
        client.post(f"/api/v1/agent/jobs/{job['id']}/result", headers=auth, json=result).status_code
        == 409
    )


def test_revoking_agent_cancels_jobs_and_blocks_credential(client):
    agent_id, auth = agent_headers(client)
    poll(client, auth)
    user_auth = headers(client)
    job = client.post(
        "/api/v1/tests/mtr",
        headers=user_auth,
        json={"source_agent_id": agent_id, "target": "example.com"},
    ).json()
    poll(client, auth)
    assert client.post(f"/api/v1/agents/{agent_id}/revoke", headers=user_auth).status_code == 204
    assert poll(client, auth).status_code == 401
    assert client.get("/api/v1/tests", headers=user_auth).json()[0]["status"] == "CANCELLED"
    assert (
        client.post(
            f"/api/v1/agent/jobs/{job['id']}/result",
            headers=auth,
            json={"success": False, "error": "failed"},
        ).status_code
        == 401
    )
