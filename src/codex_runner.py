import json
import shutil
import subprocess


class CodexRunnerError(Exception):
    """Raised when Codex CLI execution fails."""


def resolve_codex_executable():
    for candidate in ["codex", "codex.cmd", "codex.CMD"]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise CodexRunnerError("Codex CLI executable was not found in PATH. Try running codex --version in the same terminal.")


class CodexCLIClient:
    def run_prompt(self, prompt_text):
        executable = resolve_codex_executable()
        try:
            result = subprocess.run(
                [executable, "exec", "-"],
                input=prompt_text,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise CodexRunnerError("Codex CLI executable was not found in PATH. Try running codex --version in the same terminal.") from exc
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
        catalog = {
            "business_context": {
                "business_name": "Mock Business",
                "business_type": "Retail",
                "model_purpose": "Mock analytical model",
                "target_database": "PostgreSQL",
            },
            "table_column_rules": [
                {"table_name": "load_customer_raw", "column_name": "customer_id", "semantic_role": "primary_key", "data_type": "integer", "numeric_min": 1, "numeric_max": 1000, "allowed_values": [], "value_examples": [], "value_pattern": "", "date_rule": "", "boolean_rule": "", "calculation_rule": "", "relationship_rule": "", "nullable_rule": "not_null", "uniqueness_rule": "unique", "business_reason": "Mock raw customer identifier."},
                {"table_name": "stg_customer", "column_name": "customer_id", "semantic_role": "business_key", "data_type": "integer", "numeric_min": 1, "numeric_max": 1000, "allowed_values": [], "value_examples": [], "value_pattern": "", "date_rule": "", "boolean_rule": "", "calculation_rule": "", "relationship_rule": "", "nullable_rule": "not_null", "uniqueness_rule": "unique", "business_reason": "Mock staged customer identifier."},
                {"table_name": "dim_customer", "column_name": "customer_key", "semantic_role": "surrogate_key", "data_type": "integer", "numeric_min": 1, "numeric_max": 1000, "allowed_values": [], "value_examples": [], "value_pattern": "", "date_rule": "", "boolean_rule": "", "calculation_rule": "", "relationship_rule": "", "nullable_rule": "not_null", "uniqueness_rule": "unique", "business_reason": "Mock customer surrogate key."},
                {"table_name": "dim_customer", "column_name": "customer_id", "semantic_role": "business_key", "data_type": "integer", "numeric_min": 1, "numeric_max": 1000, "allowed_values": [], "value_examples": [], "value_pattern": "", "date_rule": "", "boolean_rule": "", "calculation_rule": "", "relationship_rule": "", "nullable_rule": "not_null", "uniqueness_rule": "", "business_reason": "Mock customer natural key."},
                {"table_name": "fact_sales", "column_name": "sales_key", "semantic_role": "surrogate_key", "data_type": "integer", "numeric_min": 1, "numeric_max": 1000, "allowed_values": [], "value_examples": [], "value_pattern": "", "date_rule": "", "boolean_rule": "", "calculation_rule": "", "relationship_rule": "", "nullable_rule": "not_null", "uniqueness_rule": "unique", "business_reason": "Mock fact surrogate key."},
                {"table_name": "fact_sales", "column_name": "customer_key", "semantic_role": "foreign_key", "data_type": "integer", "numeric_min": 1, "numeric_max": 1000, "allowed_values": [], "value_examples": [], "value_pattern": "", "date_rule": "", "boolean_rule": "", "calculation_rule": "", "relationship_rule": "References dim_customer.customer_key", "nullable_rule": "not_null", "uniqueness_rule": "", "business_reason": "Mock fact-to-customer relationship."},
                {"table_name": "fact_sales", "column_name": "order_total_amount", "semantic_role": "measure", "data_type": "numeric(10,2)", "numeric_min": 10, "numeric_max": 500, "allowed_values": [], "value_examples": [], "value_pattern": "", "date_rule": "", "boolean_rule": "", "calculation_rule": "", "relationship_rule": "", "nullable_rule": "not_null", "uniqueness_rule": "", "business_reason": "Mock bounded sales amount."},
            ],
            "business_rules": [],
            "generation_assumptions": ["Mock catalog for tests."],
        }
        final_output = (
            "# Business Input Summary\n\nMock generated output.\n\n"
            "# SQL DDL\n\n```sql\n"
            "CREATE TABLE load_customer_raw (customer_id integer PRIMARY KEY);\n"
            "CREATE TABLE stg_customer (customer_id integer PRIMARY KEY);\n"
            "CREATE TABLE dim_customer (customer_key integer PRIMARY KEY, customer_id integer);\n"
            "CREATE TABLE fact_sales (sales_key integer PRIMARY KEY, customer_key integer REFERENCES dim_customer(customer_key), order_total_amount numeric(10,2));\n"
            "```\n\n# Fact Grain\n\nfact_sales = one row per order item.\n\n"
            "# Synthetic Data Value Catalog\n\n"
            "BEGIN_SYNTHETIC_VALUE_CATALOG_JSON\n"
            f"{json.dumps(catalog, indent=2)}\n"
            "END_SYNTHETIC_VALUE_CATALOG_JSON\n\n"
            "# AI Additions / Assumptions\n\n"
            "| Added Item | Type | Reason | Mandatory / Optional |\n"
            "|---|---|---|---|\n"
            "| sample_assumption | assumption | Mock generation assumption for testing. | optional |"
        )
        response = {
            "status": "generated",
            "final_output_markdown": final_output,
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
