from codex_runner import MockCodexClient, resolve_codex_executable, CodexRunnerError
from generation_quality_validator import validate_generation_quality


def test_mock_generation_contains_data_engineering_ddl_and_passes_quality_gate():
    response = MockCodexClient(95).run_generation("prompt")
    markdown = __import__("json").loads(response)["final_output_markdown"]
    assert "CREATE TABLE load_" in markdown
    assert "CREATE TABLE stg_" in markdown
    assert "CREATE TABLE dim_" in markdown
    assert "CREATE TABLE fact_" in markdown
    assert "CREATE VIEW" in markdown
    result = validate_generation_quality(
        {"final_output_markdown": markdown},
        {"model_type": "analytical_data_warehouse", "required_layers": ["raw_load", "staging", "dimension", "fact", "reporting"]},
        {"inferred_fact_tables": ["fact_sales"]},
    )
    assert result["status"] in {"passed", "passed_with_warnings"}


def test_resolve_codex_executable_raises_when_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda candidate: None)
    try:
        resolve_codex_executable()
    except CodexRunnerError as exc:
        assert "Codex CLI executable" in str(exc)
    else:
        raise AssertionError("Expected CodexRunnerError")


def test_resolve_codex_executable_tries_windows_cmd(monkeypatch):
    seen = []
    def fake_which(candidate):
        seen.append(candidate)
        return "C:/tools/codex.cmd" if candidate == "codex.cmd" else None
    monkeypatch.setattr("shutil.which", fake_which)
    assert resolve_codex_executable() == "C:/tools/codex.cmd"
    assert seen[:2] == ["codex", "codex.cmd"]
