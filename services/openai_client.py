"""OpenAI API client with function calling support."""
import asyncio
import os
import json
from typing import Any, Dict, List, Optional, Callable
from openai import OpenAI


class OpenAIClient:
    """Client for OpenAI API with function calling support."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize OpenAI client."""
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
    
    async def query(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Query OpenAI with tool calling support.
        
        Args:
            messages: Conversation history
            system_prompt: System prompt to prepend
            tools: Available tools (in new format)
            tool_executor: Callable to execute tools
            max_iterations: Maximum tool call iterations
            
        Returns:
            Final assistant message with usage stats
        """
        # Prepare messages
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation messages (removing internal fields)
        for msg in messages:
            api_msg = {"role": msg["role"]}
            if "content" in msg and msg["content"] is not None:
                api_msg["content"] = msg["content"]
            if "name" in msg:
                api_msg["name"] = msg["name"]
            if "tool_calls" in msg:
                api_msg["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                api_msg["tool_call_id"] = msg["tool_call_id"]
            api_messages.append(api_msg)
        
        total_tokens = 0
        tool_use_count = 0
        
        retry_attempts = 10
        backoff_seconds = 2.0
        
        # Conversation loop with tool calling
        for iteration in range(max_iterations):
            # Call OpenAI
            response = None
            for attempt in range(retry_attempts):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=api_messages,
                        tools=tools if tools else None,
                        tool_choice="auto" if tools else None,
                        temperature=0.7
                    )
                    break
                except Exception as e:
                    status = getattr(e, "status_code", None)
                    message_text = str(e).lower()
                    is_rate_limited = (
                        status == 429
                        or "rate limit" in message_text
                        or "max rpm" in message_text
                    )
                    if is_rate_limited and attempt < retry_attempts - 1:
                        delay = backoff_seconds * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    raise
            
            if response is None:
                raise RuntimeError("Failed to obtain response from OpenAI after retries")
            
            message = response.choices[0].message
            
            # Track usage
            if response.usage:
                total_tokens += response.usage.total_tokens
            
            # Check if tool calls are requested
            if message.tool_calls:
                tool_use_count += len(message.tool_calls)
                
                # Add assistant message with tool calls
                api_messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # Execute tools
                if tool_executor:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                        
                        # Execute the tool
                        result = await tool_executor(tool_name, arguments)
                        
                        # Add tool result message
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(result) if isinstance(result, dict) else str(result)
                        })
                else:
                    # No executor, stop here
                    break
            else:
                # No tool calls, we're done
                return {
                    "content": message.content or "",
                    "role": "assistant",
                    "total_tokens": total_tokens,
                    "tool_use_count": tool_use_count,
                    "finish_reason": response.choices[0].finish_reason
                }
        
        # Max iterations reached
        return {
            "content": "Maximum tool call iterations reached",
            "role": "assistant",
            "total_tokens": total_tokens,
            "tool_use_count": tool_use_count,
            "finish_reason": "max_iterations"
        }
