from uuid import uuid4

from app.models.assessments import RootCauseAssessment
from app.models.enums import RecommendationActionType, RecommendationStatus
from app.models.recommendations import Recommendation

HIGH_IMPACT_TERMS = (
    "account reset",
    "reset account",
    "mfa reset",
    "reset mfa",
    "access change",
    "permission change",
    "change permissions",
    "change access",
    "change permission",
    "grant access",
    "revoke access",
    "unlock account",
    "disable account",
    "user disable",
    "disable user",
    "credential action",
    "credential reset",
    "reset credential",
)


def classify_action(instructions: str, *, requires_escalation: bool) -> RecommendationActionType:
    normalized = " ".join(instructions.casefold().split())
    if any(term in normalized for term in HIGH_IMPACT_TERMS):
        return RecommendationActionType.HIGH_IMPACT
    if requires_escalation:
        return RecommendationActionType.ESCALATE
    if any(term in normalized for term in ("ask ", "request ", "collect ", "confirm ")):
        return RecommendationActionType.REQUEST_INFORMATION
    return RecommendationActionType.TROUBLESHOOT


def recommendation_from_assessment(assessment: RootCauseAssessment) -> Recommendation:
    if assessment.recommendation is None:
        raise ValueError("Completed assessment requires recommendation instructions")
    instructions = assessment.recommendation.strip()
    action_type = classify_action(
        instructions, requires_escalation=assessment.requires_escalation
    )
    title = {
        RecommendationActionType.ESCALATE: "Escalate for human investigation",
        RecommendationActionType.HIGH_IMPACT: "High-impact support action",
        RecommendationActionType.REQUEST_INFORMATION: "Request additional information",
        RecommendationActionType.TROUBLESHOOT: "Recommended troubleshooting",
    }[action_type]
    return Recommendation(
        id=uuid4(),
        ticket_id=assessment.ticket_id,
        assessment_id=assessment.id,
        title=title,
        original_instructions=instructions,
        instructions=instructions,
        action_type=action_type,
        requires_approval=True,
        status=RecommendationStatus.PROPOSED,
    )
