import httpx
import logging
import uuid
import json
from typing import Any

from .base import TargetAdapter, AgentInteraction, ToolCall

logger = logging.getLogger(__name__)

class OpenAICompatibleAdapter(TargetAdapter):
    """
    Adapter for communicating with any agent/LLM exposing the OpenAI Chat Completions API.
    """

    def __init__(self, endpoint_url: str, config: dict):
        # Default to local ollama if no endpoint provided
        self.endpoint = (endpoint_url or "http://127.0.0.1:11434").strip()
        
        if not self.endpoint.startswith("http://") and not self.endpoint.startswith("https://"):
            self.endpoint = f"http://{self.endpoint}"
        if not self.endpoint.endswith("/chat/completions"):
            if not self.endpoint.endswith("/"):
                self.endpoint += "/"
            self.endpoint += "v1/chat/completions"
            
        self.config = config
        self.model = config.get("model", "llama3.2:3b")
        self.api_key = config.get("api_key", "")
        self.system_prompt = config.get("system_prompt", "You are a helpful assistant.")
        
        # Default mock tools to simulate a vulnerable agent environment
        default_tools = [
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send an email to a user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Email address"},
                            "body": {"type": "string", "description": "Content of the email"}
                        },
                        "required": ["to", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_sql_query",
                    "description": "Execute a raw SQL query on the database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL query to execute"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "Delete a file from the server.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Absolute path to the file"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_user_data",
                    "description": "Fetch confidential user data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "ID of the user"}
                        },
                        "required": ["user_id"]
                    }
                }
            }
        ]
        self.tools = config.get("tools", default_tools)

    @property
    def adapter_type(self) -> str:
        return "openai_compatible"

    async def send_message(
        self,
        session_id: str,
        message: str,
        history: list[dict[str, Any]] | None = None,
        turn_number: int = 0,
    ) -> AgentInteraction:
        messages = list(history) if history else []
        
        # Inject system prompt if it's the first turn and no system prompt exists
        if turn_number == 0 and not any(m.get("role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": self.system_prompt})
            
        messages.append({"role": "user", "content": message})
        
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": messages,
        }
        
        if self.tools:
            payload["tools"] = self.tools

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=60.0
                )
                resp.raise_for_status()
                data = resp.json()
                
                choices = data.get("choices", [])
                if not choices:
                    return AgentInteraction(
                        session_id=session_id,
                        turn_number=turn_number,
                        input_text=message,
                        output_text="",
                        error="No choices returned from API"
                    )
                    
                message_data = choices[0].get("message", {})
                content = message_data.get("content", "")
                raw_tool_calls = message_data.get("tool_calls", [])
                
                tool_calls = []
                for tc in raw_tool_calls:
                    if tc.get("type") != "function":
                        continue
                        
                    fn = tc.get("function", {})
                    tc_id = tc.get("id") or str(uuid.uuid4())
                    
                    # OpenAI returns arguments as a JSON string
                    args_str = fn.get("arguments", "{}")
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {"raw": args_str}
                            
                    tool_calls.append(ToolCall(
                        call_id=tc_id,
                        tool_name=fn.get("name", ""),
                        arguments=args
                    ))

                usage = data.get("usage", {})

                return AgentInteraction(
                    session_id=session_id,
                    turn_number=turn_number,
                    input_text=message,
                    output_text=content or "",
                    tool_calls=tool_calls,
                    model=data.get("model", self.model),
                    token_usage=usage,
                    metadata={"raw_response": data}
                )
            except Exception as e:
                logger.error(f"OpenAICompatibleAdapter error: {e}")
                return AgentInteraction(
                    session_id=session_id,
                    turn_number=turn_number,
                    input_text=message,
                    output_text="",
                    error=str(e)
                )

    async def discover_capabilities(self) -> list[dict[str, Any]]:
        # We rely on the config to provide tools since OpenAI endpoints don't expose 
        # a standard "discover tools" endpoint.
        return self.tools
