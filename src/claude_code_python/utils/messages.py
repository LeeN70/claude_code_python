"""Message formatting and utilities."""
from typing import Any, Dict, List, Union
import uuid


def create_user_message(content: str) -> Dict[str, Any]:
    """Create a user message in OpenAI format."""
    return {
        "role": "user",
        "content": content,
        "id": str(uuid.uuid4())
    }


def create_assistant_message(content: str) -> Dict[str, Any]:
    """Create an assistant message in OpenAI format."""
    return {
        "role": "assistant",
        "content": content,
        "id": str(uuid.uuid4())
    }


def create_function_message(name: str, content: str) -> Dict[str, Any]:
    """Create a function result message in OpenAI format."""
    return {
        "role": "function",
        "name": name,
        "content": content,
        "id": str(uuid.uuid4())
    }


def format_messages_for_api(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Format messages for OpenAI API (remove internal fields like id)."""
    formatted = []
    for msg in messages:
        formatted_msg = {"role": msg["role"]}
        if "content" in msg:
            formatted_msg["content"] = msg["content"]
        if "name" in msg:
            formatted_msg["name"] = msg["name"]
        if "function_call" in msg:
            formatted_msg["function_call"] = msg["function_call"]
        formatted.append(formatted_msg)
    return formatted

