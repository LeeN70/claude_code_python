# Claude Code Python

A minimal Python implementation of Claude Code - a command-line AI coding assistant with bash execution and parallel agent capabilities.

## Features

- **Bash Tool**: Execute shell commands with security validation
- **Agent Tool**: Launch parallel agents for complex multi-step tasks
- **OpenAI Function Calling**: Uses OpenAI API with function calling
- **Agent Configuration**: Load custom agents from `.claude/agents/*.md` files

## Installation

### Quick Install (Recommended)

Install the package globally to use the `vibe` command from anywhere:

```bash
# Clone the repository
git clone https://github.com/LeeN70/claude_code_python.git
cd claude_code_python

# Install in development mode (changes reflect immediately)
pip install -e .

# Or install normally
pip install .
```

After installation, you can use `vibe` from any directory!

### Manual Setup (Without Installation)

```bash
# Install dependencies only
pip install -r requirements.txt

# Run directly with Python
python main.py
```

### Environment Variables

```bash
# Set OpenAI API key (required)
export OPENAI_API_KEY="your-api-key-here"

# Optional: Set custom OpenAI endpoint
export OPENAI_BASE_URL="https://your-endpoint.com/v1"

# Optional: Set model (default: gpt-4)
export OPENAI_MODEL="gpt-4"
```

## Usage

### Using the Global Command (After Installation)

Once installed, use `vibe` from any directory:

```bash
# Interactive mode
vibe

# Single query mode
vibe "List files in current directory"

# With options
vibe --help
vibe --model gpt-4 --parallel-agents 5 "Analyze this project"
```

### Using Python Directly (Without Installation)

```bash
# Interactive mode
python main.py

# Single query mode
python main.py "List files in current directory"

# Command-line options
python main.py --help
python main.py --model gpt-4 --parallel-agents 5
```

## Tools

### Bash Tool

Execute shell commands with security validation:
- Validates commands for safety
- Blocks dangerous commands (rm, dd, mkfs, etc.)
- Restricts `cd` to subdirectories only
- Configurable timeout (default 120s, max 600s)
- Truncates long output automatically

### Agent Tool

Launch parallel agents for complex tasks:
- Parallel execution with configurable agent count (default 3)
- Result synthesis from multiple agent perspectives
- Custom agent configurations via `.claude/agents/*.md` files
- Tool filtering based on agent permissions

## Agent Configuration

Create custom agents by placing `.md` files in `.claude/agents/`:

```markdown
---
agent-type: code-analyzer
when-to-use: Analyze code structure and patterns
allowed-tools: bash, agent
---

You are a code analysis agent. Your task is to analyze code structure,
identify patterns, and provide insights about the codebase architecture.

Guidelines:
- Focus on code organization and design patterns
- Identify potential improvements
- Provide clear, actionable recommendations
```

### Agent Configuration Fields

- `agent-type`: Unique identifier for the agent
- `when-to-use`: Description of when to use this agent
- `allowed-tools`: Comma-separated list of tools, or `*` for all tools

The content after the frontmatter becomes the agent's system prompt.

## Architecture

```
claude_code_python/
├── main.py              # CLI entry point
├── tools/
│   ├── bash_tool.py     # Bash command execution
│   └── agent_tool.py    # Agent orchestration
├── services/
│   ├── openai_client.py # OpenAI API integration
│   ├── agent_manager.py # Agent config loading
│   └── executor.py      # Parallel execution
└── utils/
    ├── messages.py      # Message formatting
    └── validation.py    # Input validation
```

## Security

- Commands are validated before execution
- Dangerous commands are blocked
- Directory changes restricted to subdirectories
- Timeout protection for long-running commands
- Output truncation to prevent memory issues

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key (required)
- `OPENAI_BASE_URL`: Custom OpenAI endpoint (optional)
- `OPENAI_MODEL`: Model to use (default: gpt-4)
- `PARALLEL_AGENTS`: Number of parallel agents (default: 1)

## Examples

### Using the `vibe` Command

```bash
# Simple bash command
vibe "Show current directory and list files"

# Complex multi-step task with agents
vibe "Analyze the Python files in this project and summarize the architecture"

# Interactive mode - just type vibe!
vibe
> What files are in this directory?
> Can you analyze the main.py file?
> exit

# From any directory
cd /tmp
vibe "Create a hello world Python script"
```

### Using Python Directly

```bash
# Simple bash command
python main.py "Show current directory and list files"

# Complex multi-step task with agents
python main.py "Analyze the Python files in this project and summarize the architecture"

# Interactive mode
python main.py
> What files are in this directory?
> Can you analyze the main.py file?
> exit
```

## License

MIT License - feel free to use and modify as needed.

