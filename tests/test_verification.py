"""Deterministic evaluation harness for the verification tools.

The same pattern used to build reinforcement-learning environments for coding
agents: seed a known broken state, define a golden reference solution, and use a
deterministic verifier to confirm the tools catch the fault and clear it only
once the state is repaired.

Tests never touch the shipped sample data: they build a minimal knowledge base in
a temp directory and point the server at it. The only shipped artifact under test
is the JSON Schema.
"""

import importlib.util
import shutil
from pathlib import Path

import pytest

_SERVER = Path(__file__).resolve().parents[1] / "server.py"
_REPO = Path(__file__).resolve().parents[1]

IDENTITY_OK = """\
asset:
  name: Demo Compressor Unit
  category: equipment
  serial: SAMPLE-0001
  commissioned: 2024-01-15
  registry:
    initial_hours: 12000
    target_hours: 100000
"""

STATE_OK = """\
updated: 2026-02-01
current_hours: 41230
last_event: EVT-0001
systems:
  cooling: ok
open_issues:
  - id: R-001
    desc: "sample issue"
    severity: medium
    refs: [EVT-0001]
pending:
  - "sample pending item"
next_action:
  objective: "Sample next action"
  safety: "Sample safety note"
"""

EVT_0001 = "---\nid: EVT-0001\ntype: event\nrefs: []\n---\n# EVT-0001\n"


def _load_server():
    spec = importlib.util.spec_from_file_location("server", _SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A minimal, healthy knowledge base in a temp dir, with the server pointed at it."""
    (tmp_path / "data" / "log").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()

    shutil.copy(
        _REPO / "schemas" / "identity.schema.json",
        tmp_path / "schemas" / "identity.schema.json",
    )
    (tmp_path / "data" / "identity.yaml").write_text(IDENTITY_OK, encoding="utf-8")
    (tmp_path / "data" / "state.yaml").write_text(STATE_OK, encoding="utf-8")
    (tmp_path / "data" / "log" / "EVT-0001-sample.md").write_text(EVT_0001, encoding="utf-8")

    server = _load_server()
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "DATA", tmp_path / "data")
    monkeypatch.setattr(server, "SCHEMAS", tmp_path / "schemas")
    return server, tmp_path


def test_read_tools_return_live_state(env):
    server, _ = env
    state = server.get_state()
    assert state["current_hours"] == 41230
    assert state["hours_to_target"] == 100000 - 41230  # computed, not stored
    assert server.next_action()["objective"] == "Sample next action"


def test_healthy_state_passes(env):
    server, _ = env
    assert server.validate_schemas()["valid"] is True
    assert server.check_links()["intact"] is True


def test_detects_invalid_schema(env):
    server, root = env
    (root / "data" / "identity.yaml").write_text(
        IDENTITY_OK.replace("category: equipment", "category: spaceship"), encoding="utf-8"
    )
    result = server.validate_schemas()
    assert result["valid"] is False
    assert any("category" in err for d in result["detail"] for err in d["errors"])


def test_detects_broken_link(env):
    server, root = env
    (root / "data" / "log" / "DOC-0002-x.md").write_text(
        "---\nid: DOC-0002\nrefs: [EVT-9999]\n---\n", encoding="utf-8"
    )
    result = server.check_links()
    assert result["intact"] is False
    assert any(b["id"] == "EVT-9999" for b in result["broken_links"])


def test_golden_solution_repairs_everything(env):
    server, root = env
    identity = root / "data" / "identity.yaml"
    broken_doc = root / "data" / "log" / "DOC-0002-x.md"

    # 1) Seed the broken state.
    identity.write_text(
        IDENTITY_OK.replace("category: equipment", "category: spaceship"), encoding="utf-8"
    )
    broken_doc.write_text("---\nid: DOC-0002\nrefs: [EVT-9999]\n---\n", encoding="utf-8")
    assert server.validate_schemas()["valid"] is False
    assert server.check_links()["intact"] is False

    # 2) Apply the golden solution: fix the value and create the missing document.
    identity.write_text(IDENTITY_OK, encoding="utf-8")
    (root / "data" / "log" / "EVT-9999-created.md").write_text(
        "---\nid: EVT-9999\n---\n", encoding="utf-8"
    )

    # 3) The deterministic verifier confirms it is healthy again.
    assert server.validate_schemas()["valid"] is True
    assert server.check_links()["intact"] is True
