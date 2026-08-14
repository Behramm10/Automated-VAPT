"""Dashboard and Experiments API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session

# ─── Dashboard ────────────────────────────────────────────────────────────────
router = APIRouter()


@router.get("/dashboard/summary", summary="Get dashboard metrics summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db_session)):
    from app.database.models.run_model import RunModel
    from app.database.models.finding_model import FindingModel
    from app.database.models.target_model import TargetModel

    # Aggregate counts
    total_runs = (await db.execute(select(func.count()).select_from(RunModel))).scalar() or 0
    active_runs = (await db.execute(select(func.count()).select_from(RunModel).where(RunModel.status == "running"))).scalar() or 0
    total_findings = (await db.execute(select(func.count()).select_from(FindingModel))).scalar() or 0
    critical = (await db.execute(select(func.count()).select_from(FindingModel).where(FindingModel.severity == "critical"))).scalar() or 0
    high = (await db.execute(select(func.count()).select_from(FindingModel).where(FindingModel.severity == "high"))).scalar() or 0
    medium = (await db.execute(select(func.count()).select_from(FindingModel).where(FindingModel.severity == "medium"))).scalar() or 0
    low = (await db.execute(select(func.count()).select_from(FindingModel).where(FindingModel.severity.in_(["low", "informational"])))).scalar() or 0

    # Recent findings
    recent_findings_result = await db.execute(select(FindingModel).order_by(FindingModel.first_seen.desc()).limit(5))
    recent_findings = recent_findings_result.scalars().all()

    # Recent runs
    recent_runs_result = await db.execute(select(RunModel).order_by(RunModel.created_at.desc()).limit(5))
    recent_runs = recent_runs_result.scalars().all()

    # Pipeline distribution
    pipeline_results = await db.execute(select(FindingModel.pipeline, func.count()).group_by(FindingModel.pipeline))
    pipeline_dist = dict(pipeline_results.all())

    asr = (critical + high) / max(total_findings, 1)

    return {
        "total_assessments": total_runs,
        "active_runs": active_runs,
        "total_findings": total_findings,
        "critical_findings": critical,
        "high_findings": high,
        "medium_findings": medium,
        "low_findings": low,
        "attack_success_rate": round(asr, 3),
        "detection_precision": None,
        "detection_recall": None,
        "f1_score": None,
        "false_positive_rate": None,
        "pipeline_distribution": pipeline_dist,
        "severity_distribution": {"critical": critical, "high": high, "medium": medium, "low": low},
        "recent_findings": [{"id": f.id, "title": f.title, "severity": f.severity, "risk_score": f.risk_score, "pipeline": f.pipeline, "first_seen": f.first_seen.isoformat()} for f in recent_findings],
        "recent_runs": [{"id": r.id, "name": r.name, "status": r.status, "findings_count": r.findings_count, "created_at": r.created_at.isoformat()} for r in recent_runs],
    }
