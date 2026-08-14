"""Findings, Artifacts, Telemetry, Evaluations, Reports, Experiments, Dashboard API routes."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db_session

# ─── Findings ────────────────────────────────────────────────────────────────
router = APIRouter()

@router.get("/findings", summary="List all findings")
async def list_findings(severity: str | None = None, status: str | None = None, pipeline: str | None = None, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.finding_model import FindingModel
    query = select(FindingModel).order_by(FindingModel.risk_score.desc()).limit(limit).offset(offset)
    if severity:
        query = query.where(FindingModel.severity == severity)
    if status:
        query = query.where(FindingModel.status == status)
    if pipeline:
        query = query.where(FindingModel.pipeline == pipeline)
    result = await db.execute(query)
    findings = result.scalars().all()
    return [{"id": f.id, "title": f.title, "severity": f.severity, "risk_score": f.risk_score, "confidence": f.confidence, "status": f.status, "pipeline": f.pipeline, "objective": f.objective, "run_id": f.run_id, "affected_tool": f.affected_tool, "first_seen": f.first_seen.isoformat()} for f in findings]

@router.get("/findings/{finding_id}", summary="Get finding details")
async def get_finding(finding_id: str, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.finding_model import FindingModel, EvidenceBundleModel
    result = await db.execute(select(FindingModel).where(FindingModel.id == finding_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(404, f"Finding {finding_id} not found")
    bundle_result = await db.execute(select(EvidenceBundleModel).where(EvidenceBundleModel.finding_id == finding_id))
    bundle = bundle_result.scalar_one_or_none()
    return {"id": f.id, "title": f.title, "description": f.description, "severity": f.severity, "risk_score": f.risk_score, "risk_score_breakdown": f.risk_score_breakdown, "confidence": f.confidence, "status": f.status, "pipeline": f.pipeline, "objective": f.objective, "run_id": f.run_id, "session_id": f.session_id, "payload_id": f.payload_id, "deterministic_signals": f.deterministic_signals, "llm_judge_result": f.llm_judge_result, "reproduction_steps": f.reproduction_steps, "remediation": f.remediation, "affected_target": f.affected_target, "affected_tool": f.affected_tool, "evidence_bundle": {"id": bundle.id, "bundle_hash": bundle.bundle_hash, "behavioral_delta": bundle.behavioral_delta, "tool_calls": bundle.tool_calls} if bundle else None, "first_seen": f.first_seen.isoformat()}

@router.patch("/findings/{finding_id}/status", summary="Update finding status")
async def update_finding_status(finding_id: str, body: dict, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.finding_model import FindingModel
    result = await db.execute(select(FindingModel).where(FindingModel.id == finding_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(404, f"Finding {finding_id} not found")
    new_status = body.get("status")
    valid_statuses = ["open", "triaged", "confirmed", "false_positive", "accepted_risk", "resolved"]
    if new_status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
    f.status = new_status
    await db.flush()
    return {"id": f.id, "status": f.status}
