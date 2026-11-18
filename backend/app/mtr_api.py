import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api import AuthenticatedUser, DbSession, bearer_scheme
from app.models import Agent, AuditEvent, Site, TestResult, TestSession
from app.schemas import (
    AgentCreate,
    AgentCreated,
    AgentPoll,
    AgentResult,
    DnsCreate,
    IperfCreate,
    MtrCreate,
    NmapCreate,
    PingCreate,
    SippCreate,
    TestResponse,
    TracerouteCreate,
)

router = APIRouter(prefix="/api/v1")


def expire_stale(db: DbSession) -> None:
    now = datetime.now(UTC)
    db.execute(
        update(Agent)
        .where(Agent.status == "online", Agent.last_seen_at < now - timedelta(seconds=120))
        .values(status="offline")
        .execution_options(synchronize_session="fetch")
    )
    db.execute(
        update(TestSession)
        .where(
            TestSession.status.in_(("PREPARING", "READY", "RUNNING")),
            TestSession.started_at < now - timedelta(seconds=150),
        )
        .values(status="TIMEOUT", completed_at=now)
        .execution_options(synchronize_session="fetch")
    )
    db.execute(
        update(TestSession)
        .where(
            TestSession.status == "CREATED",
            TestSession.created_at < now - timedelta(minutes=5),
        )
        .values(status="TIMEOUT", completed_at=now)
        .execution_options(synchronize_session="fetch")
    )
    db.commit()


def authenticated_agent(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> Agent:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Agent authentication required")
    try:
        agent_id, secret = credentials.credentials.split(".", 1)
        agent = db.get(Agent, UUID(agent_id))
    except ValueError:
        agent = None
        secret = ""
    digest = hashlib.sha256(secret.encode()).hexdigest()
    if (
        agent is None
        or agent.credential_hash is None
        or not hmac.compare_digest(agent.credential_hash, digest)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid agent credential")
    return agent


AgentIdentity = Annotated[Agent, Depends(authenticated_agent)]


@router.post("/agents", response_model=AgentCreated, status_code=201)
def create_agent(request: AgentCreate, user: AuthenticatedUser, db: DbSession) -> AgentCreated:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only administrators can create agents")
    if request.site_id is not None and db.get(Site, request.site_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")
    secret = secrets.token_urlsafe(32)
    agent = Agent(
        name=request.name,
        site_id=request.site_id,
        credential_hash=hashlib.sha256(secret.encode()).hexdigest(),
    )
    try:
        db.add(agent)
        db.flush()
        db.add(
            AuditEvent(
                actor_user_id=user.id,
                event_type="agent.created",
                entity_type="agent",
                entity_id=agent.id,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Agent name already exists") from None
    return AgentCreated(id=agent.id, credential=f"{agent.id}.{secret}")


@router.post("/agents/{agent_id}/revoke", status_code=204)
def revoke_agent(agent_id: UUID, user: AuthenticatedUser, db: DbSession) -> None:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only administrators can revoke agents")
    agent = db.get(Agent, agent_id, with_for_update=True)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    agent.credential_hash = None
    agent.status = "offline"
    agent.available_engines = []
    db.execute(
        update(TestSession)
        .where(
            (TestSession.source_agent_id == agent_id)
            | (TestSession.destination_agent_id == agent_id),
            TestSession.status.in_(("CREATED", "PREPARING", "READY", "RUNNING")),
        )
        .values(status="CANCELLED", completed_at=datetime.now(UTC))
    )
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            event_type="agent.revoked",
            entity_type="agent",
            entity_id=agent_id,
        )
    )
    db.commit()


@router.post("/agent/poll")
def poll_agent(request: AgentPoll, agent: AgentIdentity, db: DbSession) -> dict:
    expire_stale(db)
    db.refresh(agent, with_for_update=True)
    if agent.credential_hash is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Agent credential revoked")
    agent.hostname = request.hostname
    agent.os_name = request.os_name
    agent.architecture = request.architecture
    agent.last_seen_at = datetime.now(UTC)
    agent.status = "online"
    agent.version = "0.1.0"
    agent.available_engines = (
        sorted(
            set(request.available_engines)
            & {"mtr", "iperf3", "sipp", "nmap", "ping", "traceroute", "dns"}
        )
        if request.available_engines is not None
        else (["mtr"] if request.mtr_available else [])
    )
    server_id = None
    if "iperf3" in agent.available_engines:
        server_id = db.scalar(
            select(TestSession.id)
            .where(
                TestSession.destination_agent_id == agent.id,
                TestSession.status == "CREATED",
                TestSession.engine == "iperf3",
            )
            .order_by(TestSession.created_at)
            .limit(1)
        )
    if server_id is not None:
        claimed = db.execute(
            update(TestSession)
            .where(TestSession.id == server_id, TestSession.status == "CREATED")
            .values(status="PREPARING", started_at=datetime.now(UTC))
        )
        db.commit()
        if claimed.rowcount != 1:
            return {"job": None}
        job = db.get(TestSession, server_id)
        return {"job": {"id": str(job.id), "engine": "iperf3-server", **job.configuration}}
    job_id = db.scalar(
        select(TestSession.id)
        .where(
            TestSession.source_agent_id == agent.id,
            (
                ((TestSession.status == "CREATED") & TestSession.destination_agent_id.is_(None))
                | ((TestSession.status == "READY") & (TestSession.engine == "iperf3"))
            ),
            TestSession.engine.in_(agent.available_engines),
        )
        .order_by(TestSession.created_at)
        .limit(1)
    )
    if job_id is None:
        db.commit()
        return {"job": None}
    claimed = db.execute(
        update(TestSession)
        .where(TestSession.id == job_id, TestSession.status.in_(("CREATED", "READY")))
        .values(status="RUNNING", started_at=datetime.now(UTC))
    )
    db.commit()
    if claimed.rowcount != 1:
        return {"job": None}
    job = db.get(TestSession, job_id)
    return {"job": {"id": str(job.id), "engine": job.engine, **job.configuration}}


@router.post("/agent/jobs/{job_id}/ready", status_code=204)
def receiver_ready(job_id: UUID, agent: AgentIdentity, db: DbSession) -> None:
    db.refresh(agent, with_for_update=True)
    if agent.credential_hash is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Agent credential revoked")
    claimed = db.execute(
        update(TestSession)
        .where(
            TestSession.id == job_id,
            TestSession.destination_agent_id == agent.id,
            TestSession.engine == "iperf3",
            TestSession.status == "PREPARING",
            TestSession.started_at >= datetime.now(UTC) - timedelta(seconds=150),
        )
        .values(status="READY")
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Receiver job is not preparing")
    db.commit()


@router.post("/agent/jobs/{job_id}/result", status_code=204)
def submit_result(job_id: UUID, request: AgentResult, agent: AgentIdentity, db: DbSession) -> None:
    if request.success and (request.report is None or request.error is not None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "A successful result needs a report"
        )
    if not request.success and not request.error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A failed result needs an error")
    if len(json.dumps(request.report).encode()) > 500_000:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Report is too large")
    db.refresh(agent, with_for_update=True)
    if agent.credential_hash is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Agent credential revoked")
    now = datetime.now(UTC)
    job = db.get(TestSession, job_id, with_for_update=True)
    if (
        job is None
        or agent.id not in (job.source_agent_id, job.destination_agent_id)
        or job.status not in ("PREPARING", "READY", "RUNNING")
        or job.started_at is None
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Job is not running for this agent")
    if job.engine == "iperf3" and job.destination_agent_id is not None:
        if job.started_at.replace(tzinfo=UTC) < now - timedelta(seconds=150):
            raise HTTPException(status.HTTP_409_CONFLICT, "Job has expired")
        existing = db.scalar(
            select(TestResult.id).where(
                TestResult.session_id == job_id, TestResult.agent_id == agent.id
            )
        )
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Agent result already submitted")
        if agent.id == job.source_agent_id and job.status != "RUNNING":
            raise HTTPException(status.HTTP_409_CONFLICT, "Source job is not running")
        if agent.id == job.destination_agent_id and request.success and job.status != "RUNNING":
            request.success = False
            request.error = "Receiver was consumed before the source started"
        db.add(
            TestResult(
                session_id=job_id,
                agent_id=agent.id,
                success=request.success,
                error=request.error,
                metrics={"report": request.report} if request.report is not None else {},
            )
        )
        if not request.success:
            job.status = "FAILED"
            job.completed_at = now
        elif db.scalar(select(TestResult.id).where(TestResult.session_id == job_id)) is not None:
            job.status = "COMPLETED"
            job.completed_at = now
        db.commit()
        return
    claimed = db.execute(
        update(TestSession)
        .where(
            TestSession.id == job_id,
            TestSession.source_agent_id == agent.id,
            TestSession.status == "RUNNING",
            TestSession.started_at >= now - timedelta(seconds=150),
        )
        .values(status="COMPLETED" if request.success else "FAILED", completed_at=now)
        .execution_options(synchronize_session="fetch")
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Job is not running for this agent")
    db.add(
        TestResult(
            session_id=job_id,
            agent_id=agent.id,
            success=request.success,
            error=request.error,
            metrics={"report": request.report} if request.report is not None else {},
        )
    )
    db.commit()


@router.post("/tests/mtr", response_model=TestResponse, status_code=201)
def create_mtr(request: MtrCreate, user: AuthenticatedUser, db: DbSession) -> TestSession:
    if user.role == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Viewer role cannot run tests")
    expire_stale(db)
    agent = db.get(Agent, request.source_agent_id, with_for_update=True)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    if agent.status != "online" or "mtr" not in agent.available_engines:
        raise HTTPException(status.HTTP_409_CONFLICT, "Agent is offline or MTR is unavailable")
    job = TestSession(
        source_agent_id=agent.id,
        engine="mtr",
        status="CREATED",
        configuration={"target": request.target, "cycles": request.cycles},
    )
    db.add(job)
    db.flush()
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            event_type="test.created",
            entity_type="test_session",
            entity_id=job.id,
            details={"engine": "mtr", "target": request.target, "source_agent_id": str(agent.id)},
        )
    )
    db.commit()
    return job


def create_tool_test(
    engine: str,
    request: IperfCreate | SippCreate | NmapCreate | PingCreate | TracerouteCreate | DnsCreate,
    user: AuthenticatedUser,
    db: DbSession,
) -> TestSession:
    if user.role == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Viewer role cannot run tests")
    expire_stale(db)
    destination_id = request.destination_agent_id if isinstance(request, IperfCreate) else None
    if destination_id == request.source_agent_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Agents must be different")
    agent_ids = sorted([value for value in (request.source_agent_id, destination_id) if value])
    agents = list(
        db.scalars(
            select(Agent).where(Agent.id.in_(agent_ids)).order_by(Agent.id).with_for_update()
        )
    )
    if len(agents) != len(agent_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    if any(agent.status != "online" or engine not in agent.available_engines for agent in agents):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Agent is offline or {engine} is unavailable"
        )
    config = request.model_dump(exclude={"source_agent_id", "destination_agent_id"})
    job = TestSession(
        source_agent_id=request.source_agent_id,
        destination_agent_id=destination_id,
        engine=engine,
        status="CREATED",
        configuration=config,
    )
    db.add(job)
    db.flush()
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            event_type="test.created",
            entity_type="test_session",
            entity_id=job.id,
            details={"engine": engine, "target": request.target},
        )
    )
    db.commit()
    return job


@router.post("/tests/iperf3", response_model=TestResponse, status_code=201)
def create_iperf(request: IperfCreate, user: AuthenticatedUser, db: DbSession) -> TestSession:
    return create_tool_test("iperf3", request, user, db)


@router.post("/tests/sipp", response_model=TestResponse, status_code=201)
def create_sipp(request: SippCreate, user: AuthenticatedUser, db: DbSession) -> TestSession:
    return create_tool_test("sipp", request, user, db)


@router.post("/tests/nmap", response_model=TestResponse, status_code=201)
def create_nmap(request: NmapCreate, user: AuthenticatedUser, db: DbSession) -> TestSession:
    return create_tool_test("nmap", request, user, db)


@router.post("/tests/ping", response_model=TestResponse, status_code=201)
def create_ping(request: PingCreate, user: AuthenticatedUser, db: DbSession) -> TestSession:
    return create_tool_test("ping", request, user, db)


@router.post("/tests/traceroute", response_model=TestResponse, status_code=201)
def create_traceroute(
    request: TracerouteCreate, user: AuthenticatedUser, db: DbSession
) -> TestSession:
    return create_tool_test("traceroute", request, user, db)


@router.post("/tests/dns", response_model=TestResponse, status_code=201)
def create_dns(request: DnsCreate, user: AuthenticatedUser, db: DbSession) -> TestSession:
    return create_tool_test("dns", request, user, db)


@router.get("/tests", response_model=list[TestResponse])
def list_tests(_: AuthenticatedUser, db: DbSession) -> list[TestSession]:
    expire_stale(db)
    return list(
        db.scalars(
            select(TestSession)
            .options(selectinload(TestSession.results))
            .order_by(TestSession.created_at.desc())
            .limit(100)
        )
    )
