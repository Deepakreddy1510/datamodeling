import json
import re


class ResponseParserError(Exception):
    """Raised when Codex output is not valid expected JSON."""


def strip_markdown_code_fence(raw_text):
    text = raw_text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def parse_json_response(raw_text):
    cleaned = strip_markdown_code_fence(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ResponseParserError(f"Invalid Codex JSON response: {exc}") from exc


def require_fields(data, fields, response_name):
    missing = [field for field in fields if field not in data]
    if missing:
        raise ResponseParserError(f"{response_name} is missing required field(s): {', '.join(missing)}")


def validate_semantic_review(data):
    require_fields(
        data,
        [
            "ai_review_score",
            "readiness_level",
            "semantic_status",
            "missing_items",
            "relationship_review",
            "entity_review",
            "reporting_review",
            "business_rule_review",
            "platform_review",
            "suggestions",
            "assumptions_needed",
        ],
        "Semantic review response",
    )
    score = data["ai_review_score"]
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ResponseParserError("ai_review_score must be numeric.")
    if score < 0 or score > 100:
        raise ResponseParserError("ai_review_score must be between 0 and 100.")
    for field in ["missing_items", "suggestions", "assumptions_needed"]:
        if not isinstance(data[field], list):
            raise ResponseParserError(f"{field} must be a list.")
    return data


def validate_generation_response(data):
    require_fields(data, ["status", "final_output_markdown", "ai_additions_and_assumptions"], "Generation response")
    if not isinstance(data["final_output_markdown"], str) or not data["final_output_markdown"].strip():
        raise ResponseParserError("final_output_markdown must be a non-empty string.")
    if not isinstance(data["ai_additions_and_assumptions"], list):
        raise ResponseParserError("ai_additions_and_assumptions must be a list.")
    return data
