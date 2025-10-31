"""File write tool for creating or overwriting files."""
import os
import difflib
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class WriteToolInput(BaseModel):
    """Input schema for write tool."""
    file_path: str = Field(description="The path to the file to write")
    content: str = Field(description="The content to write to the file")


class WriteTool:
    """Tool for writing/overwriting files."""
    
    name = "write"
    description = "A tool for writing complete file content (create or overwrite)"
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema."""
        return {
            "type": "function",
            "function": {
                "name": "write",
                "description": "Write content to a file (creates new file or overwrites existing one).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to write (absolute or relative)"
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        }
    
    @staticmethod
    def _read_file(file_path: str) -> str:
        """Read file with encoding fallback."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    @staticmethod
    def _write_file(file_path: str, content: str) -> None:
        """Write file with encoding fallback."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except UnicodeEncodeError:
            with open(file_path, 'w', encoding='latin-1') as f:
                f.write(content)
    
    @staticmethod
    def generate_preview(
        file_path: str,
        content: str,
        read_file_timestamps: Dict[str, float]
    ) -> Tuple[bool, Any]:
        """
        Generate a preview of the write operation.
        
        Args:
            file_path: Path to the file to write
            content: Content to write
            read_file_timestamps: Dictionary of file read timestamps
            
        Returns:
            Tuple of (success, preview_data_or_error)
            preview_data is (diff_lines, file_path, file_exists) for success
        """
        # Resolve full path
        full_file_path = file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)
        
        # Check if file exists
        file_exists = os.path.exists(full_file_path)
        
        # Validate existing files
        if file_exists:
            # Check if it's a Jupyter notebook
            if full_file_path.endswith('.ipynb'):
                return False, "File is a Jupyter Notebook. Use a notebook edit tool instead."
            
            # Check if file has been read
            read_timestamp = read_file_timestamps.get(full_file_path)
            if not read_timestamp:
                return False, "File has not been read yet. Read it first before writing to it."
            
            # Check if file was modified since read
            try:
                last_write_time = os.path.getmtime(full_file_path)
                if last_write_time > read_timestamp:
                    return False, "File has been modified since read, either by the user or by a linter. Read it again before attempting to write it."
            except OSError as e:
                return False, f"Cannot access file: {e}"
        
        # Read old content if file exists
        old_content = ""
        if file_exists:
            try:
                old_content = WriteTool._read_file(full_file_path)
            except Exception as e:
                return False, f"Cannot read existing file: {e}"
        
        # Generate diff
        diff_lines = []
        if file_exists and old_content:
            diff_lines = list(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=file_path,
                tofile=file_path,
                lineterm=''
            ))
        
        return True, (diff_lines, file_path, file_exists, content)
    
    @staticmethod
    async def execute(
        file_path: str,
        content: str,
        read_file_timestamps: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Execute file write.
        
        Returns:
            Dictionary with file_path, content, and metadata
        """
        # Resolve full path
        full_file_path = file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)
        
        # Check if file exists
        file_exists = os.path.exists(full_file_path)
        
        # Validate existing files
        if file_exists:
            # Check if it's a Jupyter notebook
            if full_file_path.endswith('.ipynb'):
                return {
                    "success": False,
                    "error": "File is a Jupyter Notebook. Use a notebook edit tool instead.",
                    "file_path": file_path
                }
            
            # Check if file has been read
            read_timestamp = read_file_timestamps.get(full_file_path)
            if not read_timestamp:
                return {
                    "success": False,
                    "error": "File has not been read yet. Read it first before writing to it.",
                    "file_path": file_path
                }
            
            # Check if file was modified since read
            try:
                last_write_time = os.path.getmtime(full_file_path)
                if last_write_time > read_timestamp:
                    return {
                        "success": False,
                        "error": "File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.",
                        "file_path": file_path
                    }
            except OSError as e:
                return {
                    "success": False,
                    "error": f"Cannot access file: {e}",
                    "file_path": file_path
                }
        
        # Read old content if file exists
        old_content = ""
        if file_exists:
            try:
                old_content = WriteTool._read_file(full_file_path)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Cannot read existing file: {e}",
                    "file_path": file_path
                }
        
        # Create directory if needed
        try:
            os.makedirs(os.path.dirname(full_file_path) or '.', exist_ok=True)
        except Exception as e:
            return {
                "success": False,
                "error": f"Cannot create directory: {e}",
                "file_path": file_path
            }
        
        # Write the file
        try:
            WriteTool._write_file(full_file_path, content)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write file: {e}",
                "file_path": file_path
            }
        
        # Update read timestamp
        try:
            read_file_timestamps[full_file_path] = os.path.getmtime(full_file_path)
        except OSError:
            pass
        
        # Generate diff for updates
        diff_lines = []
        if file_exists and old_content:
            diff_lines = list(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=file_path,
                tofile=file_path,
                lineterm=''
            ))
        
        return {
            "success": True,
            "file_path": file_path,
            "content": content,
            "type": "update" if file_exists else "create",
            "diff": diff_lines
        }
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format tool result for display to LLM."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        file_path = result.get("file_path", "")
        content = result.get("content", "")
        result_type = result.get("type", "create")
        
        if result_type == "create":
            num_lines = len(content.split('\n'))
            return f"File created successfully at: {file_path} ({num_lines} lines)"
        else:
            # For updates, show line-numbered content
            lines = content.split('\n')
            numbered_lines = [f"{i:4d} | {line}" for i, line in enumerate(lines, start=1)]
            
            output = f"The file {file_path} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:\n"
            output += '\n'.join(numbered_lines[:100])  # Limit to first 100 lines
            
            if len(lines) > 100:
                output += f"\n... (+{len(lines) - 100} more lines)"
            
            return output

