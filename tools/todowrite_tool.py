"""Todo management tool for tracking tasks."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TodoStatus(str, Enum):
    """Todo status enum."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TodoPriority(str, Enum):
    """Todo priority enum."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TodoItem(BaseModel):
    """Todo item model."""
    content: str = Field(description="Todo content")
    status: TodoStatus = Field(description="Todo status")
    priority: TodoPriority = Field(description="Todo priority")
    id: str = Field(description="Unique todo ID")


class TodoWriteToolInput(BaseModel):
    """Input schema for todo write tool."""
    todos: List[TodoItem] = Field(description="List of todo items")


# Global state for todo persistence
_global_todo_state: List[Dict[str, Any]] = []


class TodoWriteTool:
    """Tool for managing todo lists."""
    
    name = "todo_write"
    description = "Create and manage a structured task list for tracking progress"
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema."""
        return {
            "type": "function",
            "function": {
                "name": "todo_write",
                "description": """Use this tool to create and manage a structured task list for your current coding session. This helps track progress, organize complex tasks, and demonstrate thoroughness.

When to use:
- Complex multi-step tasks (3+ distinct steps)
- Non-trivial tasks requiring careful planning
- User explicitly requests todo list
- User provides multiple tasks
- After receiving new instructions - capture requirements as todos
- When starting tasks - mark as in_progress (only one at a time)
- After completing tasks - mark as completed

When NOT to use:
- Single, straightforward tasks
- Trivial tasks with no organizational benefit
- Tasks completable in < 3 trivial steps
- Purely conversational/informational requests""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todos": {
                            "type": "array",
                            "description": "List of todo items",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "Todo content/description"
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["pending", "in_progress", "completed"],
                                        "description": "Todo status"
                                    },
                                    "priority": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                        "description": "Todo priority"
                                    },
                                    "id": {
                                        "type": "string",
                                        "description": "Unique ID for the todo"
                                    }
                                },
                                "required": ["content", "status", "priority", "id"]
                            }
                        }
                    },
                    "required": ["todos"]
                }
            }
        }
    
    @staticmethod
    def _validate_todos(todos: List[TodoItem]) -> Optional[str]:
        """Validate todo list. Returns error message if invalid, None if valid."""
        # Check for duplicate IDs
        ids = [t.id for t in todos]
        if len(ids) != len(set(ids)):
            return "Duplicate todo IDs found"
        
        # Check for multiple in_progress tasks
        in_progress = [t for t in todos if t.status == TodoStatus.IN_PROGRESS]
        if len(in_progress) > 1:
            return "Only one task can be in progress at a time"
        
        # Check for empty content
        for todo in todos:
            if not todo.content.strip():
                return "Todo content cannot be empty"
        
        return None
    
    @staticmethod
    def _detect_changes(old_todos: List[Dict[str, Any]], new_todos: List[TodoItem]) -> List[Dict[str, Any]]:
        """Detect changes between old and new todo lists."""
        changes = []
        
        # Convert new todos to dict for comparison
        new_todos_dict = {t.id: t for t in new_todos}
        old_todos_dict = {t["id"]: t for t in old_todos}
        
        # Find status changes
        for new_todo in new_todos:
            if new_todo.id in old_todos_dict:
                old_status = old_todos_dict[new_todo.id]["status"]
                if old_status != new_todo.status.value:
                    changes.append({
                        "type": "status_change",
                        "task_id": new_todo.id,
                        "old_status": old_status,
                        "new_status": new_todo.status.value,
                        "content": new_todo.content
                    })
        
        # Find new tasks
        for new_todo in new_todos:
            if new_todo.id not in old_todos_dict:
                changes.append({
                    "type": "task_added",
                    "task_id": new_todo.id,
                    "status": new_todo.status.value,
                    "content": new_todo.content
                })
        
        return changes
    
    @staticmethod
    async def execute(todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute todo management.
        
        Returns:
            Dictionary with summary and todo list
        """
        global _global_todo_state
        
        # Parse todos
        try:
            todo_items = [TodoItem(**t) for t in todos]
        except Exception as e:
            return {
                "error": f"Invalid todo format: {str(e)}",
                "todos": _global_todo_state
            }
        
        # Validate
        error = TodoWriteTool._validate_todos(todo_items)
        if error:
            return {
                "error": error,
                "todos": _global_todo_state
            }
        
        # Detect changes
        old_todos = _global_todo_state.copy()
        changes = TodoWriteTool._detect_changes(old_todos, todo_items)
        
        # Sort by status and priority
        status_order = {"in_progress": 0, "pending": 1, "completed": 2}
        priority_order = {"high": 0, "medium": 1, "low": 2}
        
        sorted_todos = sorted(
            todo_items,
            key=lambda t: (status_order[t.status.value], priority_order[t.priority.value])
        )
        
        # Update global state
        _global_todo_state = [t.dict() for t in sorted_todos]
        
        # Generate summary
        pending = sum(1 for t in sorted_todos if t.status == TodoStatus.PENDING)
        in_progress = sum(1 for t in sorted_todos if t.status == TodoStatus.IN_PROGRESS)
        completed = sum(1 for t in sorted_todos if t.status == TodoStatus.COMPLETED)
        
        summary = f"{len(sorted_todos)} tasks managed ({pending} pending, {in_progress} in progress, {completed} completed)"
        
        return {
            "summary": summary,
            "todos": _global_todo_state,
            "changes": changes,
            "pending_count": pending,
            "in_progress_count": in_progress,
            "completed_count": completed
        }
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format tool result for display."""
        if "error" in result:
            return f"Error: {result['error']}"
        
        output = [f"✓ {result['summary']}\n"]
        
        todos = result.get("todos", [])
        if not todos:
            output.append("(Empty todo list)")
            return "\n".join(output)
        
        # Group by status
        for status in ["in_progress", "pending", "completed"]:
            status_todos = [t for t in todos if t["status"] == status]
            if status_todos:
                status_label = status.replace("_", " ").title()
                output.append(f"\n{status_label}:")
                for todo in status_todos:
                    icon = "☒" if status == "completed" else "☐"
                    priority_marker = "🔴" if todo["priority"] == "high" else "🟡" if todo["priority"] == "medium" else "🟢"
                    output.append(f"  {icon} {priority_marker} {todo['content']}")
        
        return "\n".join(output)
    
    @staticmethod
    def get_current_todos() -> List[Dict[str, Any]]:
        """Get current todo state."""
        return _global_todo_state.copy()

