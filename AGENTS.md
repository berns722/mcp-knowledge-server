# AGENTS.md — mcp-knowledge-server

An MCP server (Python, official `mcp` SDK / `MCPServer`) that exposes a version-controlled
knowledge base as agent-callable tools — two read (`get_state`, `next_action`) and two
deterministic verify (`validate_schemas`, `check_links`) — plus a pytest evaluation harness
and GitHub Actions CI. Public portfolio piece; a generalized, synthetic-data extract of tooling
built for a private knowledge-management project.

Part of the **ml-lab** system; follows the lab-wide mandate (human review gate, integrity,
lean/anti-sprawl, no AI attribution in commit messages), restated below so this repo stands alone.

## Working here
- **Run:** `pip install -r requirements.txt` → `python server.py` (stdio MCP server) or
  `mcp dev server.py` (MCP Inspector).
- **Test:** `pytest -v` (the eval harness: seed a broken state → golden fix → deterministic verify).
- **Conventions:** Python; MCP SDK v2 (`from mcp.server.mcpserver import MCPServer`); English.
  All data under `data/` is synthetic sample data.
- **Structure:** `server.py` · `data/` · `schemas/` · `tests/test_verification.py` · `.github/workflows/ci.yml`.

## Core mandate (from the lab)
- Propose changes as reviewable diffs; the human decides. Never fabricate; flag uncertainty.
- Lean over clever; edit over create; match existing style.
- Commit messages carry no AI/agent attribution.

## Session close
Before ending a session, update **STATUS.md**: what changed + the suggested next action.
