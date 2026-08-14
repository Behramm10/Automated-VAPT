"""
ORM Models — AttackGraph, AttackGraphNode, AttackGraphEdge

Tables: attack_graphs, attack_graph_nodes, attack_graph_edges

Attack graphs are automatically built from telemetry — never manually authored.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.session import Base


class AttackGraphModel(Base):
    """Root of an attack graph for a run."""

    __tablename__ = "attack_graphs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False, unique=True)
    node_count: Mapped[int] = mapped_column(default=0)
    edge_count: Mapped[int] = mapped_column(default=0)
    max_chain_length: Mapped[int] = mapped_column(default=0)
    graph_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    nodes: Mapped[list["AttackGraphNodeModel"]] = relationship(
        "AttackGraphNodeModel", back_populates="graph", cascade="all, delete-orphan"
    )
    edges: Mapped[list["AttackGraphEdgeModel"]] = relationship(
        "AttackGraphEdgeModel", back_populates="graph", cascade="all, delete-orphan"
    )


class AttackGraphNodeModel(Base):
    """A node in the attack graph."""

    __tablename__ = "attack_graph_nodes"
    __table_args__ = (
        Index("ix_node_graph", "graph_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    graph_id: Mapped[str] = mapped_column(String(36), ForeignKey("attack_graphs.id", ondelete="CASCADE"))
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # injection_event|agent_interpretation|behavioral_change|tool_execution|
    # data_access|secondary_action|finding

    event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    finding_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pipeline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    graph: Mapped["AttackGraphModel"] = relationship("AttackGraphModel", back_populates="nodes")
    outgoing_edges: Mapped[list["AttackGraphEdgeModel"]] = relationship(
        "AttackGraphEdgeModel", back_populates="source_node", foreign_keys="AttackGraphEdgeModel.source_id"
    )
    incoming_edges: Mapped[list["AttackGraphEdgeModel"]] = relationship(
        "AttackGraphEdgeModel", back_populates="target_node", foreign_keys="AttackGraphEdgeModel.target_id"
    )


class AttackGraphEdgeModel(Base):
    """A directed edge in the attack graph."""

    __tablename__ = "attack_graph_edges"
    __table_args__ = (
        Index("ix_edge_graph", "graph_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    graph_id: Mapped[str] = mapped_column(String(36), ForeignKey("attack_graphs.id", ondelete="CASCADE"))
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("attack_graph_nodes.id"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("attack_graph_nodes.id"), nullable=False)

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # caused|triggered|followed_by|accessed|propagated_to

    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    graph: Mapped["AttackGraphModel"] = relationship("AttackGraphModel", back_populates="edges")
    source_node: Mapped["AttackGraphNodeModel"] = relationship(
        "AttackGraphNodeModel", back_populates="outgoing_edges", foreign_keys=[source_id]
    )
    target_node: Mapped["AttackGraphNodeModel"] = relationship(
        "AttackGraphNodeModel", back_populates="incoming_edges", foreign_keys=[target_id]
    )
