# mcp-knowledge-server

An **MCP server** that exposes a small, version-controlled knowledge base as tools
any MCP-compatible agent (Claude Desktop, Claude Code, another agent) can call at
runtime — plus a **deterministic evaluation harness** that verifies those tools.

It demonstrates the pattern behind agentic tooling: an agent shouldn't re-read and
re-reason over raw files every time; it should call **self-describing tools** that
return live state or run checks, through a standard protocol, with results that are
reproducible and verifiable.

> This is a public, generalized extract of tooling I built for a private
> knowledge-management project. All data in `data/` is synthetic sample data.

## The knowledge base

A tiny, git-tracked system with the shape real ones have:

- `data/identity.yaml` — near-immutable identity of an asset (validated by a JSON Schema).
- `data/state.yaml` — the current-state snapshot, referencing the log by ID.
- `data/log/` — an append-only event log; each entry has a stable ID (`EVT-####`).

## The tools

| Tool | Kind | What it does |
|---|---|---|
| `get_state` | read | Merges identity + state into one live summary (and computes usage-to-target). |
| `next_action` | read | Returns the next recommended action and open pending items. |
| `validate_schemas` | verify | Validates each data file against its JSON Schema; returns the exact failing fields. |
| `check_links` | verify | Confirms every referenced ID (`refs:`, front-matter, prose) points to a document that exists. |

The two `verify` tools are **deterministic**: same input, same verdict, every time —
no model in the loop. That is what makes them usable as a fair, automatable check.

## The evaluation harness

`tests/test_verification.py` follows the pattern used to build reinforcement-learning
environments for coding agents:

1. **Seed** a known broken state (an invalid field, a dangling reference).
2. Assert the tools **catch** it.
3. Apply the **golden reference solution** (fix the value, create the missing document).
4. A **deterministic verifier** confirms the tools report healthy again.

It runs on every push via GitHub Actions (`.github/workflows/ci.yml`).

## Run it

```bash
pip install -r requirements.txt

python server.py        # run the MCP server over stdio
mcp dev server.py       # or open the MCP Inspector to click each tool
pytest -v               # run the evaluation harness
```

To use it from Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "knowledge-base": { "command": "python", "args": ["/absolute/path/to/server.py"] }
  }
}
```

## Stack

Python · official MCP SDK (`mcp`, `MCPServer`) · PyYAML · jsonschema · pytest · GitHub Actions.
