"""File content search tool using ripgrep."""
import os
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field


class GrepToolInput(BaseModel):
    """Input schema for grep tool."""
    pattern: str = Field(description="The regular expression pattern to search for in file contents")
    path: Optional[str] = Field(default=None, description="The directory to search in. Defaults to current working directory.")
    include: Optional[str] = Field(default=None, description='File pattern to include in search (e.g., "*.js", "*.{ts,tsx}")')


class GrepTool:
    """Tool for searching file contents using ripgrep."""
    
    name = "grep"
    description = "A powerful search tool built on ripgrep for finding files by content"
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema."""
        return {
            "type": "function",
            "function": {
                "name": "grep",
                "description": """A powerful search tool built on ripgrep.

Usage:
- ALWAYS use Grep for search tasks. NEVER invoke grep or rg as a Bash command.
- Supports full regex syntax (e.g., "log.*Error", "function\\s+\\w+")
- Filter files with include parameter (e.g., "*.js", "*.{ts,tsx}")
- Returns list of files containing matches (sorted by modification time)
- Pattern syntax: Uses ripgrep - literal braces need escaping (use interface\\{\\} to find interface{} in code)
- You can call multiple tools in parallel for better efficiency""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The regular expression pattern to search for in file contents"
                        },
                        "path": {
                            "type": "string",
                            "description": "Optional directory to search in. Defaults to current working directory."
                        },
                        "include": {
                            "type": "string",
                            "description": 'Optional file pattern to include in search (e.g., "*.js", "*.{ts,tsx}")'
                        }
                    },
                    "required": ["pattern"]
                }
            }
        }
    
    @staticmethod
    def _sort_by_mtime(files: List[str]) -> List[str]:
        """Sort files by modification time (most recent first)."""
        files_with_mtime: List[Tuple[str, float]] = []
        for filepath in files:
            try:
                mtime = os.path.getmtime(filepath)
                files_with_mtime.append((filepath, mtime))
            except (OSError, IOError):
                # If we can't get mtime, put it at the end with mtime 0
                files_with_mtime.append((filepath, 0))
        
        # Sort by mtime descending (most recent first)
        files_with_mtime.sort(key=lambda x: x[1], reverse=True)
        return [f[0] for f in files_with_mtime]
    
    @staticmethod
    async def execute(
        pattern: str,
        path: Optional[str] = None,
        include: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute grep search using ripgrep.
        
        Returns:
            Dictionary with matched files, count, and metadata
        """
        # Determine search directory
        search_dir = path if path else os.getcwd()
        
        # Resolve to absolute path
        if not os.path.isabs(search_dir):
            search_dir = os.path.join(os.getcwd(), search_dir)
        
        # Check if directory exists
        if not os.path.exists(search_dir):
            return {
                "success": False,
                "error": f"Directory does not exist: {search_dir}",
                "files": [],
                "num_files": 0
            }
        
        if not os.path.isdir(search_dir):
            return {
                "success": False,
                "error": f"Path is not a directory: {search_dir}",
                "files": [],
                "num_files": 0
            }
        
        try:
            # Build ripgrep command
            # -l: show only filenames (not content)
            # -i: case insensitive (optional, can be removed if needed)
            cmd = ['rg', '-l', pattern]
            
            # Add glob filter if specified
            if include:
                cmd.extend(['--glob', include])
            
            # Add search directory
            cmd.append(search_dir)
            
            # Execute ripgrep
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Exit code 1 means no matches found (not an error)
            if result.returncode == 1:
                return {
                    "success": True,
                    "files": [],
                    "num_files": 0
                }
            
            # Other non-zero exit codes are errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "ripgrep command failed"
                return {
                    "success": False,
                    "error": f"Search failed: {error_msg}",
                    "files": [],
                    "num_files": 0
                }
            
            # Parse results
            matched_files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            
            # Sort by modification time
            sorted_files = GrepTool._sort_by_mtime(matched_files)
            
            # Limit to 100 results
            limit = 100
            truncated = len(sorted_files) > limit
            result_files = sorted_files[:limit]
            
            return {
                "success": True,
                "files": result_files,
                "num_files": len(result_files),
                "total_matches": len(sorted_files),
                "truncated": truncated
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "ripgrep (rg) command not found. Please install ripgrep to use this tool.",
                "files": [],
                "num_files": 0
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Search timed out after 10 seconds",
                "files": [],
                "num_files": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "files": [],
                "num_files": 0
            }
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format tool result for display to LLM."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        files = result.get("files", [])
        num_files = result.get("num_files", 0)
        truncated = result.get("truncated", False)
        
        if num_files == 0:
            return "No files found"
        
        # Format file list with count
        output = f"Found {num_files} file{'s' if num_files != 1 else ''}\n"
        output += '\n'.join(files)
        
        # Add truncation notice if applicable
        if truncated:
            total_matches = result.get("total_matches", num_files)
            output += f"\n\n(Results are truncated. Showing {num_files} of {total_matches} matches. Consider using a more specific path or pattern.)"
        
        return output

