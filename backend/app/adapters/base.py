"""
Target Adapter Base — Abstract interface for all target adapters.

Adapters must:
  - Capture input, output, tool calls, tool results, session ID, timestamps
  - NOT contain any attack logic
  - NOT contain any evaluation logic
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ToolCall:
    """A tool call made by the agent."""
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    origin_hint: str | None = None  # Optional origin hint from adapter


@dataclass
class ToolResult:
    """Result of a tool call."""
    call_id: str
    tool_name: str
    result: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_mock: bool = True
    error: str | None = None


@dataclass
class AgentInteraction:
    """A single input→response interaction with the agent."""
    session_id: str
    turn_number: int
    input_text: str
    output_text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    model: str | None = None
    token_usage: dict[str, int] | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionTranscript:
    """Full transcript of a session — returned by a pipeline after execution."""
    session_id: str
    pipeline: str
    target_id: str
    session_type: str  # attack|control
    interactions: list[AgentInteraction] = field(default_factory=list)
    error: str | None = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def all_tool_calls(self) -> list[ToolCall]:
        """Flatten all tool calls across interactions."""
        return [tc for interaction in self.interactions for tc in interaction.tool_calls]

    @property
    def all_tool_names(self) -> list[str]:
        """All unique tool names called in this session."""
        return list({tc.tool_name for tc in self.all_tool_calls})

    @property
    def turn_count(self) -> int:
        return len(self.interactions)


class TargetAdapter(abc.ABC):
    """
    Abstract base class for all target adapters.

    Adapters are responsible for:
      - Sending input to the target agent
      - Capturing the response (text + tool calls)
      - Reporting token usage if available
      - NOT doing any attack logic
      - NOT doing any evaluation
    """

    @property
    @abc.abstractmethod
    def adapter_type(self) -> str:
        """Return adapter type identifier."""
        ...

    @abc.abstractmethod
    async def send_message(
        self,
        session_id: str,
        message: str,
        history: list[dict[str, Any]] | None = None,
        turn_number: int = 0,
    ) -> AgentInteraction:
        """
        Send a message to the agent and return the interaction.

        Must capture:
        - response text
        - tool calls made by the agent
        - tool results
        - token usage (if available)
        - errors
        """
        ...

    @abc.abstractmethod
    async def discover_capabilities(self) -> list[dict[str, Any]]:
        """
        Discover the tools/capabilities of this target agent.

        Returns a list of tool definitions.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the target is reachable. Default: always healthy."""
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} ({self.adapter_type})>"
