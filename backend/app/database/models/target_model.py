"""
ORM Models — Target and Authorization

Tables: targets, target_capabilities, authorization_records
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.session import Base

# Use JSONB for PostgreSQL, JSON for SQLite
JsonType = JSONB().with_variant(JSON(), "sqlite")  # type: ignore[call-arg]


class TargetModel(Base):
    """Represents a registered AI agent target."""

    __tablename__ = "targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    adapter_type: Mapped[str] = mapped_column(String(50), nullable=False)  # rest|openai|local_python|langchain
    endpoint_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adapter_config: Mapped[dict] = mapped_column(JsonType, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="registered")  # registered|active|inactive|archived
    tags: Mapped[list] = mapped_column(JsonType, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    capabilities: Mapped[list["TargetCapabilityModel"]] = relationship(
        "TargetCapabilityModel", back_populates="target", cascade="all, delete-orphan"
    )
    authorization_records: Mapped[list["AuthorizationRecordModel"]] = relationship(
        "AuthorizationRecordModel", back_populates="target"
    )
    runs: Mapped[list["RunModel"]] = relationship("RunModel", back_populates="target")

    def __repr__(self) -> str:
        return f"<Target {self.id}: {self.name} ({self.adapter_type})>"


class TargetCapabilityModel(Base):
    """A tool/capability discovered on a target agent."""

    __tablename__ = "target_capabilities"
    __table_args__ = (UniqueConstraint("target_id", "name", name="uq_capability_target_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("targets.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict] = mapped_column(JsonType, default=dict)
    is_destructive: Mapped[bool] = mapped_column(Boolean, default=False)
    privilege_level: Mapped[str] = mapped_column(String(50), default="standard")  # standard|elevated|admin
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    target: Mapped["TargetModel"] = relationship("TargetModel", back_populates="capabilities")

    def __repr__(self) -> str:
        return f"<Capability {self.name} on target {self.target_id}>"


class AuthorizationRecordModel(Base):
    """Explicit authorization required before an assessment run can start."""

    __tablename__ = "authorization_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("targets.id", ondelete="CASCADE"), nullable=False)
    authorized_by: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[dict] = mapped_column(JsonType, default=dict)
    allowed_tools: Mapped[list] = mapped_column(JsonType, default=list)
    allowed_pipelines: Mapped[list] = mapped_column(JsonType, default=list)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorization_document: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorization_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active|revoked|expired
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    target: Mapped["TargetModel"] = relationship("TargetModel", back_populates="authorization_records")
    runs: Mapped[list["RunModel"]] = relationship("RunModel", back_populates="authorization_record")

    def __repr__(self) -> str:
        return f"<Authorization {self.id} for target {self.target_id} by {self.authorized_by}>"


# Import here to avoid circular imports but ensure models are registered
from app.database.models.run_model import RunModel  # noqa: E402, F401
