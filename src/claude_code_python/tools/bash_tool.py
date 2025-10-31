"""Bash command execution tool."""
import subprocess
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from ..utils.validation import validate_bash_command, truncate_output


class BashToolInput(BaseModel):
    """Input schema for bash tool."""
    command: str = Field(description="The bash command to execute")
    timeout: Optional[int] = Field(default=120, description="Timeout in seconds (max 600)")
    description: Optional[str] = Field(default=None, description="Brief description of command")


class BashTool:
    """Tool for executing bash commands."""
    
    name = "bash"
    description = "Execute a bash command in the shell"
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema (new format)."""
        return {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Execute a bash command in the shell. Returns stdout, stderr, and exit code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Optional timeout in seconds (default 120, max 600)",
                            "default": 120
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional brief description of what this command does"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    
    @staticmethod
    async def execute(command: str, timeout: int = 120, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a bash command.
        
        Returns:
            Dictionary with stdout, stderr, exit_code, and interrupted flag
        """
        # Get current working directory
        cwd = os.getcwd()
        
        # Validate command
        is_valid, error_msg = validate_bash_command(command, cwd)
        if not is_valid:
            return {
                "stdout": "",
                "stderr": error_msg,
                "exit_code": 1,
                "interrupted": False
            }
        
        # Ensure timeout is within limits
        timeout = min(max(1, timeout), 600)
        
        # Execute command
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            # Truncate output if needed
            stdout_truncated, stdout_lines = truncate_output(result.stdout)
            stderr_truncated, stderr_lines = truncate_output(result.stderr)
            
            return {
                "stdout": stdout_truncated,
                "stderr": stderr_truncated,
                "exit_code": result.returncode,
                "interrupted": False,
                "stdout_lines": stdout_lines,
                "stderr_lines": stderr_lines
            }
            
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command execution timed out after {timeout} seconds",
                "exit_code": 124,  # Standard timeout exit code
                "interrupted": True
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Command execution failed: {str(e)}",
                "exit_code": 1,
                "interrupted": False
            }
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format tool result for display to LLM."""
        output_parts = []
        
        if result.get("stdout"):
            output_parts.append(result["stdout"])
        
        if result.get("stderr"):
            if output_parts:
                output_parts.append("\n")
            output_parts.append(result["stderr"])
        
        if result.get("interrupted"):
            output_parts.append("\n<error>Command was aborted before completion</error>")
        
        return "".join(output_parts) if output_parts else ""

