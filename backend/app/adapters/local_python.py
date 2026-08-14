"""
Local Python Agent Adapter

Wraps a local Python callable/class as a target agent.
Used for mock agents and testing without external API calls.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from app.adapters.base import AgentInteraction, TargetAdapter, ToolCall, ToolResult

logger = structlog.get_logger(__name__)


class LocalPythonAdapter(TargetAdapter):
    """
    Adapter for local Python callables.

    Supports:
      - Any class with a process_message(message, history) method
      - Any callable that returns a dict with 'response' and 'tool_calls'
    """

    adapter_type = "local_python"

    def __init__(
        self,
        agent_instance: Any,
        model_name: str = "local_mock",
    ):
        self._agent = agent_instance
        self._model_name = model_name

    async def send_message(
        self,
        session_id: str,
        message: str,
        history: list[dict[str, Any]] | None = None,
        turn_number: int = 0,
    ) -> AgentInteraction:
        """Send message to the local agent and capture all interactions."""
        try:
            # Call the agent
            if hasattr(self._agent, "process_message"):
                raw = self._agent.process_message(message, history)
            elif callable(self._agent):
                raw = self._agent(message, history)
            else:
                raise TypeError(f"Agent {type(self._agent)} has no process_message method or callable interface")

            # Parse response
            response_text = raw.get("response", "") if isinstance(raw, dict) else str(raw)
            raw_tool_calls = raw.get("tool_calls", []) if isinstance(raw, dict) else []

            # Convert to structured ToolCall/ToolResult objects
            tool_calls = []
            tool_results = []
            for tc in raw_tool_calls:
                call_id = str(uuid.uuid4())
                tool_calls.append(
                    ToolCall(
                        call_id=call_id,
                        tool_name=tc.get("name", "unknown"),
                        arguments=tc.get("args", {}),
                        timestamp=datetime.now(timezone.utc),
                    )
                )
                if "result" in tc:
                    tool_results.append(
                        ToolResult(
                            call_id=call_id,
                            tool_name=tc.get("name", "unknown"),
                            result=tc["result"],
                            is_mock=True,
                        )
                    )

            interaction = AgentInteraction(
                session_id=session_id,
                turn_number=turn_number,
                input_text=message,
                output_text=response_text,
                tool_calls=tool_calls,
                tool_results=tool_results,
                model=self._model_name,
                metadata={"injection_followed": raw.get("injection_followed", False) if isinstance(raw, dict) else False},
            )

            logger.debug(
                "local_agent_response",
                session_id=session_id,
                turn=turn_number,
                tool_calls=[tc.tool_name for tc in tool_calls],
                injection_followed=interaction.metadata.get("injection_followed"),
            )

            return interaction

        except Exception as exc:
            logger.error("local_agent_error", session_id=session_id, error=str(exc))
            return AgentInteraction(
                session_id=session_id,
                turn_number=turn_number,
                input_text=message,
                output_text="",
                error=str(exc),
            )

    async def discover_capabilities(self) -> list[dict[str, Any]]:
        """Return tool definitions from the agent."""
        if hasattr(self._agent, "get_capabilities"):
            return self._agent.get_capabilities()
        if hasattr(self._agent, "tools"):
            return self._agent.tools
        return []

    async def health_check(self) -> bool:
        return self._agent is not None


class MockAgentRegistry:
    """Registry of all available mock agents."""

    _registry: dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, agent_instance: Any) -> None:
        cls._registry[name] = agent_instance
        logger.info("mock_agent_registered", name=name)

    @classmethod
    def get(cls, name: str) -> Any | None:
        return cls._registry.get(name)

    @classmethod
    def list_agents(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def create_adapter(cls, name: str) -> LocalPythonAdapter | None:
        agent = cls.get(name)
        if agent is None:
            return None
        return LocalPythonAdapter(agent_instance=agent, model_name=name)


def initialize_mock_agents() -> None:
    """Register all mock agents in the registry."""
    try:
        # Add parent directory to path for datasets
        datasets_path = Path(__file__).parent.parent.parent.parent.parent / "datasets" / "mock_agents"
        if str(datasets_path) not in sys.path:
            sys.path.insert(0, str(datasets_path.parent.parent))

        from datasets.mock_agents.support_agent import MockSupportAgent
        MockAgentRegistry.register("mock_support_agent", MockSupportAgent())

        from datasets.mock_agents.productivity_agent import MockProductivityAgent
        MockAgentRegistry.register("mock_productivity_agent", MockProductivityAgent())

        from datasets.mock_agents.research_agent import MockResearchAgent
        MockAgentRegistry.register("mock_research_agent", MockResearchAgent())

        from datasets.mock_agents.developer_agent import MockDeveloperAgent
        MockAgentRegistry.register("mock_developer_agent", MockDeveloperAgent())

        logger.info("mock_agents_initialized", count=len(MockAgentRegistry.list_agents()))
    except ImportError as e:
        logger.warning("mock_agent_import_error", error=str(e))
