"""CLI entry point for the agent."""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console

from .core import Agent

console = Console()


def main() -> None:
    """Run the agent with a goal from command line args."""
    if len(sys.argv) < 2:
        console.print("[red]Usage: agent <goal>[/]")
        console.print('  Example: agent "Create a Python fibonacci module with tests"')
        sys.exit(1)

    goal = " ".join(sys.argv[1:])
    agent = Agent()

    # Register default tools
    try:
        from tools.filesystem_tool import FilesystemTool
        from tools.code_executor_tool import CodeExecutorTool

        agent.register_tool("filesystem", FilesystemTool())
        agent.register_tool("code_executor", CodeExecutorTool())
    except ImportError:
        console.print("[yellow]Warning: Some tools not available[/]")

    asyncio.run(agent.run(goal))


if __name__ == "__main__":
    main()
