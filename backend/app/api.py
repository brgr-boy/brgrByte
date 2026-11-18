from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, AuditEvent, Site, TestSession, User
from app.schemas import (
    AgentResponse,
    LoginRequest,
    OverviewResponse,
    SiteCreate,
    SiteResponse,
    TokenResponse,
)
from app.security import create_access_token, decode_access_token, verify_password

router = APIRouter(prefix="/api/v1")
bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        user_id, _ = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token"
        ) from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


AuthenticatedUser = Annotated[User, Depends(current_user)]


@router.post("/auth/token", response_model=TokenResponse)
def login(request: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == request.username))
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return TokenResponse(access_token=create_access_token(user))


@router.get("/overview", response_model=OverviewResponse)
def overview(_: AuthenticatedUser, db: DbSession) -> OverviewResponse:
    from app.mtr_api import expire_stale

    expire_stale(db)
    return OverviewResponse(
        total_sites=db.scalar(select(func.count()).select_from(Site)) or 0,
        total_agents=db.scalar(select(func.count()).select_from(Agent)) or 0,
        online_agents=db.scalar(
            select(func.count()).select_from(Agent).where(Agent.status == "online")
        )
        or 0,
        active_tests=db.scalar(
            select(func.count())
            .select_from(TestSession)
            .where(TestSession.status.in_(("PREPARING", "READY", "RUNNING")))
        )
        or 0,
    )


@router.get("/sites", response_model=list[SiteResponse])
def list_sites(_: AuthenticatedUser, db: DbSession) -> list[Site]:
    return list(db.scalars(select(Site).order_by(Site.name)))


@router.post("/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(request: SiteCreate, user: AuthenticatedUser, db: DbSession) -> Site:
    if user.role == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Viewer role cannot create sites")
    site = Site(name=request.name.strip(), region=request.region, category=request.category)
    if not site.name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Site name cannot be blank")
    try:
        db.add(site)
        db.flush()
        db.add(
            AuditEvent(
                actor_user_id=user.id,
                event_type="site.created",
                entity_type="site",
                entity_id=site.id,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A site with that name already exists"
        ) from None
    db.refresh(site)
    return site


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(_: AuthenticatedUser, db: DbSession) -> list[Agent]:
    from app.mtr_api import expire_stale

    expire_stale(db)
    return list(db.scalars(select(Agent).order_by(Agent.name)))


@router.get("/users/me")
def read_current_user(user: AuthenticatedUser) -> dict[str, str | UUID]:
    return {"id": user.id, "username": user.username, "role": user.role}
