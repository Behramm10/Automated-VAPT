"""Runs API routes — create, start, cancel, status, replay."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.run_model import RunModel, TestPlanModel
from app.database.session import get_db_session
from app.domain.models import RunCreate

router = APIRouter()


@router.post("/runs", status_code=201, summary="Create a new assessment run")
async def create_run(body: RunCreate, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.target_model import TargetModel
    result = await db.execute(select(TargetModel).where(TargetModel.id == body.target_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, f"Target {body.target_id} not found")

    run = RunModel(
        id=str(uuid.uuid4()),
        target_id=body.target_id,
        authorization_id=body.authorization_id,
        name=body.name,
        description=body.description,
        pipelines=[p.value for p in body.pipelines] if body.pipelines else ["direct"],
        objectives=body.objectives or ["unauthorized_tool_call"],
        payload_families=body.payload_families or ["instruction_override"],
        risk_limits=body.risk_limits or {},
        config=body.config or {},
        status="registered",
    )
    db.add(run)
    await db.flush()
    return {"id": run.id, "name": run.name, "status": run.status, "created_at": run.created_at.isoformat()}


@router.get("/runs", summary="List assessment runs")
async def list_runs(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(RunModel).order_by(RunModel.created_at.desc()))
    runs = result.scalars().all()
    return [{"id": r.id, "name": r.name, "status": r.status, "target_id": r.target_id, "findings_count": r.findings_count, "critical_findings": r.critical_findings, "high_findings": r.high_findings, "medium_findings": r.medium_findings, "attack_success_rate": r.attack_success_rate, "created_at": r.created_at.isoformat(), "started_at": r.started_at.isoformat() if r.started_at else None, "completed_at": r.completed_at.isoformat() if r.completed_at else None} for r in runs]


@router.get("/runs/{run_id}", summary="Get run details")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(RunModel).where(RunModel.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    return {"id": run.id, "name": run.name, "status": run.status, "target_id": run.target_id, "authorization_id": run.authorization_id, "pipelines": run.pipelines, "objectives": run.objectives, "total_test_cases": run.total_test_cases, "completed_test_cases": run.completed_test_cases, "findings_count": run.findings_count, "critical_findings": run.critical_findings, "high_findings": run.high_findings, "medium_findings": run.medium_findings, "low_findings": run.low_findings, "attack_success_rate": run.attack_success_rate, "error_message": run.error_message, "created_at": run.created_at.isoformat(), "started_at": run.started_at.isoformat() if run.started_at else None, "completed_at": run.completed_at.isoformat() if run.completed_at else None}


@router.post("/runs/{run_id}/plan", summary="Generate test plan for a run")
async def generate_test_plan(run_id: str, db: AsyncSession = Depends(get_db_session)):
    from app.core.orchestrator.orchestrator import orchestrator
    result = await db.execute(select(RunModel).where(RunModel.id == run_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, f"Run {run_id} not found")
    test_plan = await orchestrator.generate_test_plan(db, run_id)
    return {"test_plan_id": test_plan.id, "test_cases": len(test_plan.test_cases), "status": test_plan.status}


@router.post("/runs/{run_id}/start", summary="Start an assessment run")
async def start_run(run_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(RunModel).where(RunModel.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")

    # Ensure test plan exists
    plan_result = await db.execute(select(TestPlanModel).where(TestPlanModel.run_id == run_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        from app.core.orchestrator.orchestrator import orchestrator
        await orchestrator.generate_test_plan(db, run_id)
        await db.commit()

    # Start in background
    from app.core.orchestrator.orchestrator import orchestrator
    background_tasks.add_task(orchestrator.start_run, run_id)

    return {"message": f"Run {run_id} started", "run_id": run_id, "status": "running"}


@router.post("/runs/{run_id}/cancel", summary="Cancel a run")
async def cancel_run(run_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(RunModel).where(RunModel.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    run.status = "cancelled"
    await db.flush()
    return {"message": f"Run {run_id} cancelled", "run_id": run_id}


@router.get("/runs/{run_id}/telemetry", summary="Get telemetry for a run")
async def get_run_telemetry(run_id: str, event_type: str | None = None, limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.telemetry_model import TelemetryEventModel
    query = select(TelemetryEventModel).where(TelemetryEventModel.run_id == run_id).order_by(TelemetryEventModel.sequence_number)
    if event_type:
        query = query.where(TelemetryEventModel.event_type == event_type.upper())
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    events = result.scalars().all()
    return [{"id": e.id, "event_type": e.event_type, "session_id": e.session_id, "turn_number": e.turn_number, "sequence_number": e.sequence_number, "payload_data": e.payload_data, "origin": e.origin, "timestamp": e.timestamp.isoformat()} for e in events]


@router.get("/runs/{run_id}/findings", summary="Get findings for a run")
async def get_run_findings(run_id: str, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.finding_model import FindingModel
    result = await db.execute(select(FindingModel).where(FindingModel.run_id == run_id).order_by(FindingModel.risk_score.desc()))
    findings = result.scalars().all()
    return [{"id": f.id, "title": f.title, "severity": f.severity, "risk_score": f.risk_score, "confidence": f.confidence, "status": f.status, "pipeline": f.pipeline, "objective": f.objective, "affected_tool": f.affected_tool, "first_seen": f.first_seen.isoformat()} for f in findings]


@router.get("/runs/{run_id}/attack-graph", summary="Get attack graph for a run")
async def get_attack_graph(run_id: str, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.attack_graph_model import AttackGraphModel, AttackGraphNodeModel, AttackGraphEdgeModel
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(AttackGraphModel)
        .where(AttackGraphModel.run_id == run_id)
        .options(selectinload(AttackGraphModel.nodes), selectinload(AttackGraphModel.edges))
    )
    graph = result.scalar_one_or_none()
    if not graph:
        raise HTTPException(404, "Attack graph not yet generated for this run")
    return {
        "id": graph.id, "run_id": run_id, "node_count": graph.node_count, "edge_count": graph.edge_count,
        "nodes": [{"id": n.id, "type": n.node_type, "label": n.label, "description": n.description, "origin": n.origin, "severity": n.severity, "pipeline": n.pipeline, "session_id": n.session_id, "metadata": n.metadata_ or {}} for n in graph.nodes],
        "edges": [{"id": e.id, "source": e.source_id, "target": e.target_id, "relationship": e.relationship_type, "confidence": e.confidence, "label": e.label} for e in graph.edges],
    }


@router.post("/runs/{run_id}/replay", summary="Replay a run from stored telemetry")
async def replay_run(run_id: str, session_id: str | None = None, db: AsyncSession = Depends(get_db_session)):
    """Replay stored telemetry — NEVER contacts the live target."""
    from app.database.models.telemetry_model import TelemetryEventModel
    from sqlalchemy import select as sa_select
    query = sa_select(TelemetryEventModel).where(TelemetryEventModel.run_id == run_id).order_by(TelemetryEventModel.sequence_number)
    if session_id:
        query = query.where(TelemetryEventModel.session_id == session_id)
    result = await db.execute(query.limit(500))
    events = result.scalars().all()
    return {
        "run_id": run_id,
        "replay_mode": True,
        "live_target_contacted": False,
        "events": [{"id": e.id, "event_type": e.event_type, "session_id": e.session_id, "turn_number": e.turn_number, "sequence_number": e.sequence_number, "payload_data": e.payload_data, "origin": e.origin, "timestamp": e.timestamp.isoformat()} for e in events],
    }
