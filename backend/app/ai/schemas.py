from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Category(StrEnum):
    VPN = "vpn"
    NETWORK = "network"
    WIFI = "wifi"
    EMAIL = "email"
    PASSWORD = "password"
    ACCOUNT_ACCESS = "account_access"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    APPLICATION = "application"
    SECURITY = "security"
    OTHER = "other"


class AffectedScope(StrEnum):
    INDIVIDUAL = "individual"
    MULTIPLE_USERS = "multiple_users"
    ORGANIZATION = "organization"
    UNKNOWN = "unknown"


class Urgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExtractedEntities(StrictModel):
    user: str | None = Field(max_length=200)
    location: str | None = Field(max_length=200)
    application: str | None = Field(max_length=200)
    device: str | None = Field(max_length=200)
    issue_type: str | None = Field(max_length=100)
    affected_scope: AffectedScope
    urgency: Urgency


class PriorityFactors(StrictModel):
    affected_scope: AffectedScope
    business_critical: bool
    production_outage: bool
    security_risk: bool
    workaround_available: bool
    information_request: bool


class ProviderSignals(StrictModel):
    category: Category
    category_confidence: float = Field(ge=0, le=1)
    entities: ExtractedEntities
    priority_factors: PriorityFactors


class TicketAnalysisInput(StrictModel):
    title: str
    description: str
    requester_name: str
    requester_department: str | None = None
    location: str | None = None
    device: str | None = None
    application: str | None = None
