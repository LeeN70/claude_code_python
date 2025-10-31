"""Permission system for tool execution."""
from typing import Optional


def format_bash_preview(command: str) -> str:
    """
    Format a bash command for preview display.
    
    Args:
        command: The bash command to format
        
    Returns:
        Formatted preview string
    """
    preview = "\n" + "=" * 60 + "\n"
    preview += "BASH COMMAND PREVIEW\n"
    preview += "=" * 60 + "\n"
    preview += f"\n{command}\n"
    preview += "\n" + "=" * 60 + "\n"
    return preview


def format_diff_preview(diff_lines: list, file_path: str, operation: str = "edit") -> str:
    """
    Format a unified diff for preview display.
    
    Args:
        diff_lines: List of diff lines from difflib.unified_diff
        file_path: Path to the file being modified
        operation: Type of operation ("edit", "write", "create")
        
    Returns:
        Formatted preview string
    """
    preview = "\n" + "=" * 60 + "\n"
    preview += f"FILE {operation.upper()} PREVIEW: {file_path}\n"
    preview += "=" * 60 + "\n"
    
    if not diff_lines:
        preview += "\n[No changes to display]\n"
    else:
        preview += "\n"
        for line in diff_lines:
            preview += line
            if not line.endswith('\n'):
                preview += '\n'
    
    preview += "=" * 60 + "\n"
    return preview


def format_write_preview(file_path: str, content: str, exists: bool, max_lines: int = 20) -> str:
    """
    Format a write operation preview.
    
    Args:
        file_path: Path to the file being written
        content: Content to be written
        exists: Whether the file already exists
        max_lines: Maximum number of lines to show in preview
        
    Returns:
        Formatted preview string
    """
    preview = "\n" + "=" * 60 + "\n"
    if exists:
        preview += f"FILE OVERWRITE PREVIEW: {file_path}\n"
    else:
        preview += f"FILE CREATION PREVIEW: {file_path}\n"
    preview += "=" * 60 + "\n"
    
    lines = content.split('\n')
    preview += f"\nShowing first {min(len(lines), max_lines)} lines:\n\n"
    
    for i, line in enumerate(lines[:max_lines], 1):
        preview += f"{i:4d} | {line}\n"
    
    if len(lines) > max_lines:
        preview += f"\n... ({len(lines) - max_lines} more lines)\n"
    
    preview += "\n" + "=" * 60 + "\n"
    return preview


def prompt_user_permission(preview: str, tool_name: str) -> bool:
    """
    Prompt user for permission to execute a tool.
    
    Args:
        preview: Formatted preview of the operation
        tool_name: Name of the tool being executed
        
    Returns:
        True if user approves, False otherwise
    """
    print(preview)
    print(f"\nPermission required to execute {tool_name} tool")
    print("Do you want to proceed? (yes/no): ", end="", flush=True)
    
    try:
        response = input().strip().lower()
        
        # Accept y, yes for approval
        if response in ['y', 'yes']:
            return True
        # Accept n, no, or any other input for rejection
        else:
            return False
            
    except (EOFError, KeyboardInterrupt):
        print("\n")
        return False

