#!/usr/bin/env python3
"""Basic tests for Claude Code Python."""
import asyncio
import os
from .tools.bash_tool import BashTool
from .services.agent_manager import load_all_agents, parse_frontmatter
from .utils.validation import validate_bash_command, truncate_output


async def test_bash_tool():
    """Test bash tool execution."""
    print("Testing Bash Tool...")
    
    # Test simple command
    result = await BashTool.execute("echo 'Hello World'")
    assert result["exit_code"] == 0
    assert "Hello World" in result["stdout"]
    print("✓ Basic command execution works")
    
    # Test banned command
    result = await BashTool.execute("rm -rf /tmp/test")
    assert result["exit_code"] != 0
    assert "not allowed" in result["stderr"]
    print("✓ Banned command validation works")
    
    # Test timeout
    result = await BashTool.execute("sleep 2", timeout=1)
    assert result["interrupted"] == True
    assert "timed out" in result["stderr"]
    print("✓ Timeout handling works")


def test_validation():
    """Test validation utilities."""
    print("\nTesting Validation...")
    
    # Test command validation
    cwd = os.getcwd()
    
    valid, msg = validate_bash_command("ls -la", cwd)
    assert valid == True
    print("✓ Valid command accepted")
    
    valid, msg = validate_bash_command("rm -rf /", cwd)
    assert valid == False
    assert "not allowed" in msg
    print("✓ Dangerous command rejected")
    
    # Test output truncation
    long_output = "\n".join([f"Line {i}" for i in range(2000)])
    truncated, total = truncate_output(long_output, max_lines=100)
    assert total == 2000
    assert "truncated" in truncated
    print("✓ Output truncation works")


def test_agent_manager():
    """Test agent manager."""
    print("\nTesting Agent Manager...")
    
    # Test frontmatter parsing
    content = """---
agent-type: test-agent
when-to-use: Test purposes
allowed-tools: bash, agent
---

This is the system prompt."""
    
    frontmatter, prompt = parse_frontmatter(content)
    assert frontmatter["agent-type"] == "test-agent"
    assert "system prompt" in prompt
    print("✓ Frontmatter parsing works")
    
    # Test loading agents
    agents = load_all_agents()
    assert len(agents) > 0
    assert any(a.agent_type == "general-purpose" for a in agents)
    print(f"✓ Loaded {len(agents)} agent(s)")
    
    # Check for example agent
    example_agent = [a for a in agents if a.agent_type == "code-analyzer"]
    if example_agent:
        print(f"✓ Found example agent: {example_agent[0].agent_type}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Claude Code Python - Basic Tests")
    print("=" * 60)
    
    try:
        await test_bash_tool()
        test_validation()
        test_agent_manager()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

