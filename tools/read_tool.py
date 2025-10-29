"""File read tool for reading text and image files."""
import os
import base64
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


# File size limit for text files (0.25MB)
MAX_OUTPUT_SIZE = 0.25 * 1024 * 1024

# Image file extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

# Max image size (3.75MB for base64 encoding overhead)
MAX_IMAGE_SIZE = 3.75 * 1024 * 1024


class ReadToolInput(BaseModel):
    """Input schema for read tool."""
    file_path: str = Field(description="The absolute path to the file to read")
    offset: Optional[int] = Field(default=None, description="The line number to start reading from")
    limit: Optional[int] = Field(default=None, description="The number of lines to read")


class ReadTool:
    """Tool for reading files."""
    
    name = "read"
    description = "A tool for reading files (text and images)"
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema."""
        return {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read a file from the filesystem. Supports text files with optional line offset/limit, and image files (returns base64).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to read (absolute or relative)"
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Optional line number to start reading from (1-indexed). Only for text files."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Optional number of lines to read. Only for text files."
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }
    
    @staticmethod
    def _is_image_file(file_path: str) -> bool:
        """Check if file is an image based on extension."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in IMAGE_EXTENSIONS
    
    @staticmethod
    def _read_text_file(file_path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> Tuple[str, int, int]:
        """
        Read text file with optional offset/limit.
        
        Returns:
            (content, line_count, total_lines)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                all_lines = f.readlines()
        
        total_lines = len(all_lines)
        
        # Handle offset and limit
        start_idx = (offset - 1) if offset else 0
        start_idx = max(0, start_idx)
        
        if limit:
            end_idx = start_idx + limit
            selected_lines = all_lines[start_idx:end_idx]
        else:
            selected_lines = all_lines[start_idx:]
        
        content = ''.join(selected_lines)
        line_count = len(selected_lines)
        
        return content, line_count, total_lines
    
    @staticmethod
    def _read_image_file(file_path: str) -> Dict[str, Any]:
        """
        Read image file and return base64 encoded data.
        
        Returns:
            Dictionary with type, base64 data, and media type
        """
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        # Get media type from extension
        ext = os.path.splitext(file_path)[1].lower()
        media_type = f"image/{ext[1:]}"  # Remove the dot
        if ext == '.jpg':
            media_type = "image/jpeg"
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        return {
            "type": "image",
            "base64": base64_data,
            "media_type": media_type,
            "file_path": file_path
        }
    
    @staticmethod
    async def execute(
        file_path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        read_file_timestamps: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Execute file read.
        
        Returns:
            Dictionary with file content and metadata
        """
        # Resolve full path
        full_file_path = file_path if os.path.isabs(file_path) else os.path.join(os.getcwd(), file_path)
        
        # Check if file exists
        if not os.path.exists(full_file_path):
            return {
                "success": False,
                "error": "File does not exist.",
                "file_path": file_path
            }
        
        # Check if it's a directory
        if os.path.isdir(full_file_path):
            return {
                "success": False,
                "error": "Path is a directory, not a file.",
                "file_path": file_path
            }
        
        # Get file size
        file_size = os.path.getsize(full_file_path)
        
        try:
            # Handle image files
            if ReadTool._is_image_file(full_file_path):
                if file_size > MAX_IMAGE_SIZE:
                    return {
                        "success": False,
                        "error": f"Image file too large ({file_size / (1024*1024):.2f}MB). Maximum size is {MAX_IMAGE_SIZE / (1024*1024):.2f}MB.",
                        "file_path": file_path
                    }
                
                result = ReadTool._read_image_file(full_file_path)
                
                # Update timestamp
                if read_file_timestamps is not None:
                    read_file_timestamps[full_file_path] = os.path.getmtime(full_file_path)
                
                return {
                    "success": True,
                    **result
                }
            
            # Handle text files
            # Check size before reading if no offset/limit
            if file_size > MAX_OUTPUT_SIZE and not offset and not limit:
                return {
                    "success": False,
                    "error": f"File too large ({file_size / 1024:.0f}KB). Maximum size is {MAX_OUTPUT_SIZE / 1024:.0f}KB. Use offset and limit parameters to read specific portions.",
                    "file_path": file_path
                }
            
            content, line_count, total_lines = ReadTool._read_text_file(full_file_path, offset, limit)
            
            # Check content size after reading
            if len(content) > MAX_OUTPUT_SIZE:
                return {
                    "success": False,
                    "error": f"File content too large ({len(content) / 1024:.0f}KB). Use offset and limit parameters to read specific portions.",
                    "file_path": file_path
                }
            
            # Update timestamp
            if read_file_timestamps is not None:
                read_file_timestamps[full_file_path] = os.path.getmtime(full_file_path)
            
            return {
                "success": True,
                "type": "text",
                "file_path": file_path,
                "content": content,
                "line_count": line_count,
                "total_lines": total_lines,
                "start_line": offset or 1
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}",
                "file_path": file_path
            }
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format tool result for display to LLM."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        result_type = result.get("type")
        
        if result_type == "image":
            # For images, return a message indicating the image was read
            # The actual base64 data will be sent separately in the message
            return f"Successfully read image file: {result.get('file_path')}"
        
        elif result_type == "text":
            file_path = result.get("file_path", "")
            content = result.get("content", "")
            start_line = result.get("start_line", 1)
            line_count = result.get("line_count", 0)
            total_lines = result.get("total_lines", 0)
            
            if not content:
                return "File is empty."
            
            # Add line numbers to content
            lines = content.split('\n')
            numbered_lines = []
            for i, line in enumerate(lines, start=start_line):
                numbered_lines.append(f"{i:6d}|{line}")
            
            output = '\n'.join(numbered_lines)
            
            # Add info about partial reads
            if line_count < total_lines:
                output += f"\n\n(Showing lines {start_line}-{start_line + line_count - 1} of {total_lines} total lines)"
            
            return output
        
        return "Unknown result type"

