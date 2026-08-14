"""Payloads API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db_session
from app.payloads.engine import payload_engine, PAYLOAD_FAMILIES
from app.domain.models import PayloadGenerateRequest

router = APIRouter()

@router.get("/payloads", summary="List payload families and attack types")
async def list_payloads():
    return {"families": payload_engine.list_families(), "total_families": len(PAYLOAD_FAMILIES)}

@router.post("/payloads/generate", summary="Generate attack payloads")
async def generate_payloads(body: PayloadGenerateRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        payloads = payload_engine.generate(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    from app.database.models.payload_model import PayloadModel
    for p in payloads:
        pm = PayloadModel(payload_id=p.payload_id, family=p.family, attack_type=p.attack_type, objective=p.objective, base_template=p.base_template, realized_content=p.realized_content, mutation_strategy=p.mutation_strategy, mutation_seed=p.mutation_seed, pipeline_compatibility=p.pipeline_compatibility, expected_signal=p.expected_signal, severity_prior=p.severity_prior.value, source=p.source)
        try:
            db.add(pm)
            await db.flush()
        except Exception:
            pass
    return {"payloads": [p.model_dump() for p in payloads], "count": len(payloads)}
