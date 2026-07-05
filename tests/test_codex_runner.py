import json

import pytest

from codex_runner import CodexRunnerError, MockCodexClient, resolve_codex_executable
from generation_quality_validator import validate_generation_quality


def test_mock_generation_contains_parseable_catalog_and_passes_quality_gate():
    raw = MockCodexClient(ai_score=100).run_generation("prompt")
    response = json.loads(raw)
    markdown = response["final_output_markdown"]
    assert "# Synthetic Data Value Catalog" in markdown
    assert "BEGIN_SYNTHETIC_VALUE_CATALOG_JSON" in markdown
    assert "END_SYNTHETIC_VALUE_CATALOG_JSON" in markdown
    result = validate_generation_quality(
        response,
        {"model_type": "analytical_data_warehouse", "required_layers": ["raw_load", "staging", "dimension", "fact"]},
        {"inferred_fact_tables": ["fact_sales"]},
    )
    assert result["status"] == "passed"


def test_resolve_codex_executable_uses_shutil_which(monkeypatch):
    calls = []

    def fake_which(candidate):
        calls.append(candidate)
        return "/usr/bin/codex.cmd" if candidate == "codex.cmd" else None

    monkeypatch.setattr("codex_runner.shutil.which", fake_which)
    assert resolve_codex_executable() == "/usr/bin/codex.cmd"
    assert calls == ["codex", "codex.cmd"]


def test_resolve_codex_executable_clear_error(monkeypatch):
    monkeypatch.setattr("codex_runner.shutil.which", lambda candidate: None)
    with pytest.raises(CodexRunnerError, match="Codex CLI executable was not found in PATH"):
        resolve_codex_executable()
