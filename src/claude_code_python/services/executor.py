"""Parallel agent execution and synthesis."""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from .openai_client import OpenAIClient
from .agent_manager import AgentConfig
from ..utils.prompts import get_system_prompt


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_index: int
    content: str
    tool_use_count: int
    tokens: int
    duration_ms: int


class ParallelExecutor:
    """Executor for parallel agent tasks."""
    
    def __init__(self, client: OpenAIClient):
        """Initialize executor with OpenAI client."""
        self.client = client
    
    async def execute_agent_task(
        self,
        task_prompt: str,
        agent_index: int,
        agent_config: AgentConfig,
        functions: List[Dict[str, Any]],
        function_executor: Callable,
        max_iterations: int = 10
    ) -> AgentResult:
        """
        Execute a single agent task.
        
        Args:
            task_prompt: Task description
            agent_index: Index of this agent
            agent_config: Agent configuration
            functions: Available tools
            function_executor: Tool executor function
            max_iterations: Max tool call iterations
            
        Returns:
            AgentResult with execution details
        """
        import time
        start_time = time.time()
        
        # Create initial message
        messages = [{"role": "user", "content": task_prompt}]
        
        # Combine agent's system prompt with base agent prompt
        combined_prompt = f"{get_system_prompt()}\n\n{agent_config.system_prompt}"
        
        # Execute with combined system prompt
        result = await self.client.query(
            messages=messages,
            system_prompt=combined_prompt,
            tools=functions,
            tool_executor=function_executor,
            max_iterations=max_iterations
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_index=agent_index,
            content=result.get("content", ""),
            tool_use_count=result.get("tool_use_count", 0),
            tokens=result.get("total_tokens", 0),
            duration_ms=duration_ms
        )
    
    async def execute_parallel_tasks(
        self,
        task_prompt: str,
        agent_config: AgentConfig,
        num_agents: int,
        functions: List[Dict[str, Any]],
        function_executor: Callable,
        max_iterations: int = 10
    ) -> List[AgentResult]:
        """
        Execute multiple agents in parallel.
        
        Args:
            task_prompt: Task description
            agent_config: Agent configuration to use
            num_agents: Number of parallel agents
            functions: Available tools
            function_executor: Tool executor function
            max_iterations: Max tool call iterations
            
        Returns:
            List of AgentResult objects
        """
        # Create tasks for parallel execution
        tasks = []
        for i in range(num_agents):
            task = self.execute_agent_task(
                task_prompt=f"{task_prompt}\n\nProvide a thorough and complete analysis.",
                agent_index=i,
                agent_config=agent_config,
                functions=functions,
                function_executor=function_executor,
                max_iterations=max_iterations
            )
            tasks.append(task)
        
        # Execute all agents in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Agent {i} failed with error: {result}")
                # Create error result
                valid_results.append(AgentResult(
                    agent_index=i,
                    content=f"Agent execution failed: {result}",
                    tool_use_count=0,
                    tokens=0,
                    duration_ms=0
                ))
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def synthesize_results(
        self,
        original_task: str,
        agent_results: List[AgentResult],
        agent_config: AgentConfig
    ) -> AgentResult:
        """
        Synthesize results from multiple agents into a unified response.
        
        Args:
            original_task: Original task prompt
            agent_results: Results from parallel agents
            agent_config: Agent configuration
            
        Returns:
            Synthesized AgentResult
        """
        import time
        start_time = time.time()
        
        # Build synthesis prompt
        results_text = []
        for result in sorted(agent_results, key=lambda r: r.agent_index):
            results_text.append(
                f"== AGENT {result.agent_index + 1} RESPONSE ==\n{result.content}\n"
            )
        
        synthesis_prompt = f"""Original task: {original_task}

I've assigned multiple agents to tackle this task. Each agent has analyzed the problem and provided their findings.

{chr(10).join(results_text)}

Based on all the information provided by these agents, synthesize a comprehensive and cohesive response that:
1. Combines the key insights from all agents
2. Resolves any contradictions between agent findings
3. Presents a unified solution that addresses the original task
4. Includes all important details from the individual responses
5. Is well-structured and complete

Your synthesis should be thorough but focused on the original task."""
        
        # Execute synthesis (without tool calling)
        messages = [{"role": "user", "content": synthesis_prompt}]
        
        # Use agent prompt for synthesis
        combined_prompt = f"{get_system_prompt()}\n\n{agent_config.system_prompt}"
        
        result = await self.client.query(
            messages=messages,
            system_prompt=combined_prompt,
            tools=None,  # No tool calling for synthesis
            tool_executor=None,
            max_iterations=1
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return AgentResult(
            agent_index=-1,  # Synthesis agent
            content=result.get("content", ""),
            tool_use_count=0,
            tokens=result.get("total_tokens", 0),
            duration_ms=duration_ms
        )

