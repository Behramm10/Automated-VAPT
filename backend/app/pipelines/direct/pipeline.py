"""
Pipeline 1 — Direct Prompt Injection

Flow: Payload → Target Adapter → Agent → Tool Layer → Telemetry → Evaluator → Finding

Tests:
  - system prompt disclosure
  - unauthorized tool invocation
  - instruction hierarchy bypass
  - sensitive information extraction
  - restricted actions
  - privilege escalation

Every attack has a matched benign control run for behavioral delta comparison.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.adapters.base import AgentInteraction, InteractionTranscript, TargetAdapter
from app.database.models.run_model import SessionModel
from app.database.session import AsyncSession
from app.domain.models import EventType, InstructionOrigin
from app.pipelines.base import AttackPipeline
from app.telemetry.emitter import emit_event, emit_tool_call, emit_tool_result, record_instruction_span

logger = structlog.get_logger(__name__)


class DirectInjectionPipeline(AttackPipeline):
    """
    Pipeline 1: Direct prompt injection.

    Sends the attack payload directly as user input to the target agent.
    Executes a benign control run with the same conversational structure.
    """

    pipeline_type = "direct"

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
        """Execute direct injection attack."""
        session_id = self.new_session_id()
        cfg = config or {}
        max_turns = cfg.get("max_turns", 1)

        # Create session record
        session = SessionModel(
            id=session_id,
            run_id=run_id,
            test_case_id=test_case_id,
            session_type="attack",
            pipeline="direct",
            status="running",
        )
        db.add(session)
        await db.flush()

        # Emit session start
        await emit_event(
            db=db,
            run_id=run_id,
            session_id=session_id,
            event_type=EventType.session_started,
            payload_data={"pipeline": "direct", "session_type": "attack"},
            payload_id=payload.payload_id if payload else None,
        )

        interactions: list[AgentInteraction] = []
        history: list[dict] = []

        for turn in range(max_turns):
            # First turn: send the attack payload
            # Subsequent turns: follow-up probes
            if turn == 0:
                message = payload.realized_content if payload else cfg.get("message", "")
                msg_origin = InstructionOrigin.user
            else:
                message = cfg.get(f"turn_{turn}_message", "Please continue.")
                msg_origin = InstructionOrigin.user

            # Record the input as an instruction span
            if payload and turn == 0:
                await record_instruction_span(
                    db=db,
                    run_id=run_id,
                    session_id=session_id,
                    content=message,
                    origin=msg_origin,
                )

            # Emit INPUT event
            input_event = await emit_event(
                db=db,
                run_id=run_id,
                session_id=session_id,
                turn_number=turn,
                event_type=EventType.input,
                payload_data={"message": message, "turn": turn},
                payload_id=payload.payload_id if payload and turn == 0 else None,
                origin=msg_origin,
            )

            # Send to agent
            interaction = await adapter.send_message(
                session_id=session_id,
                message=message,
                history=history,
                turn_number=turn,
            )
            interactions.append(interaction)

            # Emit RESPONSE event
            await emit_event(
                db=db,
                run_id=run_id,
                session_id=session_id,
                turn_number=turn,
                event_type=EventType.response,
                payload_data={"response": interaction.output_text, "turn": turn, "error": interaction.error},
            )

            # Emit tool calls and results
            for tc in interaction.tool_calls:
                _, call_id = await emit_tool_call(
                    db=db,
                    run_id=run_id,
                    session_id=session_id,
                    tool_name=tc.tool_name,
                    tool_args=tc.arguments,
                    turn_number=turn,
                    origin=InstructionOrigin.user if turn == 0 else None,
                    call_id=tc.call_id,
                    payload_id=payload.payload_id if payload and turn == 0 else None,
                )

            for tr in interaction.tool_results:
                await emit_tool_result(
                    db=db,
                    run_id=run_id,
                    session_id=session_id,
                    tool_name=tr.tool_name,
                    result=tr.result,
                    call_id=tr.call_id,
                    turn_number=turn,
                    is_mock=tr.is_mock,
                )

            # Update conversation history
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": interaction.output_text})

        # Session end
        await emit_event(
            db=db,
            run_id=run_id,
            session_id=session_id,
            event_type=EventType.session_ended,
            payload_data={"turns": len(interactions), "pipeline": "direct"},
        )

        # Update session record
        session.status = "completed"
        session.turn_count = len(interactions)
        session.tool_call_count = sum(len(i.tool_calls) for i in interactions)
        await db.flush()

        logger.info(
            "direct_pipeline_complete",
            session_id=session_id,
            turns=len(interactions),
            tool_calls=session.tool_call_count,
        )

        return InteractionTranscript(
            session_id=session_id,
            pipeline="direct",
            target_id="",
            session_type="attack",
            interactions=interactions,
        )

    async def execute_control(
        self,
        test_case_id: str,
        run_id: str,
        benign_message: str,
        adapter: TargetAdapter,
        db: AsyncSession,
        config: dict[str, Any] | None = None,
    ) -> InteractionTranscript:
        """Execute benign control run — same structure, no injection."""
        session_id = self.new_session_id()

        session = SessionModel(
            id=session_id,
            run_id=run_id,
            test_case_id=test_case_id,
            session_type="control",
            pipeline="direct",
            status="running",
        )
        db.add(session)
        await db.flush()

        await emit_event(db=db, run_id=run_id, session_id=session_id, event_type=EventType.session_started, payload_data={"pipeline": "direct", "session_type": "control"})

        await record_instruction_span(db=db, run_id=run_id, session_id=session_id, content=benign_message, origin=InstructionOrigin.user)

        await emit_event(db=db, run_id=run_id, session_id=session_id, turn_number=0, event_type=EventType.input, payload_data={"message": benign_message, "turn": 0}, origin=InstructionOrigin.user)

        interaction = await adapter.send_message(session_id=session_id, message=benign_message, turn_number=0)

        await emit_event(db=db, run_id=run_id, session_id=session_id, turn_number=0, event_type=EventType.response, payload_data={"response": interaction.output_text})

        for tc in interaction.tool_calls:
            await emit_tool_call(db=db, run_id=run_id, session_id=session_id, tool_name=tc.tool_name, tool_args=tc.arguments, turn_number=0, call_id=tc.call_id)

        for tr in interaction.tool_results:
            await emit_tool_result(db=db, run_id=run_id, session_id=session_id, tool_name=tr.tool_name, result=tr.result, call_id=tr.call_id, is_mock=tr.is_mock)

        await emit_event(db=db, run_id=run_id, session_id=session_id, event_type=EventType.session_ended, payload_data={"turns": 1, "pipeline": "direct"})

        session.status = "completed"
        session.turn_count = 1
        session.tool_call_count = len(interaction.tool_calls)
        await db.flush()

        return InteractionTranscript(session_id=session_id, pipeline="direct", target_id="", session_type="control", interactions=[interaction])
