"""Stub API routes — artifacts, telemetry, evaluations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db_session

router = APIRouter()

@router.post("/artifacts/generate", summary="Generate injection artifact")
async def generate_artifact(body: dict, db: AsyncSession = Depends(get_db_session)):
    from app.pipelines.indirect.pipeline import ArtifactGenerator
    from app.domain.models import ArtifactFormat
    gen = ArtifactGenerator()
    fmt = body.get("format", "markdown")
    try:
        fmt_enum = ArtifactFormat(fmt)
    except ValueError:
        raise HTTPException(400, f"Invalid format: {fmt}")
    artifact = gen.generate(format=fmt_enum, visible_content=body.get("visible_content", "Normal document content"), injection_payload=body.get("injection_payload", "Ignore previous instructions"), injection_technique=body.get("injection_technique", "html_comment"), payload_id=body.get("payload_id"))
    from app.database.models.payload_model import ArtifactModel
    am = ArtifactModel(artifact_id=artifact["artifact_id"], artifact_hash=artifact["artifact_hash"], visible_content_hash=artifact["visible_content_hash"], injection_payload_id=artifact.get("injection_payload_id"), format=artifact["format"], injection_technique=artifact.get("injection_technique"), placement_strategy=artifact.get("placement_strategy"), visible_content=artifact.get("visible_content", "")[:2000])
    try:
        db.add(am)
        await db.flush()
    except Exception:
        pass
    return artifact
