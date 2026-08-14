import httpx
import logging
import uuid
import json
from typing import Any

from .base import TargetAdapter, AgentInteraction, ToolCall

logger = logging.getLogger(__name__)

class RestAdapter(TargetAdapter):
    """
    Adapter for communicating with standard REST API agents (like DVAIA).
    Expects a /chat endpoint accepting JSON with `messages`.
    """

    def __init__(self, endpoint_url: str, config: dict):
        self.endpoint = endpoint_url or "http://localhost:8001/chat"
        self.config = config
        self.model = config.get("model", "llama3.2:3b")

    @property
    def adapter_type(self) -> str:
        return "rest"

    async def send_message(
        self,
        session_id: str,
        message: str,
        history: list[dict[str, Any]] | None = None,
        turn_number: int = 0,
    ) -> AgentInteraction:
        messages = list(history) if history else []
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    self.endpoint,
                    json={"messages": messages, "model": self.model},
                    timeout=60.0
                )
                resp.raise_for_status()
                data = resp.json()
                
                content = data.get("content", "")
                raw_tool_calls = data.get("tool_calls", [])
                
                tool_calls = []
                for tc in raw_tool_calls:
                    fn = tc.get("function", {})
                    tc_id = tc.get("id") or str(uuid.uuid4())
                    # Convert arguments string to dict if needed
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            args = {"raw": args}
                            
                    tool_calls.append(ToolCall(
                        call_id=tc_id,
                        tool_name=fn.get("name", ""),
                        arguments=args
                    ))

                return AgentInteraction(
                    session_id=session_id,
                    turn_number=turn_number,
                    input_text=message,
                    output_text=content,
                    tool_calls=tool_calls,
                    model=self.model,
                    metadata={"raw_response": data}
                )
            except Exception as e:
                logger.error(f"RestAdapter error: {e}")
                return AgentInteraction(
                    session_id=session_id,
                    turn_number=turn_number,
                    input_text=message,
                    output_text="",
                    error=str(e)
                )

    async def discover_capabilities(self) -> list[dict[str, Any]]:
        # For this adapter, we might query an endpoint or just return from config
        return self.config.get("capabilities", [])
