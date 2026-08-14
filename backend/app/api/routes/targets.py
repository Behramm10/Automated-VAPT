"""
Targets API routes — register, list, discover capabilities.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.local_python import MockAgentRegistry, initialize_mock_agents
from app.database.models.target_model import TargetCapabilityModel, TargetModel
from app.database.session import get_db_session
from app.domain.models import AdapterType, Target, TargetCapability, TargetCreate, TargetStatus

router = APIRouter()


@router.post("/targets", response_model=dict, status_code=201, summary="Register a new target agent")
async def register_target(
    body: TargetCreate,
    db: AsyncSession = Depends(get_db_session),
):
    target = TargetModel(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        adapter_type=body.adapter_type.value,
        endpoint_url=body.endpoint_url,
        model_name=body.model_name,
        adapter_config=body.adapter_config,
        tags=body.tags,
        status="registered",
    )
    db.add(target)
    await db.flush()
    return {"id": target.id, "name": target.name, "status": target.status, "created_at": target.created_at.isoformat()}


@router.get("/targets", response_model=list[dict], summary="List all registered targets")
async def list_targets(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(TargetModel).order_by(TargetModel.created_at.desc()))
    targets = result.scalars().all()
    return [
        {
            "id": t.id, "name": t.name, "description": t.description,
            "adapter_type": t.adapter_type, "status": t.status,
            "tags": t.tags, "created_at": t.created_at.isoformat(),
            "last_assessed_at": t.last_assessed_at.isoformat() if t.last_assessed_at else None,
        }
        for t in targets
    ]


@router.get("/targets/{target_id}", response_model=dict, summary="Get target details")
async def get_target(target_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(TargetModel).where(TargetModel.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

    caps_result = await db.execute(
        select(TargetCapabilityModel).where(TargetCapabilityModel.target_id == target_id)
    )
    capabilities = caps_result.scalars().all()

    return {
        "id": target.id, "name": target.name, "description": target.description,
        "adapter_type": target.adapter_type, "endpoint_url": target.endpoint_url,
        "model_name": target.model_name, "status": target.status,
        "tags": target.tags, "created_at": target.created_at.isoformat(),
        "capabilities": [
            {"name": c.name, "description": c.description, "privilege_level": c.privilege_level, "is_destructive": c.is_destructive, "category": c.category}
            for c in capabilities
        ],
    }


@router.delete("/targets/{target_id}", status_code=204, summary="Delete a target")
async def delete_target(target_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(TargetModel).where(TargetModel.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")
    await db.delete(target)


@router.post("/targets/{target_id}/discover", response_model=dict, summary="Discover target capabilities")
async def discover_capabilities(target_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(TargetModel).where(TargetModel.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

    # Initialize mock agents if needed
    initialize_mock_agents()

    # Get capabilities from adapter
    capabilities: list[dict] = []
    if target.adapter_type in ("mock", "local_python"):
        agent_name = target.adapter_config.get("agent_name", "mock_support_agent")
        adapter = MockAgentRegistry.create_adapter(agent_name)
        if adapter:
            capabilities = await adapter.discover_capabilities()

    # Persist capabilities
    for cap in capabilities:
        # Check if already exists
        existing = await db.execute(
            select(TargetCapabilityModel).where(
                TargetCapabilityModel.target_id == target_id,
                TargetCapabilityModel.name == cap["name"],
            )
        )
        existing_cap = existing.scalar_one_or_none()
        if not existing_cap:
            cap_model = TargetCapabilityModel(
                id=str(uuid.uuid4()),
                target_id=target_id,
                name=cap["name"],
                description=cap.get("description"),
                parameters=cap.get("parameters", {}),
                is_destructive=cap.get("is_destructive", False),
                privilege_level=cap.get("privilege_level", "standard"),
                category=cap.get("category"),
            )
            db.add(cap_model)

    target.status = "active"
    await db.flush()

    return {
        "target_id": target_id,
        "capabilities_discovered": len(capabilities),
        "capabilities": capabilities,
    }
