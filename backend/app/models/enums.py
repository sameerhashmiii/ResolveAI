from enum import StrEnum


class Role(StrEnum):
    SUPPORT_ANALYST = "support_analyst"
    MANAGER = "manager"
    ADMINISTRATOR = "administrator"


class TicketStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class TicketPriority(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


_ROLE_ORDER = {
    Role.SUPPORT_ANALYST: 0,
    Role.MANAGER: 1,
    Role.ADMINISTRATOR: 2,
}


def role_allows(actual: Role, required: Role) -> bool:
    return _ROLE_ORDER[actual] >= _ROLE_ORDER[required]
