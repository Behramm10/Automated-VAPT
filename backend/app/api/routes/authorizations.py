"""Authorizations API routes."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session

# ─── Authorizations ───────────────────────────────────────────────────────────
authorizations = APIRouter()

@authorizations.post("/authorizations", status_code=201, summary="Create authorization record")
async def create_authorization(body: dict, db: AsyncSession = Depends(get_db_session)):
    from app.database.models.target_model import AuthorizationRecordModel, TargetModel
    from sqlalchemy import select
    target_id = body.get("target_id")
    if target_id:
        result = await db.execute(select(TargetModel).where(TargetModel.id == target_id))
        if not result.scalar_one_or_none():
            raise HTTPException(404, f"Target {target_id} not found")
    auth = AuthorizationRecordModel(
        id=str(uuid.uuid4()),
        target_id=target_id,
        authorized_by=body.get("authorized_by", "system"),
        scope=body.get("scope", {}),
        allowed_tools=body.get("allowed_tools", []),
        allowed_pipelines=body.get("allowed_pipelines", ["direct", "indirect", "multiturn", "tool_output"]),
        valid_from=datetime.fromisoformat(body["valid_from"]) if "valid_from" in body else datetime.now(timezone.utc),
        valid_until=datetime.fromisoformat(body["valid_until"]) if body.get("valid_until") else None,
        authorization_document=body.get("authorization_document"),
        authorization_reference=body.get("authorization_reference"),
        notes=body.get("notes"),
        status="active",
    )
    db.add(auth)
    await db.flush()
    return {"id": auth.id, "target_id": auth.target_id, "status": auth.status, "authorized_by": auth.authorized_by}

@authorizations.get("/authorizations", summary="List authorization records")
async def list_authorizations(db: AsyncSession = Depends(get_db_session)):
    from app.database.models.target_model import AuthorizationRecordModel
    result = await db.execute(select(AuthorizationRecordModel).order_by(AuthorizationRecordModel.created_at.desc()))
    auths = result.scalars().all()
    return [{"id": a.id, "target_id": a.target_id, "authorized_by": a.authorized_by, "status": a.status, "valid_from": a.valid_from.isoformat(), "valid_until": a.valid_until.isoformat() if a.valid_until else None, "created_at": a.created_at.isoformat()} for a in auths]

# Alias so main.py can use `authorizations.router`
router = authorizations

