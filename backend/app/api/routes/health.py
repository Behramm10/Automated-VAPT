"""Health check endpoints."""
from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/health", summary="Health check")
async def health():
    return {"status": "healthy", "version": settings.app_version, "env": settings.app_env}

@router.get("/health/ready", summary="Readiness check")
async def ready():
    try:
        from app.database.session import get_engine
        engine = get_engine()
        async with engine.connect():
            pass
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": str(e)})
