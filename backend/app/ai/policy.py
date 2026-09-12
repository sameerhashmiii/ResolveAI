from app.ai.schemas import AffectedScope, PriorityFactors, Urgency
from app.models.enums import TicketPriority


def assign_priority(factors: PriorityFactors, urgency: Urgency) -> TicketPriority:
    """Assign priority from validated policy factors; urgency alone cannot create P1."""
    if (
        factors.production_outage
        and factors.affected_scope == AffectedScope.ORGANIZATION
        and urgency == Urgency.CRITICAL
    ):
        return TicketPriority.P1
    if factors.security_risk or (
        factors.affected_scope in {AffectedScope.MULTIPLE_USERS, AffectedScope.ORGANIZATION}
        and (urgency in {Urgency.HIGH, Urgency.CRITICAL} or factors.business_critical)
    ) or (factors.business_critical and not factors.workaround_available):
        return TicketPriority.P2
    if factors.information_request or (
        urgency == Urgency.LOW
        and not factors.business_critical
        and not factors.production_outage
        and not factors.security_risk
    ):
        return TicketPriority.P4
    return TicketPriority.P3
