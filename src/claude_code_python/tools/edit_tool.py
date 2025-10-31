"""File edit tool for modifying files."""
import os
import difflib
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


# Number of lines of context to include before/after the change
N_LINES_SNIPPET = 4


class EditToolInput(BaseModel):
    """Input schema for edit tool."""
    file_path: str = Field(description="The path to the file to modify")
    old_string: str = Field(description="The text to replace")
    new_string: str = Field(description="The text to replace it with")


class EditTool:
    """Tool for editing files."""
    
    name = "edit"
    description = "A tool for editing files"
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema."""
        return {
            "type": "function",
            "function": {
                "name": "edit",
                "description": "Edit a file by replacing old_string with new_string. For creating new files, use empty string for old_string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to modify (absolute or relative)"
                        },
                        "old_string": {
                            "type": "string",
                            "description": "The text to replace (empty string for new file creation)"
                        },
                        "new_string": {
                            "type": "string",
                            "description": "The text to replace it with (empty string to delete)"
                        }
                    },
                    "required": ["file_path", "old_string", "new_string"]
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
    def validate_input(
        file_path: str,
        old_string: str,
        new_string: str,
        read_file_timestamps: Dict[str, float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate edit input.
        
        Returns:
            (is_valid, error_message)
        """
        # Check for no-op
        if old_string == new_string:
            return False, "No changes to make: old_string and new_string are exactly the same."
        
        # Resolve full path
        full_file_path = file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)
        
        # Check for creating file that already exists
        if os.path.exists(full_file_path) and old_string == "":
            return False, "Cannot create new file - file already exists."
        
        # Allow creation of new files
        if not os.path.exists(full_file_path) and old_string == "":
            return True, None
        
        # Check if file exists
        if not os.path.exists(full_file_path):
            return False, "File does not exist."
        
        # Check for Jupyter notebooks
        if full_file_path.endswith('.ipynb'):
            return False, "File is a Jupyter Notebook. Use a notebook edit tool instead."
        
        # Check if file has been read
        read_timestamp = read_file_timestamps.get(full_file_path)
        if not read_timestamp:
            return False, "File has not been read yet. Read it first before writing to it."
        
        # Check if file has been modified since read
        try:
            last_write_time = os.path.getmtime(full_file_path)
            if last_write_time > read_timestamp:
                return False, "File has been modified since read, either by the user or by a linter. Read it again before attempting to write it."
        except OSError as e:
            return False, f"Cannot access file: {e}"
        
        # Read file and check for old_string
        try:
            file_content = EditTool._read_file(full_file_path)
        except Exception as e:
            return False, f"Cannot read file: {e}"
        
        if old_string not in file_content:
            return False, "String to replace not found in file."
        
        # Check for multiple occurrences
        matches = file_content.count(old_string)
        if matches > 1:
            return False, f"Found {matches} matches of the string to replace. For safety, this tool only supports replacing exactly one occurrence at a time. Add more lines of context to your edit and try again."
        
        return True, None
    
    @staticmethod
    def generate_preview(
        file_path: str,
        old_string: str,
        new_string: str,
        read_file_timestamps: Dict[str, float]
    ) -> Tuple[bool, str]:
        """
        Generate a preview of the edit operation.
        
        Args:
            file_path: Path to the file to edit
            old_string: Text to replace
            new_string: Text to replace it with
            read_file_timestamps: Dictionary of file read timestamps
            
        Returns:
            Tuple of (success, preview_string_or_error)
        """
        # Validate input
        is_valid, error_msg = EditTool.validate_input(
            file_path, old_string, new_string, read_file_timestamps
        )
        if not is_valid:
            return False, f"Cannot preview edit: {error_msg}"
        
        # Resolve full path
        full_file_path = file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)
        
        # Read original file if it exists
        original_file = ""
        if os.path.exists(full_file_path):
            try:
                original_file = EditTool._read_file(full_file_path)
            except Exception as e:
                return False, f"Cannot read file for preview: {e}"
        
        # Apply the edit
        if old_string == "":
            # Create new file
            updated_file = new_string
        else:
            # Edit existing file
            updated_file = original_file.replace(old_string, new_string, 1)
        
        # Generate diff
        diff_lines = list(difflib.unified_diff(
            original_file.splitlines(keepends=True),
            updated_file.splitlines(keepends=True),
            fromfile=file_path,
            tofile=file_path,
            lineterm=''
        ))
        
        return True, (diff_lines, file_path)
    
    @staticmethod
    def get_snippet(initial_text: str, old_str: str, new_str: str) -> Tuple[str, int]:
        """
        Get a snippet of the file around the change with context.
        
        Returns:
            (snippet, start_line_number)
        """
        if not initial_text and old_str == "":
            # New file creation
            new_file_lines = new_str.split('\n')
            snippet_lines = new_file_lines[:N_LINES_SNIPPET * 2 + 1]
            return '\n'.join(snippet_lines), 1
        
        before = initial_text.split(old_str)[0] if old_str in initial_text else ""
        replacement_line = len(before.split('\n')) - 1 if before else 0
        new_file_lines = initial_text.replace(old_str, new_str).split('\n')
        
        # Calculate the start and end line numbers for the snippet
        start_line = max(0, replacement_line - N_LINES_SNIPPET)
        end_line = replacement_line + N_LINES_SNIPPET + len(new_str.split('\n'))
        
        # Get snippet
        snippet_lines = new_file_lines[start_line:end_line + 1]
        snippet = '\n'.join(snippet_lines)
        return snippet, start_line + 1
    
    @staticmethod
    async def execute(
        file_path: str,
        old_string: str,
        new_string: str,
        read_file_timestamps: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Execute file edit.
        
        Returns:
            Dictionary with file_path, snippet, and diff information
        """
        # Validate input
        is_valid, error_msg = EditTool.validate_input(
            file_path, old_string, new_string, read_file_timestamps
        )
        if not is_valid:
            return {
                "success": False,
                "error": error_msg,
                "file_path": file_path
            }
        
        # Resolve full path
        full_file_path = file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(full_file_path) or '.', exist_ok=True)
        
        # Read original file if it exists
        original_file = ""
        if os.path.exists(full_file_path):
            original_file = EditTool._read_file(full_file_path)
        
        # Apply the edit
        if old_string == "":
            # Create new file
            updated_file = new_string
        else:
            # Edit existing file
            updated_file = original_file.replace(old_string, new_string, 1)
        
        # Generate diff
        diff_lines = list(difflib.unified_diff(
            original_file.splitlines(keepends=True),
            updated_file.splitlines(keepends=True),
            fromfile=file_path,
            tofile=file_path,
            lineterm=''
        ))
        
        # Write the updated content
        try:
            EditTool._write_file(full_file_path, updated_file)
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
        
        # Get snippet for display
        snippet, start_line = EditTool.get_snippet(original_file, old_string, new_string)
        
        return {
            "success": True,
            "file_path": file_path,
            "snippet": snippet,
            "start_line": start_line,
            "diff": diff_lines,
            "original_file": original_file,
            "updated_file": updated_file
        }
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format tool result for display to LLM."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        file_path = result.get("file_path", "")
        snippet = result.get("snippet", "")
        start_line = result.get("start_line", 1)
        
        # Add line numbers to snippet
        numbered_lines = []
        for i, line in enumerate(snippet.split('\n'), start=start_line):
            numbered_lines.append(f"{i:4d} | {line}")
        
        output = f"The file {file_path} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:\n"
        output += '\n'.join(numbered_lines)
        
        return output

