#!/usr/bin/env python3
"""Main entry point for Claude Code Python."""
import os
import sys
import asyncio
import argparse
from typing import List, Dict, Any
from .services.openai_client import OpenAIClient
from .services.executor import ParallelExecutor
from .tools.bash_tool import BashTool
from .tools.agent_tool import AgentTool
from .tools.todowrite_tool import TodoWriteTool
from .tools.edit_tool import EditTool
from .tools.read_tool import ReadTool
from .tools.write_tool import WriteTool
from .tools.glob_tool import GlobTool
from .tools.grep_tool import GrepTool
from .utils.prompts import get_system_prompt


class ClaudeCodeCLI:
    """Simple CLI for Claude Code."""
    
    def __init__(self):
        """Initialize CLI."""
        self.client = OpenAIClient()
        self.executor = ParallelExecutor(self.client)
        self.bash_tool = BashTool()
        self.agent_tool = AgentTool(self.executor)
        self.todowrite_tool = TodoWriteTool()
        self.edit_tool = EditTool()
        self.read_tool = ReadTool()
        self.write_tool = WriteTool()
        self.glob_tool = GlobTool()
        self.grep_tool = GrepTool()
        self.conversation_history: List[Dict[str, Any]] = []
        self.read_file_timestamps: Dict[str, float] = {}
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools."""
        return [
            self.bash_tool.get_tool_schema(),
            self.edit_tool.get_tool_schema(),
            self.read_tool.get_tool_schema(),
            self.write_tool.get_tool_schema(),
            self.glob_tool.get_tool_schema(),
            self.grep_tool.get_tool_schema(),
            self.todowrite_tool.get_tool_schema()
            # self.agent_tool.get_tool_schema()
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool call."""
        if tool_name == "bash":
            # Print tool execution info
            command = arguments.get('command', '')
            print(f"\nusing bash tool: {command}")
            result = await self.bash_tool.execute(**arguments)
            return self.bash_tool.format_result(result)
        elif tool_name == "edit":
            # Print tool execution info
            file_path = arguments.get('file_path', '')
            print(f"\nusing edit tool: {file_path}")
            result = await self.edit_tool.execute(**arguments, read_file_timestamps=self.read_file_timestamps)
            return self.edit_tool.format_result(result)
        elif tool_name == "read":
            # Print tool execution info
            file_path = arguments.get('file_path', '')
            print(f"\nusing read tool: {file_path}")
            result = await self.read_tool.execute(**arguments, read_file_timestamps=self.read_file_timestamps)
            return self.read_tool.format_result(result)
        elif tool_name == "write":
            # Print tool execution info
            file_path = arguments.get('file_path', '')
            print(f"\nusing write tool: {file_path}")
            result = await self.write_tool.execute(**arguments, read_file_timestamps=self.read_file_timestamps)
            return self.write_tool.format_result(result)
        elif tool_name == "glob":
            # Print tool execution info
            pattern = arguments.get('pattern', '')
            print(f"\nusing glob tool: {pattern}")
            result = await self.glob_tool.execute(**arguments)
            return self.glob_tool.format_result(result)
        elif tool_name == "grep":
            # Print tool execution info
            pattern = arguments.get('pattern', '')
            print(f"\nusing grep tool: {pattern}")
            result = await self.grep_tool.execute(**arguments)
            return self.grep_tool.format_result(result)
        elif tool_name == "todo_write":
            # Print tool execution info
            todo_count = len(arguments.get('todos', []))
            print(f"\nusing todo_write tool: managing {todo_count} tasks")
            result = await self.todowrite_tool.execute(**arguments)
            return self.todowrite_tool.format_result(result)
        elif tool_name == "agent":
            # Print tool execution info
            subagent_type = arguments.get('subagent_type', 'general-purpose')
            print(f"\nusing agent tool: {subagent_type}")
            result = await self.agent_tool.execute(
                **arguments,
                functions=self.get_tools(),
                function_executor=self.execute_tool,
                parallel_count=int(os.getenv("PARALLEL_AGENTS", "1"))
            )
            return self.agent_tool.format_result(result)
        else:
            return f"Unknown tool: {tool_name}"
    
    async def run_query(self, user_input: str) -> str:
        """Run a query through the system."""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Query with tool calling
        result = await self.client.query(
            messages=self.conversation_history,
            system_prompt=get_system_prompt(),
            tools=self.get_tools(),
            tool_executor=self.execute_tool,
            max_iterations=15
        )
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": result["content"]
        })
        
        return result["content"]
    
    async def interactive_mode(self):
        """Run interactive conversation mode."""
        print("=" * 60)
        print("Claude Code Python - Interactive Mode")
        print("Type 'exit' or 'quit' to end the session")
        print("=" * 60)
        
        while True:
            try:
                # Get user input
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                
                # Process query
                print("\nAssistant: ", end="", flush=True)
                response = await self.run_query(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
    
    async def single_query_mode(self, query: str):
        """Run a single query and exit."""
        response = await self.run_query(query)
        print(response)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Claude Code Python - AI Coding Assistant")
    parser.add_argument("query", nargs="*", help="Query to process (omit for interactive mode)")
    parser.add_argument("--model", help="OpenAI model to use", default=None)
    parser.add_argument("--parallel-agents", type=int, help="Number of parallel agents", default=1)
    
    args = parser.parse_args()
    
    # Set environment variables from args
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    if args.parallel_agents:
        os.environ["PARALLEL_AGENTS"] = str(args.parallel_agents)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    # Initialize CLI
    cli = ClaudeCodeCLI()
    
    # Run in appropriate mode
    if args.query:
        # Single query mode
        query = " ".join(args.query)
        await cli.single_query_mode(query)
    else:
        # Interactive mode
        await cli.interactive_mode()


def cli_entry():
    """CLI entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_entry()

