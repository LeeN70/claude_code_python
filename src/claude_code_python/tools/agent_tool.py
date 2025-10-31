"""Agent orchestration tool for parallel task execution."""
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field
from ..services.agent_manager import load_all_agents, find_agent_by_type
from ..services.executor import ParallelExecutor


class AgentToolInput(BaseModel):
    """Input schema for agent tool."""
    prompt: str = Field(description="The task for the agent to perform")
    subagent_type: Optional[str] = Field(default="general-purpose", description="Type of agent to use")
    description: Optional[str] = Field(default=None, description="Brief description of the task")


class AgentTool:
    """Tool for launching parallel agent tasks."""
    
    name = "agent"
    description = "Launch parallel agents to handle complex, multi-step tasks autonomously"
    
    def __init__(self, executor: ParallelExecutor):
        """Initialize with parallel executor."""
        self.executor = executor
    
    @staticmethod
    def get_tool_schema() -> Dict[str, Any]:
        """Get OpenAI tool schema (new format)."""
        # Load available agents for description
        agents = load_all_agents()
        agent_descriptions = []
        for agent in agents:
            tools_str = ", ".join(agent.tools) if agent.tools else "none"
            agent_descriptions.append(
                f"- {agent.agent_type}: {agent.when_to_use} (Tools: {tools_str})"
            )
        
        description = f"""Launch parallel agents to handle complex tasks autonomously.

Available agent types:
{chr(10).join(agent_descriptions)}

When to use:
- Complex multi-step tasks requiring research
- Tasks that benefit from multiple perspectives
- Code analysis across multiple files

When NOT to use:
- Simple single-file operations
- Direct file reads (use read tools instead)
- Quick searches (use grep instead)"""
        
        return {
            "type": "function",
            "function": {
                "name": "agent",
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Detailed task description for the agent to perform autonomously"
                        },
                        "subagent_type": {
                            "type": "string",
                            "description": "Type of agent to use (default: general-purpose)",
                            "default": "general-purpose"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional brief description of the task"
                        }
                    },
                    "required": ["prompt"]
                }
            }
        }
    
    async def execute(
        self,
        prompt: str,
        subagent_type: str = "general-purpose",
        description: Optional[str] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_executor: Optional[Callable] = None,
        parallel_count: int = 3
    ) -> Dict[str, Any]:
        """
        Execute agent task with parallel agents.
        
        Args:
            prompt: Task description
            subagent_type: Type of agent to use
            description: Optional task description
            functions: Available tools for agents
            function_executor: Tool executor
            parallel_count: Number of parallel agents (default 3)
            
        Returns:
            Dictionary with synthesized result and metadata
        """
        # Find agent configuration
        agent_config = find_agent_by_type(subagent_type)
        if not agent_config:
            return {
                "content": f"Error: Agent type '{subagent_type}' not found",
                "tool_use_count": 0,
                "tokens": 0
            }
        
        # Filter tools based on agent's allowed tools
        agent_functions = functions
        if agent_config.tools != ["*"] and functions:
            # Filter to only allowed tools
            allowed_names = set(agent_config.tools)
            # Extract function name from tool schema
            agent_functions = [
                f for f in functions 
                if f.get("function", {}).get("name") in allowed_names
            ]
        
        # Execute parallel agents if parallel_count > 1
        if parallel_count > 1:
            # Execute parallel agents
            agent_results = await self.executor.execute_parallel_tasks(
                task_prompt=prompt,
                agent_config=agent_config,
                num_agents=parallel_count,
                functions=agent_functions,
                function_executor=function_executor,
                max_iterations=10
            )
            
            # Synthesize results
            synthesis_result = await self.executor.synthesize_results(
                original_task=prompt,
                agent_results=agent_results,
                agent_config=agent_config
            )
            
            # Calculate totals
            total_tool_uses = sum(r.tool_use_count for r in agent_results)
            total_tokens = sum(r.tokens for r in agent_results) + synthesis_result.tokens
            
            return {
                "content": synthesis_result.content,
                "tool_use_count": total_tool_uses,
                "tokens": total_tokens,
                "parallel_agents": parallel_count,
                "synthesis": True
            }
        else:
            # Single agent execution
            result = await self.executor.execute_agent_task(
                task_prompt=prompt,
                agent_index=0,
                agent_config=agent_config,
                functions=agent_functions,
                function_executor=function_executor,
                max_iterations=10
            )
            
            return {
                "content": result.content,
                "tool_use_count": result.tool_use_count,
                "tokens": result.tokens,
                "parallel_agents": 1,
                "synthesis": False
            }
    
    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format tool result for display to LLM."""
        return result.get("content", "")

