import argparse
<<<<<<< HEAD
=======
import json
>>>>>>> personal/main
import sys
from pathlib import Path

from codex_runner import CodexCLIClient, MockCodexClient
from final_score import calculate_final_score
from generation_quality_validator import validate_generation_quality
from model_blueprint_builder import build_model_blueprint
from model_intent_detector import detect_model_intent
from output_writer import (
    clean_known_outputs,
    ensure_output_dir,
    write_error,
    write_final_output,
    write_improvement_suggestions,
    write_generation_quality_report_markdown,
    write_json,
    write_text,
    write_validation_errors,
    write_validation_errors_markdown,
)
from prompt_writer import pretty_json, write_prompt
from response_parser import parse_json_response, validate_generation_response, validate_semantic_review
from rule_score import calculate_rule_based_score
from validator import validate_required_fields
from yaml_loader import load_yaml_file
<<<<<<< HEAD
from runtime_config import PROJECT_ROOT, resolve_output_dir


SEMANTIC_TEMPLATE = PROJECT_ROOT / "prompts" / "codex_semantic_review_prompt_template.md"
GENERATION_TEMPLATE = PROJECT_ROOT / "prompts" / "codex_generation_prompt_template.md"
=======


SEMANTIC_TEMPLATE = Path("prompts") / "codex_semantic_review_prompt_template.md"
GENERATION_TEMPLATE = Path("prompts") / "codex_generation_prompt_template.md"
>>>>>>> personal/main


def parse_args():
    parser = argparse.ArgumentParser(description="AI Data Model Accelerator MVP")
    parser.add_argument("--input", required=True, help="Path to business input YAML file.")
<<<<<<< HEAD
    parser.add_argument("--output-dir", help="Optional output directory. Default: output/<business_name_slug>.")
=======
    parser.add_argument("--output-dir", default="output", help="Directory for generated output files.")
>>>>>>> personal/main
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


def _write_quality_report(output_dir, quality_report):
    write_json(output_dir / "generation_quality_report.json", quality_report)
    write_generation_quality_report_markdown(output_dir, quality_report)


def main():
    args = parse_args()
<<<<<<< HEAD
    output_dir = Path(args.output_dir) if args.output_dir else Path("output")
=======
    output_dir = Path(args.output_dir)
    ensure_output_dir(output_dir)
    # Preferred MVP behavior: always clean known generated outputs before each run.
    clean_known_outputs(output_dir)
>>>>>>> personal/main

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
<<<<<<< HEAD
        output_dir = resolve_output_dir(args.input, data, args.output_dir)
        ensure_output_dir(output_dir)
        clean_known_outputs(output_dir)
=======
>>>>>>> personal/main
        validation_result = validate_required_fields(data)
        if not validation_result["is_valid"]:
            write_validation_errors(output_dir, validation_result)
            write_validation_errors_markdown(output_dir, validation_result)
<<<<<<< HEAD
            print(f"Validation failed. See {output_dir / 'validation_errors.md'} for details.", file=sys.stderr)
=======
            print("Validation failed. See output/validation_errors.json and output/validation_errors.md for details.", file=sys.stderr)
>>>>>>> personal/main
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
<<<<<<< HEAD
            print(f"Pipeline completed: input needs improvement. See {output_dir / 'improvement_suggestions.md'}.")
=======
            print("Pipeline completed: input needs improvement. See output/improvement_suggestions.md.")
>>>>>>> personal/main
            return 0

        model_intent = detect_model_intent(data)
        write_json(output_dir / "model_intent.json", model_intent)
        model_blueprint = build_model_blueprint(data, model_intent)
        write_json(output_dir / "model_blueprint.json", model_blueprint)

        generation_prompt = write_prompt(
            GENERATION_TEMPLATE,
            output_dir / "codex_generation_prompt.md",
            {
                "canonical_json": pretty_json(data),
                "rule_based_score": pretty_json(rule_score),
                "final_score": pretty_json(final_score),
                "model_intent": pretty_json(model_intent),
                "model_blueprint": pretty_json(model_blueprint),
            },
        )
        raw_generation = get_raw_generation_response(args, generation_prompt)
        write_text(output_dir / "codex_generation_response_raw.txt", raw_generation)
        generation_response = validate_generation_response(parse_json_response(raw_generation))
        write_json(output_dir / "codex_generation_response.json", generation_response)
        quality_report = validate_generation_quality(generation_response, model_intent, model_blueprint)
        _write_quality_report(output_dir, quality_report)
        if quality_report["status"] == "failed":
<<<<<<< HEAD
            print(f"Generation quality validation failed. See {output_dir / 'generation_quality_report.md'}.", file=sys.stderr)
            return 1
        write_final_output(output_dir, generation_response)
        print(f"Pipeline completed: final output generated at {output_dir / 'final_output.md'}.")
        return 0
    except Exception as exc:
        message = str(exc)
        ensure_output_dir(output_dir)
=======
            print("Generation quality validation failed. See output/generation_quality_report.md.", file=sys.stderr)
            return 1
        write_final_output(output_dir, generation_response)
        print("Pipeline completed: final output generated. See output/final_output.md.")
        return 0
    except Exception as exc:
        message = str(exc)
>>>>>>> personal/main
        write_error(output_dir, message)
        print(f"Error: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
