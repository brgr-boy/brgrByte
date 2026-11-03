from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=80)


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    region: str | None
    category: str | None
    created_at: datetime


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    site_id: UUID | None
    status: str
    hostname: str | None
    os_name: str | None
    architecture: str | None
    version: str | None
    last_seen_at: datetime | None
    cpu_percent: float | None
    memory_percent: float | None
    available_engines: list[str]


class OverviewResponse(BaseModel):
    total_sites: int
    total_agents: int
    online_agents: int
    active_tests: int
