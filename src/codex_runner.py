import json
import subprocess


class CodexRunnerError(Exception):
    """Raised when Codex CLI execution fails."""


class CodexCLIClient:
    def run_prompt(self, prompt_text):
        try:
            result = subprocess.run(
                ["codex", "exec", "-"],
                input=prompt_text,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise CodexRunnerError("Codex CLI must be installed and authenticated before running this pipeline.") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            message = "Codex CLI returned a non-zero exit code."
            if stderr:
                message += f" stderr: {stderr}"
            raise CodexRunnerError(message) from exc

        stdout = result.stdout.strip()
        if not stdout:
            raise CodexRunnerError("Codex CLI returned empty stdout.")
        return stdout


class MockCodexClient:
    def __init__(self, ai_score=86):
        self.ai_score = ai_score

    def run_semantic_review(self, prompt_text):
        response = {
            "ai_review_score": self.ai_score,
            "readiness_level": "Ready" if self.ai_score >= 90 else "Medium",
            "semantic_status": "ready_for_generation" if self.ai_score >= 90 else "needs_improvement",
            "missing_items": [
                {
                    "section": "entity_attributes",
                    "issue": "Some entity attributes are incomplete or missing.",
                    "priority": "High",
                    "recommendation": "Add attributes for key entities before generation.",
                }
            ],
            "relationship_review": {
                "are_relationships_clear": False,
                "many_to_many_issues": [
                    "Review possible many-to-many relationships and resolve them with bridge entities."
                ],
                "missing_relationships": [],
            },
            "entity_review": {
                "are_entities_enough": False,
                "missing_entities": ["Bridge/intersection entities may be required."],
                "weak_entities": [],
            },
            "reporting_review": {
                "are_reporting_requirements_supported": False,
                "missing_reporting_details": ["Reporting grain and metrics may be incomplete."],
            },
            "business_rule_review": {
                "are_business_rules_clear": False,
                "missing_business_rules": ["Add key business rules for modeling decisions."],
            },
            "platform_review": {"is_platform_clear": True, "missing_platform_details": []},
            "suggestions": [
                "Add missing entity attributes.",
                "Resolve many-to-many relationships.",
                "Clarify reporting grain and metrics.",
            ],
            "assumptions_needed": [
                "Assumptions may be needed for missing attributes and relationships."
            ],
        }
        return json.dumps(response, indent=2)

    def run_generation(self, prompt_text):
        response = {
            "status": "generated",
            "final_output_markdown": "# Business Input Summary\n\nMock generated output.\n\n# SQL DDL\n\n```sql\nCREATE TABLE load_customer_raw (customer_id integer PRIMARY KEY);\nCREATE TABLE stg_customer (customer_id integer PRIMARY KEY);\nCREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id integer);\nCREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key), order_total_amount numeric(10,2));\n```\n\n# Fact Grain\n\nfact_sales = one row per order item.\n\n# AI Additions / Assumptions\n\n| Added Item | Type | Reason | Mandatory / Optional |\n|---|---|---|---|\n| sample_assumption | assumption | Mock generation assumption for testing. | optional |",
            "ai_additions_and_assumptions": [
                {
                    "added_item": "sample_assumption",
                    "item_type": "assumption",
                    "reason": "Mock generation assumption for testing.",
                    "mandatory_or_optional": "optional",
                }
            ],
        }
        return json.dumps(response, indent=2)
