"""
ORM Models — Telemetry, InstructionSpan

Tables: telemetry_events, instruction_spans

APPEND-ONLY: telemetry_events and instruction_spans must never be updated.
Hash-chain integrity is implemented via event_hash + previous_event_hash.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.session import Base


class TelemetryEventModel(Base):
    """
    Immutable telemetry event.

    Every interaction, tool call, evaluation, and state change is recorded here.
    Implements an optional hash-chain for tamper-evident logging.
    """

    __tablename__ = "telemetry_events"
    __table_args__ = (
        Index("ix_telemetry_session_seq", "session_id", "sequence_number"),
        Index("ix_telemetry_payload", "payload_id"),
        Index("ix_telemetry_artifact", "artifact_id"),
        Index("ix_telemetry_run", "run_id"),
        Index("ix_telemetry_event_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=True)
    turn_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Monotonic, per-session

    # Classification
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # SESSION_STARTED|SESSION_ENDED|INPUT|RESPONSE|TOOL_CALL|TOOL_RESULT|
    # ARTIFACT_CREATED|ARTIFACT_RETRIEVED|EVALUATION|AUTHORIZATION_CHECK|ERROR

    # References
    payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    call_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # Tool call/result pairing

    # Content
    payload_data: Mapped[dict] = mapped_column(JSON, default=dict)
    origin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # system|developer|user|retrieved_content|document|tool_output|previous_agent_output|external_api

    # Hash-chain (optional tamper-evident chain)
    event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="telemetry_events")  # type: ignore[name-defined]
    instruction_spans: Mapped[list["InstructionSpanModel"]] = relationship(
        "InstructionSpanModel", back_populates="source_event", foreign_keys="InstructionSpanModel.source_event_id"
    )

    def __repr__(self) -> str:
        return f"<TelemetryEvent {self.event_type} seq={self.sequence_number} session={self.session_id}>"


class InstructionSpanModel(Base):
    """
    Tracks the origin of instruction-bearing content.

    This is a core research contribution — every instruction consumed by
    the agent is tagged with its source (system, user, tool_output, etc.)
    and linked to downstream behavior.
    """

    __tablename__ = "instruction_spans"
    __table_args__ = (
        Index("ix_instruction_span_event", "source_event_id"),
        Index("ix_instruction_span_run", "run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    span_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("telemetry_events.id"), nullable=True)

    # Origin classification — where did this instruction come from?
    origin: Mapped[str] = mapped_column(String(50), nullable=False)
    # system|developer|user|retrieved_content|document|tool_output|previous_agent_output|external_api

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of span content
    content_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)  # First 500 chars
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Downstream action tracking
    triggered_tool_call_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    triggered_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source_event: Mapped["TelemetryEventModel"] = relationship(
        "TelemetryEventModel", back_populates="instruction_spans", foreign_keys=[source_event_id]
    )

    def __repr__(self) -> str:
        return f"<InstructionSpan {self.span_id[:8]}... origin={self.origin}>"


from app.database.models.run_model import SessionModel  # noqa: E402, F401
