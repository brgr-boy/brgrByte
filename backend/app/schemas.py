import ipaddress
import re
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    site_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value


class AgentCreated(BaseModel):
    id: UUID
    credential: str


class AgentPoll(BaseModel):
    hostname: str = Field(max_length=255)
    os_name: str = Field(max_length=120)
    architecture: str = Field(max_length=80)
    mtr_available: bool
    available_engines: list[str] | None = None


class TargetedTestCreate(BaseModel):
    source_agent_id: UUID
    target: str = Field(min_length=1, max_length=253)

    @field_validator("target")
    @classmethod
    def valid_target(cls, value: str) -> str:
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            pass
        if not re.fullmatch(
            r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.?",
            value,
        ):
            raise ValueError("Target must be a hostname or IP address")
        return value


class MtrCreate(TargetedTestCreate):
    cycles: int = Field(default=10, ge=1, le=20)


class PingCreate(TargetedTestCreate):
    count: int = Field(default=4, ge=1, le=10, strict=True)


class TracerouteCreate(TargetedTestCreate):
    max_hops: int = Field(default=30, ge=1, le=30, strict=True)


class DnsCreate(TargetedTestCreate):
    server: str = Field(default="8.8.8.8", min_length=1, max_length=45)
    record_type: Literal["A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT"] = "A"

    @field_validator("target")
    @classmethod
    def valid_target(cls, value: str) -> str:
        if not re.fullmatch(
            r"(?=.{1,253}\Z)(?:[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?\.)*"
            r"[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?\.?",
            value,
        ):
            raise ValueError("DNS target must be a DNS name")
        return value

    @field_validator("server")
    @classmethod
    def valid_server(cls, value: str) -> str:
        try:
            address = ipaddress.ip_address(value)
            if getattr(address, "scope_id", None):
                raise ValueError("Scoped IPv6 addresses are not supported")
            return str(address)
        except ValueError as exc:
            raise ValueError("DNS server must be an IPv4 or IPv6 address") from exc


class NmapCreate(TargetedTestCreate):
    ports: list[Annotated[int, Field(strict=True, ge=1, le=65535)]] = Field(
        default_factory=lambda: [22, 80, 443], min_length=1, max_length=100
    )

    @field_validator("ports")
    @classmethod
    def valid_ports(cls, ports: list[int]) -> list[int]:
        if any(port < 1 or port > 65535 for port in ports) or len(set(ports)) != len(ports):
            raise ValueError("Ports must be unique integers between 1 and 65535")
        return ports


class IperfCreate(TargetedTestCreate):
    destination_agent_id: UUID | None = None
    port: int = Field(default=5201, ge=1024, le=65535)
    duration: int = Field(default=10, ge=1, le=60)


class SippCreate(TargetedTestCreate):
    port: int = Field(default=5060, ge=1, le=65535)
    service: str = Field(
        default="service", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    calls: int = Field(default=10, ge=1, le=1000)
    rate: int = Field(default=1, ge=1, le=20)
    concurrency: int = Field(default=10, ge=1, le=100)


class AgentResult(BaseModel):
    success: bool
    error: str | None = Field(default=None, max_length=1000)
    report: dict[str, Any] | None = None


class ResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    agent_id: UUID | None
    success: bool
    error: str | None
    metrics: dict
    created_at: datetime


class TestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_agent_id: UUID | None
    destination_agent_id: UUID | None
    engine: str
    status: str
    configuration: dict
    created_at: datetime
    completed_at: datetime | None
    results: list[ResultResponse]
