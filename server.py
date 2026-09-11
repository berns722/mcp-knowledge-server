"""MCP server over a versioned knowledge base.

Exposes a small, version-controlled knowledge base — identity, a current-state
snapshot, and an append-only event log — as tools any MCP-compatible agent can
call at runtime:

- read tools that return live state derived from the underlying files, and
- deterministic verification tools that check the data against its JSON Schema
  and its own cross-references.

This is a public, generalized extract of tooling I built for a private
knowledge-management project. All data here is synthetic sample data.

Run:
    pip install -r requirements.txt
    python server.py          # runs the MCP server over stdio
    # or: mcp dev server.py   # opens the MCP Inspector to click the tools
"""

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from mcp.server.mcpserver import MCPServer

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SCHEMAS = ROOT / "schemas"

# Traceable ID prefixes used across the knowledge base.
_ID = re.compile(r"(?:EVT|DOC|CMP)-\d{4}")
_FILE_ID = re.compile(r"^(?:EVT|DOC|CMP)-\d{4}")
_TEXT_EXT = {".md", ".yaml", ".yml"}

mcp = MCPServer("knowledge-base")


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _text_files():
    """Iterate the repo's versionable text files (md/yaml), skipping `.git`."""
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.suffix.lower() in _TEXT_EXT:
            yield path


def _known_ids() -> set[str]:
    """IDs that exist, derived from the log/document file names."""
    known = set()
    for path in _text_files():
        match = _FILE_ID.match(path.name)
        if match:
            known.add(match.group(0))
    return known


@mcp.tool()
def get_state() -> dict:
    """Live summary of the asset, merged from data/identity.yaml and
    data/state.yaml: identity, usage vs. target, system health, and open issues."""
    identity = _load_yaml(DATA / "identity.yaml")["asset"]
    state = _load_yaml(DATA / "state.yaml")
    target = identity["registry"]["target_hours"]
    current = state["current_hours"]
    return {
        "asset": identity["name"],
        "serial": identity["serial"],
        "current_hours": current,
        "target_hours": target,
        "hours_to_target": target - current,
        "updated": state.get("updated"),
        "last_event": state.get("last_event"),
        "systems": state.get("systems", {}),
        "open_issues": state.get("open_issues", []),
    }


@mcp.tool()
def next_action() -> dict:
    """The next recommended action and the open pending items, read live from
    data/state.yaml."""
    state = _load_yaml(DATA / "state.yaml")
    nxt = state.get("next_action", {})
    return {
        "objective": nxt.get("objective"),
        "safety": nxt.get("safety"),
        "pending": state.get("pending", []),
    }


@mcp.tool()
def validate_schemas() -> dict:
    """Validate each data file against its JSON Schema. A schema
    schemas/<x>.schema.json validates data/<x>.yaml. Deterministic: same input,
    same verdict every time."""
    detail = []
    for schema_path in sorted(SCHEMAS.glob("*.schema.json")):
        name = schema_path.name.removesuffix(".schema.json")
        data_path = DATA / f"{name}.yaml"
        if not data_path.exists():
            detail.append(
                {
                    "schema": schema_path.name,
                    "file": None,
                    "valid": False,
                    "errors": [f"missing {data_path.relative_to(ROOT).as_posix()}"],
                }
            )
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        # JSON Schema validates JSON types; YAML parses dates to date objects, so
        # normalize to JSON types (ISO dates become strings) before validating.
        data = json.loads(json.dumps(_load_yaml(data_path), default=str))
        validator = Draft202012Validator(schema)
        errors = [
            f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}"
            for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        ]
        detail.append(
            {
                "schema": schema_path.name,
                "file": data_path.relative_to(ROOT).as_posix(),
                "valid": not errors,
                "errors": errors,
            }
        )
    return {"valid": all(d["valid"] for d in detail), "detail": detail}


@mcp.tool()
def check_links() -> dict:
    """Referential-integrity check: every ID referenced anywhere (state refs,
    front-matter links, prose) must point to a document that exists."""
    known = _known_ids()
    broken = []
    for path in _text_files():
        text = path.read_text(encoding="utf-8")
        for cited in set(_ID.findall(text)):
            if cited not in known:
                broken.append({"id": cited, "cited_in": path.relative_to(ROOT).as_posix()})
    broken.sort(key=lambda b: (b["cited_in"], b["id"]))
    return {"intact": not broken, "broken_links": broken}


if __name__ == "__main__":
    mcp.run(transport="stdio")
