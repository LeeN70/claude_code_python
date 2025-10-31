"""Input validation utilities."""
import os
import shlex
from typing import Tuple


# Commands that are banned for security reasons
BANNED_COMMANDS = [
    'rm', 'mkfs', 'dd', 'format', 'fdisk',
    'shutdown', 'reboot', 'init', 'halt', 'poweroff'
]


def validate_bash_command(command: str, cwd: str) -> Tuple[bool, str]:
    """
    Validate a bash command for security.
    
    Returns:
        (is_valid, error_message)
    """
    if not command or not command.strip():
        return False, "Command cannot be empty"
    
    # Parse command into parts
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return False, f"Invalid command syntax: {e}"
    
    if not parts:
        return False, "Command cannot be empty"
    
    # Check for banned commands
    base_cmd = parts[0].split('/')[-1]  # Handle paths like /bin/rm
    if base_cmd in BANNED_COMMANDS:
        return False, f"Command '{base_cmd}' is not allowed for security reasons"
    
    # Special handling for cd command - restrict to subdirectories
    if base_cmd == 'cd' and len(parts) > 1:
        target_dir = parts[1]
        # Resolve the target directory
        if os.path.isabs(target_dir):
            full_target = target_dir
        else:
            full_target = os.path.normpath(os.path.join(cwd, target_dir))
        
        # Check if target is within or below cwd
        if not full_target.startswith(cwd):
            return False, f"cd to '{full_target}' is not allowed. Can only cd to subdirectories"
    
    return True, ""


def truncate_output(output: str, max_lines: int = 1000) -> Tuple[str, int]:
    """
    Truncate output if it exceeds max_lines.
    
    Returns:
        (truncated_output, total_lines)
    """
    if not output:
        return "", 0
    
    lines = output.split('\n')
    total_lines = len(lines)
    
    if total_lines <= max_lines:
        return output, total_lines
    
    # Keep first and last portions
    keep_lines = max_lines // 2
    truncated_lines = (
        lines[:keep_lines] +
        [f"\n... ({total_lines - max_lines} lines truncated) ...\n"] +
        lines[-keep_lines:]
    )
    
    return '\n'.join(truncated_lines), total_lines

