"""Evaluations API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db_session

router = APIRouter()

@router.get("/evaluations", summary="List evaluations")
async def list_evaluations(run_id: str | None = None, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.finding_model import EvaluationModel
    query = select(EvaluationModel).order_by(EvaluationModel.created_at.desc()).limit(100)
    if run_id:
        query = query.where(EvaluationModel.run_id == run_id)
    result = await db.execute(query)
    evals = result.scalars().all()
    return [{"id": e.id, "run_id": e.run_id, "verdict": e.verdict, "confidence": e.confidence, "final_severity": e.final_severity, "risk_score": e.risk_score, "signals_count": e.signals_count, "created_at": e.created_at.isoformat()} for e in evals]
