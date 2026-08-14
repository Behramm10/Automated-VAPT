"""
ORM Models — Finding, Evaluation, EvaluationSignal, EvidenceBundle

Tables: findings, evaluations, evaluation_signals, evidence_bundles
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.session import Base


class FindingModel(Base):
    """A confirmed or suspected security vulnerability."""

    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_run_severity", "run_id", "severity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=True)
    test_case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    # informational|low|medium|high|critical

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    objective: Mapped[str] = mapped_column(String(255), nullable=False)

    payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open")
    # open|triaged|confirmed|false_positive|accepted_risk|resolved

    attack_path: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    deterministic_signals: Mapped[list] = mapped_column(JSON, default=list)
    llm_judge_result: Mapped[dict] = mapped_column(JSON, default=dict)
    reproduction_steps: Mapped[list] = mapped_column(JSON, default=list)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    references: Mapped[list] = mapped_column(JSON, default=list)

    affected_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affected_tool: Mapped[str | None] = mapped_column(String(255), nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    run: Mapped["RunModel"] = relationship("RunModel", back_populates="findings")  # type: ignore[name-defined]
    evaluation: Mapped["EvaluationModel"] = relationship("EvaluationModel", back_populates="finding", uselist=False)
    evidence_bundle: Mapped["EvidenceBundleModel"] = relationship(
        "EvidenceBundleModel", back_populates="finding", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Finding {self.id[:8]}... [{self.severity.upper()}] {self.title}>"


class EvaluationModel(Base):
    """Evaluation result for a test case or session."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=True)
    finding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("findings.id"), nullable=True)
    test_case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=True)

    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    # vulnerable|not_vulnerable|inconclusive|ambiguous|review_required

    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    deterministic_verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    final_severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    signals_count: Mapped[int] = mapped_column(Integer, default=0)
    high_confidence_signals: Mapped[int] = mapped_column(Integer, default=0)
    evaluator_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    evaluation_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    finding: Mapped["FindingModel"] = relationship("FindingModel", back_populates="evaluation")
    signals: Mapped[list["EvaluationSignalModel"]] = relationship(
        "EvaluationSignalModel", back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationSignalModel(Base):
    """Individual evaluation signal (deterministic or LLM-based)."""

    __tablename__ = "evaluation_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluations.id"), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # unauthorized_tool_call|unauthorized_data_access|secret_disclosure|
    # instruction_hierarchy_violation|injected_content_triggered_action|
    # tool_output_instruction_following|task_deviation|chained_unauthorized_action

    source: Mapped[str] = mapped_column(String(50), nullable=False)  # deterministic|llm_judge
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity_contribution: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_event_ids: Mapped[list] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    evaluation: Mapped["EvaluationModel"] = relationship("EvaluationModel", back_populates="signals")


class EvidenceBundleModel(Base):
    """
    Immutable evidence bundle for a finding.

    Contains all artifacts needed to reproduce and verify the finding.
    """

    __tablename__ = "evidence_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("findings.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)

    bundle_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of bundle content
    payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    control_transcript: Mapped[dict] = mapped_column(JSON, default=dict)
    attack_transcript: Mapped[dict] = mapped_column(JSON, default=dict)
    behavioral_delta: Mapped[dict] = mapped_column(JSON, default=dict)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    instruction_spans: Mapped[list] = mapped_column(JSON, default=list)
    telemetry_event_ids: Mapped[list] = mapped_column(JSON, default=list)
    evaluation_signals: Mapped[list] = mapped_column(JSON, default=list)
    severity_calculation: Mapped[dict] = mapped_column(JSON, default=dict)
    attack_graph_path: Mapped[list] = mapped_column(JSON, default=list)
    reproduction_steps: Mapped[list] = mapped_column(JSON, default=list)

    # Sensitive data is redacted before storage
    is_redacted: Mapped[bool] = mapped_column(default=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # Downloaded bundle

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    finding: Mapped["FindingModel"] = relationship("FindingModel", back_populates="evidence_bundle")

    def __repr__(self) -> str:
        return f"<EvidenceBundle {self.id[:8]}... for finding {self.finding_id}>"


from app.database.models.run_model import RunModel, SessionModel, TestCaseModel  # noqa: E402, F401
