"""File glob pattern matching tool."""
import os
import glob as glob_lib
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field


class GlobToolInput(BaseModel):
    """Input schema for glob tool."""
    pattern: str = Field(description="The glob pattern to match files against (e.g., '**/*.py', 'src/**/*.js')")
    path: Optional[str] = Field(default=None, description="The directory to search in. Defaults to current working directory.")


class GlobTool:
    """Tool for finding files by pattern matching."""
    
    name = "glob"
    description = "Fast file pattern matching tool for finding files by name patterns"
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema."""
        return {
            "type": "function",
            "function": {
                "name": "glob",
                "description": """Fast file pattern matching tool that works with any codebase size.
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time (most recent first)
- Use this tool when you need to find files by name patterns
- You can call multiple tools in parallel for better efficiency""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The glob pattern to match files against (e.g., '**/*.py', 'src/**/*.js')"
                        },
                        "path": {
                            "type": "string",
                            "description": "Optional directory to search in. Defaults to current working directory."
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
    async def execute(pattern: str, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute glob pattern matching.
        
        Returns:
            Dictionary with matched files, count, and truncation info
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
                "num_files": 0,
                "truncated": False
            }
        
        if not os.path.isdir(search_dir):
            return {
                "success": False,
                "error": f"Path is not a directory: {search_dir}",
                "files": [],
                "num_files": 0,
                "truncated": False
            }
        
        try:
            # Use glob with recursive support
            full_pattern = os.path.join(search_dir, pattern)
            matched_files = glob_lib.glob(full_pattern, recursive=True)
            
            # Filter out directories, keep only files
            matched_files = [f for f in matched_files if os.path.isfile(f)]
            
            # Sort by modification time
            sorted_files = GlobTool._sort_by_mtime(matched_files)
            
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
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Glob operation failed: {str(e)}",
                "files": [],
                "num_files": 0,
                "truncated": False
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
        
        # Format file list
        output = '\n'.join(files)
        
        # Add truncation notice if applicable
        if truncated:
            total_matches = result.get("total_matches", num_files)
            output += f"\n\n(Results are truncated. Showing {num_files} of {total_matches} matches. Consider using a more specific pattern.)"
        
        return output

