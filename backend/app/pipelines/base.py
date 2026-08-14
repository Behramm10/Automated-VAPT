"""
Attack Pipeline Base Class

All pipelines implement: execute(test_case, adapter, db) -> InteractionTranscript
"""
from __future__ import annotations

import abc
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.adapters.base import InteractionTranscript, TargetAdapter
from app.database.session import AsyncSession

logger = structlog.get_logger(__name__)


class AttackPipeline(abc.ABC):
    """Abstract base class for all attack pipelines."""

    @property
    @abc.abstractmethod
    def pipeline_type(self) -> str:
        """Return pipeline type: direct|indirect|multiturn|tool_output"""
        ...

    @abc.abstractmethod
    async def execute(
        self,
        test_case_id: str,
        run_id: str,
        payload: Any,
        adapter: TargetAdapter,
        db: AsyncSession,
        config: dict[str, Any] | None = None,
        artifact: Any | None = None,
    ) -> InteractionTranscript:
        """
        Execute the attack pipeline for a given test case.

        Must:
        - Emit telemetry events (do NOT evaluate here)
        - Return the full interaction transcript
        - NOT decide whether the attack succeeded (that's the evaluator's job)
        """
        ...

    async def execute_control(
        self,
        test_case_id: str,
        run_id: str,
        benign_message: str,
        adapter: TargetAdapter,
        db: AsyncSession,
        config: dict[str, Any] | None = None,
    ) -> InteractionTranscript:
        """Execute a benign control run for comparison."""
        ...

    def new_session_id(self) -> str:
        return str(uuid.uuid4())
