import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SOURCE_ID = re.compile(r"^[A-Z]+-[0-9]{3,6}$")


class StrictRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def require_aware_datetimes(cls, value: object) -> object:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("timestamps must include a timezone")
        return value


class Manifest(StrictRow):
    actual_counts: dict[str, int]
    category_distribution: dict[str, int]
    checksums: dict[str, str]
    dataset_version: str = Field(min_length=1, max_length=100)
    generated_at: datetime
    generator: str
    requested_counts: dict[str, int]
    schema_version: str
    seed: int
    simulation_window: dict[str, datetime]
    synthetic_disclaimer: str = Field(min_length=1)

    @field_validator("checksums")
    @classmethod
    def checksums_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        if any(re.fullmatch(r"[0-9a-f]{64}", checksum) is None for checksum in value.values()):
            raise ValueError("manifest checksums must be lowercase SHA-256")
        return value


class LocationRow(StrictRow):
    location_id: str = Field(pattern=r"^LOC-[0-9]{3}$")
    name: str = Field(min_length=1, max_length=120)
    office_network: str
    subnet: str
    vpn_gateway: str
    wifi_ssids: list[str]
    dns_servers: list[str]
    access_patterns: list[str]
    infrastructure_notice: str

    def network_metadata(self) -> dict[str, Any]:
        return self.model_dump(exclude={"location_id", "name"})


class ApplicationRow(StrictRow):
    application_id: str = Field(pattern=r"^APP-[0-9]{3}$")
    name: str = Field(min_length=1, max_length=120)
    owner: str
    criticality: Literal["low", "medium", "high", "critical"]
    environment: str
    normal_availability: float = Field(ge=0, le=100)
    dependencies: list[str]


class TicketRow(StrictRow):
    ticket_id: str = Field(pattern=r"^TKT-[0-9]{6}$")
    created_at: datetime
    updated_at: datetime
    user_id: str = Field(pattern=r"^USR-[0-9]{5}$")
    location_id: str = Field(pattern=r"^LOC-[0-9]{3}$")
    location_name: str
    affected_application_id: str | None = Field(default=None, pattern=r"^APP-[0-9]{3}$")
    affected_device: str | None
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    category: str
    subcategory: str
    priority: Literal["P1", "P2", "P3", "P4"]
    status: str
    assigned_team: str
    resolution: str | None
    resolution_code: str | None
    resolution_time_minutes: int | None = Field(default=None, ge=0)
    incident_id: str | None = Field(default=None, pattern=r"^INC-[0-9]{4}$")
    knowledge_article_ids: list[str]
    related_ticket_ids: list[str]
    ai_analysis: None
    ai_confidence: None

    @model_validator(mode="after")
    def valid_window(self) -> "TicketRow":
        if self.updated_at < self.created_at:
            raise ValueError("ticket updated_at precedes created_at")
        return self


class IncidentRow(StrictRow):
    incident_id: str = Field(pattern=r"^INC-[0-9]{4}$")
    title: str
    start_at: datetime
    end_at: datetime
    affected_location_ids: list[str]
    affected_application_ids: list[str]
    affected_user_ids: list[str]
    affected_services: list[str]
    public_summary: str
    resolution: str
    related_ticket_ids: list[str]

    @model_validator(mode="after")
    def valid_window(self) -> "IncidentRow":
        if self.end_at < self.start_at:
            raise ValueError("incident end_at precedes start_at")
        return self


class TelemetryRow(StrictRow):
    timestamp: datetime
    service: str = Field(min_length=1, max_length=120)
    location_id: str = Field(pattern=r"^LOC-[0-9]{3}$")
    availability: float = Field(ge=0, le=100)
    latency_ms: int = Field(ge=0)
    error_rate: float = Field(ge=0, le=100)
    incident_id: str | None = Field(default=None, pattern=r"^INC-[0-9]{4}$")


class LogRow(StrictRow):
    host: str = Field(min_length=1, max_length=255)
    timestamp: datetime
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    service: str = Field(min_length=1, max_length=120)
    location_id: str = Field(pattern=r"^LOC-[0-9]{3}$")
    message: str = Field(min_length=1, max_length=2000)
    incident_id: str | None = Field(default=None, pattern=r"^INC-[0-9]{4}$")
