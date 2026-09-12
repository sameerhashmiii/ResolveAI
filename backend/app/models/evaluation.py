from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_evaluation_runs_status",
        ),
        CheckConstraint("sample_count > 0", name="ck_evaluation_runs_sample_count"),
        CheckConstraint("length(dataset_checksum) = 64", name="ck_evaluation_runs_checksum"),
        CheckConstraint("synthetic", name="ck_evaluation_runs_synthetic"),
        CheckConstraint(
            "(status = 'running' AND completed_at IS NULL AND error_code IS NULL) OR "
            "(status = 'completed' AND completed_at IS NOT NULL AND error_code IS NULL) OR "
            "(status = 'failed' AND completed_at IS NOT NULL AND error_code IS NOT NULL)",
            name="ck_evaluation_runs_lifecycle",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_evaluation_runs_timestamps",
        ),
        Index("ix_evaluation_runs_status_created", "status", "created_at"),
        Index("ix_evaluation_runs_dataset_created", "dataset_version", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    runner_version: Mapped[str] = mapped_column(String(30), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    methodology: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
