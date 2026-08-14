"""Telemetry API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db_session

router = APIRouter()

@router.get("/telemetry", summary="Query telemetry events")
async def query_telemetry(run_id: str | None = None, session_id: str | None = None, event_type: str | None = None, origin: str | None = None, limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.telemetry_model import TelemetryEventModel
    query = select(TelemetryEventModel).order_by(TelemetryEventModel.timestamp.desc()).limit(limit).offset(offset)
    if run_id:
        query = query.where(TelemetryEventModel.run_id == run_id)
    if session_id:
        query = query.where(TelemetryEventModel.session_id == session_id)
    if event_type:
        query = query.where(TelemetryEventModel.event_type == event_type.upper())
    if origin:
        query = query.where(TelemetryEventModel.origin == origin)
    result = await db.execute(query)
    events = result.scalars().all()
    return [{"id": e.id, "run_id": e.run_id, "session_id": e.session_id, "turn_number": e.turn_number, "sequence_number": e.sequence_number, "event_type": e.event_type, "payload_data": e.payload_data, "origin": e.origin, "event_hash": e.event_hash, "timestamp": e.timestamp.isoformat()} for e in events]
