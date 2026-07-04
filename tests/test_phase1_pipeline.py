import sys
from pathlib import Path

import main as phase1_main
from output_writer import KNOWN_GENERATED_FILES, clean_known_outputs, write_text


def test_output_cleanup_includes_new_phase1_files(tmp_path):
    for filename in ["model_intent.json", "model_blueprint.json", "generation_quality_report.json", "generation_quality_report.md"]:
        write_text(tmp_path / filename, "stale")
    clean_known_outputs(tmp_path)
    for filename in ["model_intent.json", "model_blueprint.json", "generation_quality_report.json", "generation_quality_report.md"]:
        assert filename in KNOWN_GENERATED_FILES
        assert not (tmp_path / filename).exists()


def test_existing_mock_codex_flow_still_writes_final_output(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "main.py",
        "--input", "input/business_input_sample.yaml",
        "--output-dir", str(output_dir),
        "--mock-codex",
        "--mock-ai-score", "100",
    ])
    assert phase1_main.main() == 0
    assert (output_dir / "model_intent.json").exists()
    assert (output_dir / "model_blueprint.json").exists()
    assert (output_dir / "generation_quality_report.json").exists()
    assert (output_dir / "final_output.md").exists()


def test_validation_errors_still_work(tmp_path, monkeypatch):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("business_name: Only Name\n", encoding="utf-8")
    output_dir = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["main.py", "--input", str(bad_yaml), "--output-dir", str(output_dir), "--mock-codex"])
    assert phase1_main.main() == 1
    assert (output_dir / "validation_errors.json").exists()
