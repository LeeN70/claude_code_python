"""Agent configuration management."""
import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import yaml


@dataclass
class AgentConfig:
    """Agent configuration."""
    agent_type: str
    when_to_use: str
    tools: List[str]
    system_prompt: str
    location: str  # 'built-in', 'project', or 'user'
    file_path: Optional[str] = None


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.
    
    Returns:
        (frontmatter_dict, remaining_content)
    """
    # Match frontmatter pattern: --- at start, content, --- again
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return {}, content
    
    frontmatter_text = match.group(1)
    remaining_content = match.group(2)
    
    # Parse YAML
    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        frontmatter = {}
    
    return frontmatter, remaining_content


def parse_tools_list(tools_input: Any) -> List[str]:
    """Parse tools list from various formats."""
    if tools_input is None:
        return []
    
    if isinstance(tools_input, str):
        # Split by comma and strip whitespace
        tools = [t.strip() for t in tools_input.split(',') if t.strip()]
        return tools
    
    if isinstance(tools_input, list):
        return [str(t).strip() for t in tools_input if t]
    
    return []


def get_built_in_agents() -> List[AgentConfig]:
    """Get built-in agent configurations."""
    return [
        AgentConfig(
            agent_type="general-purpose",
            when_to_use="General-purpose agent for researching, searching code, and multi-step tasks",
            tools=["*"],
            system_prompt="""You are an agent for a coding assistant. Given the user's message, use the available tools to complete the task.

Your strengths:
- Searching for code, configurations, and patterns across codebases
- Analyzing multiple files to understand system architecture
- Performing multi-step research tasks

Guidelines:
- Be thorough and check multiple locations
- Consider different naming conventions
- In your final response, share relevant details and findings
- Provide clear, actionable information""",
            location="built-in"
        )
    ]


def scan_agent_files(agents_dir: str) -> List[AgentConfig]:
    """
    Scan directory for agent configuration files (.md).
    
    Args:
        agents_dir: Directory to scan
        
    Returns:
        List of AgentConfig objects
    """
    agents = []
    
    if not os.path.exists(agents_dir):
        return agents
    
    # Walk directory tree
    for root, dirs, files in os.walk(agents_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if not file.endswith('.md'):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                frontmatter, system_prompt = parse_frontmatter(content)
                
                # Validate required fields
                agent_type = frontmatter.get('agent-type') or frontmatter.get('agent_type')
                when_to_use = frontmatter.get('when-to-use') or frontmatter.get('when_to_use')
                allowed_tools = frontmatter.get('allowed-tools') or frontmatter.get('allowed_tools')
                
                if not agent_type:
                    continue
                
                if not when_to_use:
                    continue
                
                # Parse tools
                tools = parse_tools_list(allowed_tools)
                if not tools:
                    tools = ["*"]
                
                agents.append(AgentConfig(
                    agent_type=agent_type,
                    when_to_use=when_to_use,
                    tools=tools,
                    system_prompt=system_prompt.strip(),
                    location='project',
                    file_path=file_path
                ))
                
            except Exception as e:
                print(f"Error loading agent from {file_path}: {e}")
                continue
    
    return agents


def load_all_agents(project_dir: Optional[str] = None) -> List[AgentConfig]:
    """
    Load all agent configurations.
    
    Args:
        project_dir: Project directory (defaults to current directory)
        
    Returns:
        List of all agents (built-in + project)
    """
    agents = get_built_in_agents()
    
    # Load project agents from .claude/agents/
    if project_dir is None:
        project_dir = os.getcwd()
    
    project_agents_dir = os.path.join(project_dir, '.claude', 'agents')
    project_agents = scan_agent_files(project_agents_dir)
    
    agents.extend(project_agents)
    
    return agents


def find_agent_by_type(agent_type: str, project_dir: Optional[str] = None) -> Optional[AgentConfig]:
    """Find an agent by its type."""
    agents = load_all_agents(project_dir)
    
    for agent in agents:
        if agent.agent_type == agent_type:
            return agent
    
    return None

