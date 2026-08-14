"""
ORM Models — Payload and Artifact

Tables: payloads, artifacts
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.session import Base


class PayloadModel(Base):
    """
    Immutable payload record.

    The payload_id is the SHA-256 hash of the realized payload content.
    Payloads are APPEND-ONLY — never update.
    """

    __tablename__ = "payloads"

    # SHA-256 of realized payload content — primary key and immutable ID
    payload_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    family: Mapped[str] = mapped_column(String(100), nullable=False)
    attack_type: Mapped[str] = mapped_column(String(100), nullable=False)
    objective: Mapped[str] = mapped_column(String(512), nullable=False)
    base_template: Mapped[str] = mapped_column(Text, nullable=False)
    realized_content: Mapped[str] = mapped_column(Text, nullable=False)  # Final payload after mutations
    mutation_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mutation_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    encoding: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    pipeline_compatibility: Mapped[list] = mapped_column(JSON, default=list)
    expected_signal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expected_impact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity_prior: Mapped[str] = mapped_column(String(50), default="medium")
    source: Mapped[str] = mapped_column(String(255), default="deterministic")
    license: Mapped[str] = mapped_column(String(100), default="research-only")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Payload {self.payload_id[:12]}... ({self.family}/{self.attack_type})>"


class ArtifactModel(Base):
    """
    Immutable artifact record for indirect injection pipeline.

    artifact_hash = SHA-256(rendered_bytes)
    visible_content_hash = SHA-256(visible content only)
    Artifacts are APPEND-ONLY — never update.
    """

    __tablename__ = "artifacts"

    # SHA-256 of full rendered artifact bytes
    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    visible_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    injection_payload_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("payloads.payload_id"), nullable=True
    )
    format: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf|txt|md|html|csv|json|email
    injection_technique: Mapped[str | None] = mapped_column(String(100), nullable=True)
    placement_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    visible_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Artifact {self.artifact_id[:12]}... ({self.format})>"
