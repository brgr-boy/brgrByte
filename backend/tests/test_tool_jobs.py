from datetime import UTC, datetime, timedelta
from uuid import UUID

from test_mtr import headers

from app.database import SessionLocal
from app.models import TestSession as SessionModel
from app.models import User
from app.security import hash_password


def new_agent(client, name):
    response = client.post("/api/v1/agents", headers=headers(client), json={"name": name})
    data = response.json()
    auth = {"Authorization": f"Bearer {data['credential']}"}
    poll(client, auth)
    return data["id"], auth


def poll(client, auth):
    return client.post(
        "/api/v1/agent/poll",
        headers=auth,
        json={
            "hostname": "host",
            "os_name": "Linux",
            "architecture": "arm64",
            "mtr_available": True,
            "available_engines": ["mtr", "iperf3", "sipp", "nmap", "ping", "traceroute", "dns"],
        },
    )


def send(client, job, auth, result):
    return client.post(f"/api/v1/agent/jobs/{job}/result", headers=auth, json=result)


def test_dns_job_defaults_custom_server_validation_and_results(client):
    source_id, source = new_agent(client, "dns-source")
    user = headers(client)
    base = {"source_agent_id": source_id, "target": "example.com"}
    created = client.post("/api/v1/tests/dns", headers=user, json=base)
    assert created.status_code == 201
    job = poll(client, source).json()["job"]
    assert job["engine"] == "dns"
    assert job["server"] == "8.8.8.8" and job["record_type"] == "A"
    report = {"server": job["server"], "status": "NOERROR", "output": "answer"}
    assert send(client, job["id"], source, {"success": True, "report": report}).status_code == 204
    result = client.get("/api/v1/tests", headers=user).json()[0]
    assert result["results"][0]["metrics"]["report"] == report

    custom = client.post(
        "/api/v1/tests/dns",
        headers=user,
        json={
            **base,
            "target": "_dmarc.example.com",
            "server": "2001:4860:4860::8888",
            "record_type": "TXT",
        },
    )
    assert custom.status_code == 201
    job = poll(client, source).json()["job"]
    assert job["server"] == "2001:4860:4860::8888" and job["record_type"] == "TXT"
    assert job["target"] == "_dmarc.example.com"
    report = {"status": "NXDOMAIN", "output": "no such name"}
    assert (
        send(
            client,
            job["id"],
            source,
            {"success": False, "error": "DNS response: NXDOMAIN", "report": report},
        ).status_code
        == 204
    )
    result = client.get("/api/v1/tests", headers=user).json()[0]
    assert result["status"] == "FAILED" and result["results"][0]["metrics"]["report"] == report
    for invalid in (
        {"server": "resolver.example"}, {"server": "fe80::1%eth0"},
        {"record_type": "ANY"}, {"target": "-bad"}, {"target": "::1"},
    ):
        response = client.post("/api/v1/tests/dns", headers=user, json={**base, **invalid})
        assert response.status_code == 422
    assert client.post("/api/v1/tests/dns", json=base).status_code == 401
    with SessionLocal.begin() as db:
        db.add(
            User(username="dns-viewer", role="viewer", password_hash=hash_password("test-password"))
        )
    viewer = headers(client, "dns-viewer", "test-password")
    assert client.post("/api/v1/tests/dns", headers=viewer, json=base).status_code == 403
    client.post(
        "/api/v1/agent/poll", headers=source,
        json={"hostname": "host", "os_name": "Linux", "architecture": "arm64",
              "mtr_available": True, "available_engines": ["mtr"]},
    )
    assert client.post("/api/v1/tests/dns", headers=user, json=base).status_code == 409


def test_iperf_agent_receiver_then_source_then_both_results(client):
    source_id, source = new_agent(client, "source")
    destination_id, destination = new_agent(client, "destination")
    user = headers(client)
    response = client.post(
        "/api/v1/tests/iperf3",
        headers=user,
        json={
            "source_agent_id": source_id,
            "destination_agent_id": destination_id,
            "target": "192.0.2.2",
            "port": 5201,
            "duration": 5,
        },
    )
    assert response.status_code == 201
    job = response.json()["id"]
    assert poll(client, source).json()["job"] is None
    assert poll(client, destination).json()["job"]["engine"] == "iperf3-server"
    assert client.post(f"/api/v1/agent/jobs/{job}/ready", headers=source).status_code == 409
    assert client.post(f"/api/v1/agent/jobs/{job}/ready", headers=destination).status_code == 204
    assert poll(client, source).json()["job"]["engine"] == "iperf3"
    report = {"success": True, "report": {"end": {"sum_received": {"bits_per_second": 10}}}}
    assert send(client, job, destination, report).status_code == 204
    assert client.get("/api/v1/tests", headers=user).json()[0]["status"] == "RUNNING"
    assert send(client, job, destination, report).status_code == 409
    assert send(client, job, source, report).status_code == 204
    result = client.get("/api/v1/tests", headers=user).json()[0]
    assert result["status"] == "COMPLETED"
    assert {item["agent_id"] for item in result["results"]} == {source_id, destination_id}


def test_iperf_external_and_sipp_failures_are_reported(client):
    source_id, source = new_agent(client, "source")
    user = headers(client)
    iperf = client.post(
        "/api/v1/tests/iperf3",
        headers=user,
        json={"source_agent_id": source_id, "target": "192.0.2.3"},
    ).json()
    assert poll(client, source).json()["job"]["engine"] == "iperf3"
    assert (
        send(
            client, iperf["id"], source, {"success": False, "error": "connection refused"}
        ).status_code
        == 204
    )
    sipp = client.post(
        "/api/v1/tests/sipp",
        headers=user,
        json={"source_agent_id": source_id, "target": "sip.example", "calls": 2},
    ).json()
    assert poll(client, source).json()["job"]["engine"] == "sipp"
    assert (
        send(
            client,
            sipp["id"],
            source,
            {"success": False, "error": "call failed", "report": {"failed_calls": 2}},
        ).status_code
        == 204
    )
    results = client.get("/api/v1/tests", headers=user).json()
    assert all(result["status"] == "FAILED" for result in results)
    assert results[0]["results"][0]["metrics"]["report"]["failed_calls"] == 2


def test_receiver_errors_revoke_and_timeout(client):
    source_id, source = new_agent(client, "source")
    destination_id, destination = new_agent(client, "destination")
    user = headers(client)
    config = {
        "source_agent_id": source_id,
        "destination_agent_id": destination_id,
        "target": "192.0.2.2",
    }
    job = client.post("/api/v1/tests/iperf3", headers=user, json=config).json()["id"]
    poll(client, destination)
    assert (
        send(client, job, destination, {"success": False, "error": "port in use"}).status_code
        == 204
    )
    assert client.get("/api/v1/tests", headers=user).json()[0]["status"] == "FAILED"
    job = client.post("/api/v1/tests/iperf3", headers=user, json=config).json()["id"]
    poll(client, destination)
    with SessionLocal.begin() as db:
        db.get(SessionModel, UUID(job)).started_at = datetime.now(UTC) - timedelta(seconds=151)
    assert client.post(f"/api/v1/agent/jobs/{job}/ready", headers=destination).status_code == 409
    assert client.get("/api/v1/tests", headers=user).json()[0]["status"] == "TIMEOUT"
    job = client.post("/api/v1/tests/iperf3", headers=user, json=config).json()["id"]
    assert client.post(f"/api/v1/agents/{destination_id}/revoke", headers=user).status_code == 204
    assert client.get("/api/v1/tests", headers=user).json()[0]["status"] == "CANCELLED"
    assert poll(client, source).json()["job"] is None


def test_unexpected_receiver_connection_and_source_first(client):
    source_id, source = new_agent(client, "source")
    destination_id, destination = new_agent(client, "destination")
    user = headers(client)
    config = {
        "source_agent_id": source_id,
        "destination_agent_id": destination_id,
        "target": "192.0.2.2",
    }
    report = {"success": True, "report": {"end": {"sum_received": {"bits_per_second": 10}}}}
    job = client.post("/api/v1/tests/iperf3", headers=user, json=config).json()["id"]
    poll(client, destination)
    assert client.post(f"/api/v1/agent/jobs/{job}/ready", headers=destination).status_code == 204
    assert send(client, job, destination, report).status_code == 204
    result = client.get("/api/v1/tests", headers=user).json()[0]
    assert result["status"] == "FAILED"
    assert result["results"][0]["error"] == "Receiver was consumed before the source started"
    assert poll(client, source).json()["job"] is None

    job = client.post("/api/v1/tests/iperf3", headers=user, json=config).json()["id"]
    poll(client, destination)
    assert client.post(f"/api/v1/agent/jobs/{job}/ready", headers=destination).status_code == 204
    poll(client, source)
    assert send(client, job, source, report).status_code == 204
    assert client.get("/api/v1/tests", headers=user).json()[0]["status"] == "RUNNING"
    assert send(client, job, destination, report).status_code == 204
    assert client.get("/api/v1/tests", headers=user).json()[0]["status"] == "COMPLETED"


def test_tool_inputs_and_permissions(client):
    source_id, _ = new_agent(client, "source")
    user = headers(client)
    same = {"source_agent_id": source_id, "destination_agent_id": source_id, "target": "localhost"}
    assert client.post("/api/v1/tests/iperf3", headers=user, json=same).status_code == 422
    invalid = {"source_agent_id": source_id, "target": "localhost", "calls": 1001}
    assert client.post("/api/v1/tests/sipp", headers=user, json=invalid).status_code == 422
    assert client.post("/api/v1/tests/sipp", json=invalid).status_code == 401


def test_network_tool_lifecycle_and_validation(client):
    source_id, source = new_agent(client, "probe")
    user = headers(client)
    for engine, config in (
        ("nmap", {"ports": [22, 443]}),
        ("ping", {"count": 2}),
        ("traceroute", {}),
    ):
        base = {"source_agent_id": source_id, "target": "127.0.0.1", **config}
        created = client.post(f"/api/v1/tests/{engine}", headers=user, json=base)
        assert created.status_code == 201
        job = poll(client, source).json()["job"]
        assert job["engine"] == engine and job["target"] == "127.0.0.1"
        report = {"output": "result"}
        assert (
            send(client, job["id"], source, {"success": True, "report": report}).status_code == 204
        )
        result = client.get("/api/v1/tests", headers=user).json()[0]
        assert result["status"] == "COMPLETED"
        assert result["results"][0]["metrics"]["report"] == report

    base = {"source_agent_id": source_id, "target": "localhost"}
    for ports in ([], [22, 22], [True], [0], [65536], list(range(1, 102))):
        assert (
            client.post(
                "/api/v1/tests/nmap", headers=user, json={**base, "ports": ports}
            ).status_code
            == 422
        )
    assert (
        client.post("/api/v1/tests/ping", headers=user, json={**base, "count": 11}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/tests/traceroute", headers=user, json={**base, "target": "192.0.2.0/24"}
        ).status_code
        == 422
    )
    assert client.post("/api/v1/tests/nmap", json=base).status_code == 401
    with SessionLocal.begin() as db:
        db.add(User(username="viewer", role="viewer", password_hash=hash_password("test-password")))
    viewer = headers(client, "viewer", "test-password")
    for engine in ("nmap", "ping", "traceroute"):
        assert client.post(f"/api/v1/tests/{engine}", headers=viewer, json=base).status_code == 403
    client.post(
        "/api/v1/agent/poll",
        headers=source,
        json={
            "hostname": "host",
            "os_name": "Linux",
            "architecture": "arm64",
            "mtr_available": True,
            "available_engines": ["mtr"],
        },
    )
    for engine in ("nmap", "ping", "traceroute"):
        assert client.post(f"/api/v1/tests/{engine}", headers=user, json=base).status_code == 409
