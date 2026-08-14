"""
FastAPI dependencies — common reusable dependencies.
"""
from app.database.session import get_db_session

__all__ = ["get_db_session"]
