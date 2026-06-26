import json
from pathlib import Path

KNOWN_GENERATED_FILES = [
    "input.json",
    "rule_based_score.json",
    "codex_semantic_review_prompt.md",
    "codex_semantic_review_response_raw.txt",
    "codex_semantic_review_response.json",
    "final_readiness_score.json",
    "improvement_suggestions.md",
    "codex_generation_prompt.md",
    "codex_generation_response_raw.txt",
    "codex_generation_response.json",
    "final_output.md",
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


def ensure_ai_additions_section(markdown_text):
    text = markdown_text.rstrip()
    if AI_ADDITIONS_HEADING in text:
        return text + "\n"
    return text + "\n\n# AI Additions / Assumptions\n\nNo AI additions section was returned by Codex.\n"


def write_final_output(output_dir, generation_response):
    final_markdown = ensure_ai_additions_section(generation_response["final_output_markdown"])
    write_text(Path(output_dir) / "final_output.md", final_markdown)
