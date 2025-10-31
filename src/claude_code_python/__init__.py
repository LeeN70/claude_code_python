"""Claude Code Python - AI Coding Assistant.

A minimal Python implementation of Claude Code with bash execution,
parallel agent capabilities, and AI-powered coding assistance.
"""

__version__ = "0.1.0"
__author__ = "LeeN70"
__license__ = "MIT"

from .main import ClaudeCodeCLI, main

__all__ = ["ClaudeCodeCLI", "main", "__version__"]

