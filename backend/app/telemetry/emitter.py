"""
Telemetry Emitter — Async event emission and persistence.

All telemetry events are:
  - append-only (never modified)
  - hash-chained for tamper-evident logging
  - sequenced monotonically per session
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.telemetry_model import TelemetryEventModel, InstructionSpanModel
from app.domain.models import EventType, InstructionOrigin

logger = structlog.get_logger(__name__)

# In-memory sequence counter per session
_sequence_counters: dict[str, int] = {}
# Last event hash per session for chain linking
_last_event_hashes: dict[str, str | None] = {}


def _next_sequence(session_id: str) -> int:
    """Return monotonically increasing sequence number for a session."""
    n = _sequence_counters.get(session_id, 0) + 1
    _sequence_counters[session_id] = n
    return n


def _compute_event_hash(
    event_id: str,
    event_type: str,
    payload_data: dict,
    timestamp: str,
    previous_hash: str | None,
) -> str:
    """SHA-256 hash of the event content for tamper-evident chaining."""
    content = json.dumps(
        {
            "event_id": event_id,
            "event_type": event_type,
            "payload_data": payload_data,
            "timestamp": timestamp,
            "previous_hash": previous_hash or "genesis",
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(content.encode()).hexdigest()


async def emit_event(
    db: AsyncSession,
    run_id: str,
    event_type: EventType,
    payload_data: dict[str, Any],
    session_id: str | None = None,
    turn_number: int | None = None,
    payload_id: str | None = None,
    artifact_id: str | None = None,
    call_id: str | None = None,
    origin: InstructionOrigin | None = None,
) -> TelemetryEventModel:
    """
    Emit and persist a single telemetry event.

    Returns the persisted event model.
    """
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    timestamp_str = now.isoformat()

    seq = _next_sequence(session_id or run_id)
    prev_hash = _last_event_hashes.get(session_id or run_id)

    event_hash = _compute_event_hash(event_id, event_type.value, payload_data, timestamp_str, prev_hash)
    _last_event_hashes[session_id or run_id] = event_hash

    event = TelemetryEventModel(
        id=event_id,
        run_id=run_id,
        session_id=session_id,
        turn_number=turn_number,
        sequence_number=seq,
        event_type=event_type.value,
        payload_id=payload_id,
        artifact_id=artifact_id,
        call_id=call_id,
        payload_data=payload_data,
        origin=origin.value if origin else None,
        event_hash=event_hash,
        previous_event_hash=prev_hash,
        timestamp=now,
    )

    db.add(event)
    await db.flush()  # Get ID without committing

    logger.debug(
        "telemetry_event_emitted",
        event_id=event_id,
        event_type=event_type.value,
        session_id=session_id,
        run_id=run_id,
        sequence_number=seq,
    )

    return event


async def emit_tool_call(
    db: AsyncSession,
    run_id: str,
    session_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    turn_number: int | None = None,
    origin: InstructionOrigin | None = None,
    call_id: str | None = None,
    payload_id: str | None = None,
) -> tuple[TelemetryEventModel, str]:
    """
    Emit a TOOL_CALL event.

    Returns (event, call_id) — call_id is used to pair with the result.
    """
    cid = call_id or str(uuid.uuid4())
    event = await emit_event(
        db=db,
        run_id=run_id,
        session_id=session_id,
        turn_number=turn_number,
        event_type=EventType.tool_call,
        payload_data={
            "tool_name": tool_name,
            "tool_args": tool_args,
            "call_id": cid,
        },
        call_id=cid,
        origin=origin,
        payload_id=payload_id,
    )
    return event, cid


async def emit_tool_result(
    db: AsyncSession,
    run_id: str,
    session_id: str,
    tool_name: str,
    result: Any,
    call_id: str,
    turn_number: int | None = None,
    is_mock: bool = True,
    origin: InstructionOrigin | None = None,
) -> TelemetryEventModel:
    """Emit a TOOL_RESULT event paired with a prior TOOL_CALL."""
    return await emit_event(
        db=db,
        run_id=run_id,
        session_id=session_id,
        turn_number=turn_number,
        event_type=EventType.tool_result,
        payload_data={
            "tool_name": tool_name,
            "result": result,
            "call_id": call_id,
            "is_mock": is_mock,
        },
        call_id=call_id,
        origin=origin,
    )


async def record_instruction_span(
    db: AsyncSession,
    run_id: str,
    session_id: str,
    content: str,
    origin: InstructionOrigin,
    source_event_id: str | None = None,
    start_offset: int | None = None,
    end_offset: int | None = None,
) -> InstructionSpanModel:
    """
    Record an instruction-bearing content span with its origin.

    This implements core instruction-origin tracking.
    """
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    span_id = str(uuid.uuid4())

    span = InstructionSpanModel(
        span_id=span_id,
        run_id=run_id,
        session_id=session_id,
        source_event_id=source_event_id,
        origin=origin.value,
        content_hash=content_hash,
        content_preview=content[:500] if content else None,
        start_offset=start_offset,
        end_offset=end_offset,
    )

    db.add(span)
    await db.flush()

    logger.debug(
        "instruction_span_recorded",
        span_id=span_id,
        origin=origin.value,
        content_hash=content_hash[:12],
    )

    return span


def reset_session_state(session_id: str) -> None:
    """Reset in-memory state for a session (call at session end)."""
    _sequence_counters.pop(session_id, None)
    _last_event_hashes.pop(session_id, None)
