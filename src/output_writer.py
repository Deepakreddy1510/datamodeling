import json
from pathlib import Path

KNOWN_GENERATED_FILES = [
    "input.json",
    "rule_based_score.json",
    "codex_semantic_review_prompt.md",
    "codex_semantic_review_response_raw.txt",
    "codex_semantic_review_response.json",
    "final_readiness_score.json",
    "model_intent.json",
    "model_blueprint.json",
    "improvement_suggestions.md",
    "codex_generation_prompt.md",
    "codex_generation_response_raw.txt",
    "codex_generation_response.json",
    "final_output.md",
    "generation_quality_report.json",
    "generation_quality_report.md",
    "catalog_repair_prompt.md",
    "catalog_repair_response_raw.txt",
    "catalog_repair_response.json",
    "validation_errors.json",
    "validation_errors.md",
    "error.json",
]

AI_ADDITIONS_HEADING = "# AI Additions / Assumptions"


def ensure_output_dir(output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)


def clean_known_outputs(output_dir):
    ensure_output_dir(output_dir)
    for filename in KNOWN_GENERATED_FILES:
        path = Path(output_dir) / filename
        if path.exists() and path.is_file():
            path.unlink()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path, text):
    Path(path).write_text(text, encoding="utf-8")


def write_validation_errors(output_dir, validation_result):
    write_json(Path(output_dir) / "validation_errors.json", {
        "status": "validation_failed",
        "errors": validation_result["errors"],
    })


def write_validation_errors_markdown(output_dir, validation_result):
    lines = [
        "# Validation Errors",
        "",
        "The input YAML is incomplete. Please fix the following fields before running the accelerator again.",
        "",
        "| Field | Issue |",
        "|---|---|",
    ]
    for error in validation_result["errors"]:
        lines.append(f"| {error.get('field', '')} | {error.get('message', '')} |")
    lines.extend([
        "",
        "## Next Step",
        "",
        "Update the input YAML file and run:",
        "",
        "```bash",
        "python src/main.py --input input/business_input.yaml",
        "```",
        "",
    ])
    write_text(Path(output_dir) / "validation_errors.md", "\n".join(lines))


def write_error(output_dir, message):
    write_json(Path(output_dir) / "error.json", {"status": "error", "message": message})


def write_improvement_suggestions(output_dir, rule_score, semantic_review, final_score):
    lines = [
        "# Input Readiness Report",
        "",
        "## Scores",
        "",
        "| Score Type | Value |",
        "|---|---:|",
        f"| Rule-Based Score | {final_score['rule_based_score']} |",
        f"| AI Semantic Review Score | {final_score['ai_review_score']} |",
        f"| Final Score | {final_score['final_score']} |",
        "",
        "Formula:",
        "",
        "```text",
        final_score["formula"],
        "```",
        "",
        "## Decision",
        "",
        "Needs improvement.",
        "",
        "## Rule-Based Missing Sections",
        "",
    ]
    missing_sections = rule_score.get("missing_sections", [])
    lines.extend([f"- {section}" for section in missing_sections] or ["None"])
    lines.extend([
        "",
        "## Semantic Missing Items",
        "",
        "| Section | Issue | Priority | Recommendation |",
        "| ------- | ----- | -------- | -------------- |",
    ])
    missing_items = semantic_review.get("missing_items", [])
    if missing_items:
        for item in missing_items:
            lines.append(
                f"| {item.get('section', '')} | {item.get('issue', '')} | {item.get('priority', '')} | {item.get('recommendation', '')} |"
            )
    else:
        lines.append("| None | None | None | None |")

    lines.extend(["", "## Suggestions", ""])
    lines.extend([f"- {item}" for item in semantic_review.get("suggestions", [])] or ["None"])
    lines.extend(["", "## Assumptions Needed", ""])
    lines.extend([f"- {item}" for item in semantic_review.get("assumptions_needed", [])] or ["None"])
    lines.append("")
    write_text(Path(output_dir) / "improvement_suggestions.md", "\n".join(lines))



def write_generation_quality_report_markdown(output_dir, quality_report):
    lines = [
        "# Generation Quality Report",
        "",
        f"Status: **{quality_report.get('status', 'unknown')}**",
        "",
        "## Errors",
        "",
    ]
    lines.extend([f"- {error}" for error in quality_report.get("errors", [])] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {warning}" for warning in quality_report.get("warnings", [])] or ["- None"])
    repair = quality_report.get("repair", {})
    if repair:
        lines.extend([
            "", "## Catalog Repair", "",
            f"- Catalog repair attempted: {repair.get('catalog_repair_attempted', False)}",
            f"- Repair attempt count: {repair.get('repair_attempt_count', 0)}",
            f"- Catalog repair status: {repair.get('catalog_repair_status', 'not_attempted')}",
            f"- Original generation status: {repair.get('original_generation_status')}",
            f"- Repaired generation status: {repair.get('repaired_generation_status')}",
            f"- Catalog coverage before repair: {repair.get('catalog_coverage_before_repair')}",
            f"- Catalog coverage after repair: {repair.get('catalog_coverage_after_repair')}",
            f"- Final output written: {repair.get('final_output_written', False)}",
            "", "### Missing Rules Before Repair", "",
        ])
        lines.extend([f"- {item}" for item in repair.get("missing_rules_before_repair", [])] or ["- None"])
        lines.extend(["", "### Missing Rules After Repair", ""])
        lines.extend([f"- {item}" for item in repair.get("missing_rules_after_repair", [])] or ["- None"])
    checks = quality_report.get("checks", {})
    lines.extend([
        "", "## Summary", "",
        f"- Model intent: `{checks.get('model_type', 'unknown')}`",
        f"- Required layers: `{checks.get('required_layers', [])}`",
        f"- Catalog parsed: {checks.get('catalog_parsed', False)}",
        f"- Catalog rule count: {checks.get('catalog_rule_count', 0)}",
        f"- Catalog coverage percentage: {checks.get('catalog_coverage_percentage', 0)}",
        "", "## Missing Important Catalog Rules", "",
    ])
    lines.extend([f"- {item}" for item in checks.get("missing_catalog_rules", [])] or ["- None"])
    lines.extend(["", "## Checks", "", "| Check | Passed / Value |", "|---|---:|"])
    for name, value in checks.items():
        lines.append(f"| {name} | {value} |")
    lines.append("")
    write_text(Path(output_dir) / "generation_quality_report.md", "\n".join(lines))

def ensure_ai_additions_section(markdown_text):
    text = markdown_text.rstrip()
    if AI_ADDITIONS_HEADING in text:
        return text + "\n"
    return text + "\n\n# AI Additions / Assumptions\n\nNo AI additions section was returned by Codex.\n"


def write_final_output(output_dir, generation_response):
    final_markdown = ensure_ai_additions_section(generation_response["final_output_markdown"])
    write_text(Path(output_dir) / "final_output.md", final_markdown)
