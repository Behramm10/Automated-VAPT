"""
ORM Models — Report, Experiment, BenchmarkCase

Tables: reports, experiments, benchmark_cases
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.session import Base


class ReportModel(Base):
    """A generated VAPT report."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="generating")
    # generating|complete|failed

    # Generated content
    json_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # LLM sections
    llm_available: Mapped[bool] = mapped_column(default=False)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_priorities: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics snapshot
    metrics_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["RunModel"] = relationship("RunModel", back_populates="reports")  # type: ignore[name-defined]


class ExperimentModel(Base):
    """A baseline or ablation experiment."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    experiment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # baseline|ablation|comparison|benchmark

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    ablation_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # A|B|C|D|E|F|G (ablation variants)

    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending|running|completed|failed

    # Metrics
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    false_positive_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    false_negative_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    attack_success_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    reproducibility_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    causal_attribution_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    results: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    benchmark_cases: Mapped[list["BenchmarkCaseModel"]] = relationship(
        "BenchmarkCaseModel", back_populates="experiment", cascade="all, delete-orphan"
    )


class BenchmarkCaseModel(Base):
    """A single benchmark test case with ground truth label."""

    __tablename__ = "benchmark_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("experiments.id"), nullable=True)
    benchmark_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    split: Mapped[str] = mapped_column(String(50), default="development")
    # development|validation|held_out

    attack_type: Mapped[str] = mapped_column(String(100), nullable=False)
    pipeline: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_context: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    observed_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_sequence: Mapped[list] = mapped_column(JSON, default=list)
    vulnerability_label: Mapped[bool] = mapped_column(nullable=False)
    # True = vulnerable, False = not vulnerable
    predicted_label: Mapped[bool | None] = mapped_column(nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    experiment: Mapped["ExperimentModel"] = relationship("ExperimentModel", back_populates="benchmark_cases")


from app.database.models.run_model import RunModel  # noqa: E402, F401
