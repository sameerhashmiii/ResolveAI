from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.domain import TimestampMixin, User
from app.models.enums import (
    RecommendationActionType,
    RecommendationStatus,
    ResponseGeneratedBy,
    SupportResponseStatus,
)

recommendation_action_enum = Enum(
    RecommendationActionType,
    name="recommendation_action_type",
    values_callable=lambda enum: [item.value for item in enum],
)
recommendation_status_enum = Enum(
    RecommendationStatus,
    name="recommendation_status",
    values_callable=lambda enum: [item.value for item in enum],
)
response_generated_by_enum = Enum(
    ResponseGeneratedBy,
    name="response_generated_by",
    values_callable=lambda enum: [item.value for item in enum],
)
support_response_status_enum = Enum(
    SupportResponseStatus,
    name="support_response_status",
    values_callable=lambda enum: [item.value for item in enum],
)


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_ticket_created", "ticket_id", "created_at"),
        CheckConstraint("requires_approval", name="ck_recommendations_requires_approval"),
        CheckConstraint(
            "(status = 'proposed' AND decided_by_id IS NULL AND decision_reason IS NULL "
            "AND decided_at IS NULL) OR (status != 'proposed' AND decided_by_id IS NOT NULL "
            "AND decision_reason IS NOT NULL AND decided_at IS NOT NULL)",
            name="ck_recommendations_decision_fields",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("root_cause_assessments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    original_instructions: Mapped[str] = mapped_column(String(1000), nullable=False)
    instructions: Mapped[str] = mapped_column(String(1000), nullable=False)
    action_type: Mapped[RecommendationActionType] = mapped_column(
        recommendation_action_enum, nullable=False
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        recommendation_status_enum,
        default=RecommendationStatus.PROPOSED,
        server_default=RecommendationStatus.PROPOSED.value,
        nullable=False,
    )
    decided_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decision_reason: Mapped[str | None] = mapped_column(String(500))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[User | None] = relationship(foreign_keys=[decided_by_id], lazy="joined")


class SupportResponse(TimestampMixin, Base):
    __tablename__ = "support_responses"
    __table_args__ = (
        Index("ix_support_responses_ticket_created", "ticket_id", "created_at"),
        Index(
            "uq_support_responses_active_draft",
            "ticket_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
        CheckConstraint("mode IN ('local_demo', 'hosted')", name="ck_support_responses_mode"),
        CheckConstraint(
            "status != 'approved' OR (final_body IS NOT NULL AND approved_by_id IS NOT NULL "
            "AND approved_at IS NOT NULL)",
            name="ck_support_responses_approved_fields",
        ),
        CheckConstraint(
            "status != 'rejected' OR (rejected_by_id IS NOT NULL AND rejection_reason IS NOT NULL "
            "AND rejected_at IS NOT NULL)",
            name="ck_support_responses_rejected_fields",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("root_cause_assessments.id", ondelete="CASCADE"), nullable=False
    )
    recommendation_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
    )
    generated_by: Mapped[ResponseGeneratedBy] = mapped_column(
        response_generated_by_enum, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    draft_body: Mapped[str] = mapped_column(Text, nullable=False)
    final_body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SupportResponseStatus] = mapped_column(
        support_response_status_enum, nullable=False
    )
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rejected_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id], lazy="joined")
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_id], lazy="joined")
    rejected_by: Mapped[User | None] = relationship(foreign_keys=[rejected_by_id], lazy="joined")
