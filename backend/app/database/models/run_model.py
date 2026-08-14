"""
ORM Models — Run, TestPlan, TestCase

Tables: runs, test_plans, test_cases
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.session import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB
    JsonType = JSONB().with_variant(JSON(), "sqlite")  # type: ignore[call-arg]
except Exception:
    JsonType = JSON()


class RunModel(Base):
    """An assessment run — the top-level entity for an assessment."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("targets.id"), nullable=False)
    authorization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("authorization_records.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="registered")
    # Status: registered|planned|running|awaiting_telemetry|evaluating|evidence_ready|reported|failed|cancelled

    pipelines: Mapped[list] = mapped_column(JSON, default=list)
    objectives: Mapped[list] = mapped_column(JSON, default=list)
    payload_families: Mapped[list] = mapped_column(JSON, default=list)
    risk_limits: Mapped[dict] = mapped_column(JSON, default=dict)
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Metrics (populated after evaluation)
    total_test_cases: Mapped[int] = mapped_column(Integer, default=0)
    completed_test_cases: Mapped[int] = mapped_column(Integer, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_findings: Mapped[int] = mapped_column(Integer, default=0)
    high_findings: Mapped[int] = mapped_column(Integer, default=0)
    medium_findings: Mapped[int] = mapped_column(Integer, default=0)
    low_findings: Mapped[int] = mapped_column(Integer, default=0)
    attack_success_rate: Mapped[float | None] = mapped_column(default=None)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    target: Mapped["TargetModel"] = relationship("TargetModel", back_populates="runs")  # type: ignore[name-defined]
    authorization_record: Mapped["AuthorizationRecordModel"] = relationship(  # type: ignore[name-defined]
        "AuthorizationRecordModel", back_populates="runs"
    )
    test_plan: Mapped["TestPlanModel"] = relationship(
        "TestPlanModel", back_populates="run", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list["SessionModel"]] = relationship(
        "SessionModel", back_populates="run", cascade="all, delete-orphan"
    )
    findings: Mapped[list["FindingModel"]] = relationship(  # type: ignore[name-defined]
        "FindingModel", back_populates="run", cascade="all, delete-orphan"
    )
    reports: Mapped[list["ReportModel"]] = relationship(  # type: ignore[name-defined]
        "ReportModel", back_populates="run", cascade="all, delete-orphan"
    )


class TestPlanModel(Base):
    """Generated test plan for a run."""

    __tablename__ = "test_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft|approved|executing|completed
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generation_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    run: Mapped["RunModel"] = relationship("RunModel", back_populates="test_plan")
    test_cases: Mapped[list["TestCaseModel"]] = relationship(
        "TestCaseModel", back_populates="test_plan", cascade="all, delete-orphan"
    )


class TestCaseModel(Base):
    """A single test case within a test plan."""

    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False
    )
    pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256 of payload
    objective: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_required: Mapped[bool] = mapped_column(default=True)
    expected_signal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(50), default="medium")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    max_turns: Mapped[int] = mapped_column(Integer, default=6)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|running|completed|failed|skipped
    result: Mapped[str | None] = mapped_column(String(50), nullable=True)  # success|failure|inconclusive
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    test_plan: Mapped["TestPlanModel"] = relationship("TestPlanModel", back_populates="test_cases")
    sessions: Mapped[list["SessionModel"]] = relationship("SessionModel", back_populates="test_case")


class SessionModel(Base):
    """A single agent interaction session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("test_cases.id"), nullable=True
    )
    session_type: Mapped[str] = mapped_column(String(50), default="attack")  # attack|control
    pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="created")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    behavioral_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    degradation_curve: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    run: Mapped["RunModel"] = relationship("RunModel", back_populates="sessions")
    test_case: Mapped["TestCaseModel"] = relationship("TestCaseModel", back_populates="sessions")
    telemetry_events: Mapped[list["TelemetryEventModel"]] = relationship(  # type: ignore[name-defined]
        "TelemetryEventModel", back_populates="session"
    )


# Avoid circular imports
from app.database.models.target_model import TargetModel, AuthorizationRecordModel  # noqa: E402, F401
