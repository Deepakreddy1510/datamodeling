import argparse
import json
import sys
from pathlib import Path

from codex_runner import CodexCLIClient, MockCodexClient
from final_score import calculate_final_score
from output_writer import (
    clean_known_outputs,
    ensure_output_dir,
    write_error,
    write_final_output,
    write_improvement_suggestions,
    write_json,
    write_text,
    write_validation_errors,
)
from prompt_writer import pretty_json, write_prompt
from response_parser import parse_json_response, validate_generation_response, validate_semantic_review
from rule_score import calculate_rule_based_score
from validator import validate_required_fields
from yaml_loader import load_yaml_file


SEMANTIC_TEMPLATE = Path("prompts") / "codex_semantic_review_prompt_template.md"
GENERATION_TEMPLATE = Path("prompts") / "codex_generation_prompt_template.md"


def parse_args():
    parser = argparse.ArgumentParser(description="AI Data Model Accelerator MVP")
    parser.add_argument("--input", required=True, help="Path to business input YAML file.")
    parser.add_argument("--output-dir", default="output", help="Directory for generated output files.")
    parser.add_argument("--provider", default="codex_cli", help="Only codex_cli is supported in this MVP.")
    parser.add_argument("--mock-codex", action="store_true", help="Use deterministic mock Codex responses.")
    parser.add_argument("--mock-ai-score", type=float, default=86, help="Mock semantic review score, default 86.")
    parser.add_argument("--clean-output", action="store_true", help="Clean known generated output files before running. Enabled by default.")
    return parser.parse_args()


def get_raw_semantic_response(args, prompt_text):
    if args.mock_codex:
        return MockCodexClient(args.mock_ai_score).run_semantic_review(prompt_text)
    return CodexCLIClient().run_prompt(prompt_text)


def get_raw_generation_response(args, prompt_text):
    if args.mock_codex:
        return MockCodexClient(args.mock_ai_score).run_generation(prompt_text)
    return CodexCLIClient().run_prompt(prompt_text)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    ensure_output_dir(output_dir)
    # Preferred MVP behavior: always clean known generated outputs before each run.
    clean_known_outputs(output_dir)

    if args.provider == "openai":
        message = "OpenAI provider is not implemented in this MVP. Use --provider codex_cli."
        print(message, file=sys.stderr)
        write_error(output_dir, message)
        return 1
    if args.provider != "codex_cli":
        message = f"Unsupported provider '{args.provider}'. Use --provider codex_cli."
        print(message, file=sys.stderr)
        write_error(output_dir, message)
        return 1

    try:
        data = load_yaml_file(args.input)
        validation_result = validate_required_fields(data)
        if not validation_result["is_valid"]:
            write_validation_errors(output_dir, validation_result)
            print("Validation failed. See output/validation_errors.json for details.", file=sys.stderr)
            return 1

        write_json(output_dir / "input.json", data)

        rule_score = calculate_rule_based_score(data)
        write_json(output_dir / "rule_based_score.json", rule_score)

        semantic_prompt = write_prompt(
            SEMANTIC_TEMPLATE,
            output_dir / "codex_semantic_review_prompt.md",
            {
                "canonical_json": pretty_json(data),
                "rule_based_score": pretty_json(rule_score),
            },
        )

        raw_semantic = get_raw_semantic_response(args, semantic_prompt)
        write_text(output_dir / "codex_semantic_review_response_raw.txt", raw_semantic)
        semantic_review = validate_semantic_review(parse_json_response(raw_semantic))
        write_json(output_dir / "codex_semantic_review_response.json", semantic_review)

        final_score = calculate_final_score(rule_score["rule_based_score"], semantic_review["ai_review_score"])
        write_json(output_dir / "final_readiness_score.json", final_score)

        if final_score["decision"] != "ready_for_generation":
            write_improvement_suggestions(output_dir, rule_score, semantic_review, final_score)
            print("Pipeline completed: input needs improvement. See output/improvement_suggestions.md.")
            return 0

        generation_prompt = write_prompt(
            GENERATION_TEMPLATE,
            output_dir / "codex_generation_prompt.md",
            {
                "canonical_json": pretty_json(data),
                "rule_based_score": pretty_json(rule_score),
                "final_score": pretty_json(final_score),
            },
        )
        raw_generation = get_raw_generation_response(args, generation_prompt)
        write_text(output_dir / "codex_generation_response_raw.txt", raw_generation)
        generation_response = validate_generation_response(parse_json_response(raw_generation))
        write_json(output_dir / "codex_generation_response.json", generation_response)
        write_final_output(output_dir, generation_response)
        print("Pipeline completed: final output generated. See output/final_output.md.")
        return 0
    except Exception as exc:
        message = str(exc)
        write_error(output_dir, message)
        print(f"Error: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
