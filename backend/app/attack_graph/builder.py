"""
Attack Graph Builder — Automatically builds attack graphs from telemetry.

Graph is generated from telemetry events, NOT manually authored.

Nodes: injection_event, agent_interpretation, behavioral_change, tool_execution, data_access, secondary_action
Edges: caused, triggered, followed_by, accessed, propagated_to
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.attack_graph_model import AttackGraphEdgeModel, AttackGraphModel, AttackGraphNodeModel
from app.database.models.finding_model import FindingModel
from app.database.models.telemetry_model import InstructionSpanModel, TelemetryEventModel

logger = structlog.get_logger(__name__)


async def build_attack_graph(db: AsyncSession, run_id: str) -> AttackGraphModel:
    """
    Build an attack graph for a completed run from telemetry.

    This automatically converts telemetry events and findings into a
    directed graph showing the attack flow.
    """
    # Get all findings for this run
    findings_result = await db.execute(select(FindingModel).where(FindingModel.run_id == run_id))
    findings = findings_result.scalars().all()

    # Get all telemetry events (ordered by sequence)
    events_result = await db.execute(
        select(TelemetryEventModel)
        .where(TelemetryEventModel.run_id == run_id)
        .order_by(TelemetryEventModel.sequence_number)
    )
    events = events_result.scalars().all()

    # Get instruction spans
    spans_result = await db.execute(select(InstructionSpanModel).where(InstructionSpanModel.run_id == run_id))
    spans = spans_result.scalars().all()

    # Create or update graph
    existing_result = await db.execute(select(AttackGraphModel).where(AttackGraphModel.run_id == run_id))
    graph = existing_result.scalar_one_or_none()

    if not graph:
        graph = AttackGraphModel(
            id=str(uuid.uuid4()),
            run_id=run_id,
        )
        db.add(graph)
        await db.flush()

    nodes: list[AttackGraphNodeModel] = []
    edges: list[AttackGraphEdgeModel] = []

    def add_node(node_type: str, label: str, event_id: str | None = None, **kwargs) -> AttackGraphNodeModel:
        node = AttackGraphNodeModel(
            id=str(uuid.uuid4()),
            graph_id=graph.id,
            node_type=node_type,
            event_id=event_id,
            label=label,
            timestamp=datetime.now(timezone.utc),
            **kwargs,
        )
        db.add(node)
        nodes.append(node)
        return node

    def add_edge(source: AttackGraphNodeModel, target: AttackGraphNodeModel, relationship: str, confidence: float = 1.0, label: str | None = None) -> AttackGraphEdgeModel:
        edge = AttackGraphEdgeModel(
            id=str(uuid.uuid4()),
            graph_id=graph.id,
            source_id=source.id,
            target_id=target.id,
            relationship_type=relationship,
            confidence=confidence,
            label=label,
        )
        db.add(edge)
        edges.append(edge)
        return edge

    # Build graph from findings and telemetry
    for finding in findings:
        # Per-finding subgraph
        session_id = finding.session_id

        # Find injection event (INPUT event with payload_id for this session)
        injection_events = [
            e for e in events
            if e.session_id == session_id
            and e.event_type == "INPUT"
            and e.payload_id is not None
        ]

        # Find tool call events for this session
        tool_call_events = [
            e for e in events
            if e.session_id == session_id
            and e.event_type == "TOOL_CALL"
        ]

        # Find response events
        response_events = [
            e for e in events
            if e.session_id == session_id
            and e.event_type == "RESPONSE"
        ]

        # Find instruction spans (origin-tagged)
        session_spans = [s for s in spans if s.session_id == session_id]

        prev_node = None

        # 1. Injection Event Node
        if injection_events:
            inj_event = injection_events[0]
            pipeline = finding.pipeline
            origin = inj_event.origin or "user"
            inj_node = add_node(
                "injection_event",
                f"Injection [{pipeline}] via {origin}",
                event_id=inj_event.id,
                origin=origin,
                pipeline=pipeline,
                session_id=session_id,
                description=f"Payload delivered via {pipeline} pipeline. Origin: {origin}.",
            )
            prev_node = inj_node

        # 2. Agent Interpretation Node (from response events)
        if response_events:
            resp_event = response_events[0]
            interp_node = add_node(
                "agent_interpretation",
                "Agent Interpretation",
                event_id=resp_event.id,
                session_id=session_id,
                description="Agent processed injected content and produced response.",
            )
            if prev_node:
                add_edge(prev_node, interp_node, "caused", label="payload_delivered")
            prev_node = interp_node

        # 3. Instruction Span Nodes (origin tracking)
        for span in session_spans:
            if span.origin in ("tool_output", "retrieved_content", "document"):
                span_node = add_node(
                    "behavioral_change",
                    f"Instruction Span [{span.origin}]",
                    session_id=session_id,
                    origin=span.origin,
                    description=f"Instruction-bearing content from {span.origin} consumed by agent.",
                )
                if prev_node:
                    add_edge(prev_node, span_node, "triggered", confidence=0.9, label=f"origin:{span.origin}")
                prev_node = span_node
                break  # Only add first significant span to avoid graph clutter

        # 4. Tool Execution Nodes
        for tc_event in tool_call_events:
            tool_name = tc_event.payload_data.get("tool_name", "unknown_tool")
            tool_node = add_node(
                "tool_execution",
                f"Tool: {tool_name}",
                event_id=tc_event.id,
                session_id=session_id,
                origin=tc_event.origin,
                description=f"Agent called {tool_name} with args: {str(tc_event.payload_data.get('tool_args', {}))[:100]}",
            )
            if prev_node:
                add_edge(prev_node, tool_node, "triggered", label=f"calls:{tool_name}")
            prev_node = tool_node

        # 5. Finding Node
        sev_map = {"critical": "#dc2626", "high": "#ea580c", "medium": "#d97706", "low": "#65a30d", "informational": "#6b7280"}
        finding_node = add_node(
            "finding",
            f"[{finding.severity.upper()}] {finding.title[:60]}",
            finding_id=finding.id,
            session_id=session_id,
            severity=finding.severity,
            description=finding.description[:200],
            metadata_={"risk_score": finding.risk_score, "confidence": finding.confidence, "color": sev_map.get(finding.severity, "#6b7280")},
        )
        if prev_node:
            add_edge(prev_node, finding_node, "propagated_to", label=f"finding:{finding.severity}", confidence=finding.confidence)

    await db.flush()

    # Update graph stats
    graph.node_count = len(nodes)
    graph.edge_count = len(edges)
    graph.max_chain_length = max((len([n for n in nodes if n.session_id == f.session_id]) for f in findings), default=0) if findings else 0
    await db.flush()

    logger.info("attack_graph_built", run_id=run_id, nodes=len(nodes), edges=len(edges), findings=len(findings))
    return graph
