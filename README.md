# 🤖 Rise of AI Agents

> Production-grade autonomous AI agent framework with MCP tool integration.  
> Built for the [LabLab Rise of AI Agents Hackathon](https://lablab.ai/ai-hackathons) — $50K prize pool.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   USER / CALLER                     │
│              (CLI / API / Demo Script)              │
└──────────────────────┬──────────────────────────────┘
                       │ goal (natural language)
                       ▼
┌─────────────────────────────────────────────────────┐
│                  AGENT CORE                         │
│  ┌───────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Planner  │→ │ Executor │→ │    Verifier      │ │
│  │ (decompose│  │ (run tool│  │ (check output,   │ │
│  │  into     │  │  calls)  │  │  retry on fail)  │ │
│  │  steps)   │  │          │  │                  │ │
│  └───────────┘  └──────────┘  └──────────────────┘ │
│         ▲              │               │            │
│         └──────────────┴───────────────┘            │
│                   feedback loop                     │
└──────────────────────┬──────────────────────────────┘
                       │ tool calls (MCP protocol)
                       ▼
┌─────────────────────────────────────────────────────┐
│               MCP TOOL LAYER                        │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐  │
│  │  GitHub   │ │Filesystem│ │  Web   │ │  Code   │  │
│  │  Tool     │ │  Tool    │ │ Search │ │Executor │  │
│  └──────────┘ └──────────┘ └────────┘ └─────────┘  │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│            SAFETY & OBSERVABILITY                   │
│  ┌──────────────┐  ┌───────────────────────────┐    │
│  │  Guardrails  │  │      Audit Trail          │    │
│  │ (approve /   │  │ (every action logged with  │    │
│  │  deny /      │  │  timestamp, input, output, │    │
│  │  escalate)   │  │  decision rationale)       │    │
│  └──────────────┘  └───────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Features

- **Autonomous Task Execution** — Give the agent a high-level goal; it decomposes, plans, executes, and verifies
- **MCP Protocol Integration** — Standardized tool interface following the Model Context Protocol
- **4 Built-in Tools** — GitHub, Filesystem, Web Search, Code Executor
- **Safety Guardrails** — Sensitive action detection, human-in-the-loop approval, configurable policies
- **Full Audit Trail** — Every action logged with timestamps, inputs, outputs, and rationale
- **Retry & Error Handling** — Automatic retry with exponential backoff, graceful degradation
- **Async-First** — Built on asyncio for concurrent tool execution

## Quick Start

```bash
# Clone
git clone https://github.com/mgnlia/rise-of-ai-agents.git
cd rise-of-ai-agents

# Install with uv
uv sync

# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run the demo
uv run python -m demo.autonomous_task

# Or use the CLI
uv run agent "Create a Python fibonacci module with tests"
```

## Project Structure

```
rise-of-ai-agents/
├── src/
│   └── agent/
│       ├── __init__.py
│       ├── __main__.py          # CLI entry point
│       ├── core.py              # Agent loop: plan → execute → verify
│       ├── planner.py           # Task decomposition via LLM
│       ├── executor.py          # Tool dispatch and execution
│       ├── verifier.py          # Output verification
│       └── models.py            # Pydantic data models
├── src/
│   └── tools/
│       ├── __init__.py
│       ├── base.py              # MCP tool base class
│       ├── github_tool.py       # GitHub API integration
│       ├── filesystem_tool.py   # Sandboxed file operations
│       ├── web_search_tool.py   # Web search via API
│       └── code_executor_tool.py # Sandboxed Python execution
├── src/
│   └── safety/
│       ├── __init__.py
│       ├── guardrails.py        # Action approval policies
│       └── audit.py             # Audit trail logger
├── demo/
│   └── autonomous_task.py       # End-to-end demo script
├── tests/
│   ├── test_core.py
│   ├── test_tools.py
│   └── test_safety.py
├── pyproject.toml
└── README.md
```

## How It Works

### 1. Planning Phase
The agent receives a high-level goal and uses an LLM to decompose it into discrete, ordered steps. Each step specifies which tool to use and what parameters to pass.

### 2. Execution Phase
Steps are executed sequentially (or concurrently where safe). Each tool call follows the MCP protocol — standardized JSON-RPC with typed inputs and outputs.

### 3. Verification Phase
After each step, the verifier checks whether the output meets expectations. On failure, it can retry the step, replan, or escalate to a human.

### 4. Safety Layer
Every action passes through guardrails before execution. Destructive operations (file deletion, repo creation) require explicit approval. The full audit trail is persisted for post-hoc review.

## Tool Connectors (MCP Protocol)

Each tool implements the `MCPTool` interface:

```python
class MCPTool(ABC):
    name: str
    description: str
    input_schema: dict      # JSON Schema for parameters
    
    async def execute(self, params: dict) -> ToolResult:
        """Execute the tool and return structured output."""
        ...
```

| Tool | Description | Sensitive Actions |
|------|-------------|-------------------|
| `github` | Create repos, issues, read/write files | repo creation, file writes |
| `filesystem` | Read/write/list files in sandbox | writes, deletes |
| `web_search` | Search the web, return structured results | none |
| `code_executor` | Run Python in sandboxed subprocess | all executions |

## Safety Model

```
Action Request → Guardrails Check → Approved? → Execute
                                  → Denied?   → Skip + Log
                                  → Escalate? → Human Approval → Execute/Deny
```

Guardrails are configurable via policy:
- `auto_approve`: Low-risk read operations
- `log_and_approve`: Medium-risk operations (logged, auto-approved)
- `require_approval`: High-risk operations (human must confirm)
- `deny`: Blocked operations (e.g., network access outside allowlist)

## License

MIT
