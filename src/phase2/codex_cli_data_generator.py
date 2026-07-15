from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess

from codex_runner import CodexRunnerError, resolve_codex_executable
from runtime_config import PROJECT_ROOT

from .synthetic_data_generator import finalize_generated_value, table_generation_order
from .warehouse_generation_profile import build_warehouse_generation_profile


class CodexCliGenerationError(Exception):
    pass


SECRET_KEY_RE = re.compile(r"password|secret|credential|token|host|user|schema", re.IGNORECASE)
FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _safe_filename(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name) or "table"


def _redact_for_prompt(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                continue
            redacted[key] = _redact_for_prompt(item)
        return redacted
    if isinstance(value, list):
        return [_redact_for_prompt(item) for item in value]
    return value


class CodexCliDataGenerator:
    def __init__(
        self,
        output_dir="output/codex_generated_data",
        timeout_seconds=None,
        executable="codex",
        reuse_cached=True,
    ):
        self.output_dir = Path(output_dir)
        self.timeout_seconds = timeout_seconds
        self.executable = executable
        self.reuse_cached = reuse_cached

    def generate_tables(self, *, model, business_input, ddl_text, rows_per_table, allow_fallback=False):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        generated = {}
        expected_rows = {}
        stats = {
            "generation_engine": "codex-cli",
            "codex_tables_generated": [],
            "codex_adaptive_row_counts": {},
            "codex_raw_output_dir": str(self.output_dir),
            "truncated_values": 0,
        }
        for table in table_generation_order(model):
            row_count = self._row_count_for_table(table, rows_per_table)
            expected_rows[table.name] = row_count
            prompt = self.build_prompt(
                model=model,
                table=table,
                business_input=business_input,
                ddl_text=ddl_text,
                rows_per_table=row_count,
                generated_so_far=generated,
            )
            prompt_path = self.output_dir / f"{_safe_filename(table.name)}_prompt.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            raw = self._run_codex(prompt)
            raw_path = self.output_dir / f"{_safe_filename(table.name)}_raw_output.txt"
            raw_path.write_text(raw, encoding="utf-8")
            parsed = self.parse_json_output(raw, raw_path=self.output_dir / "codex_raw_output.txt")
            rows = self._extract_table_rows(parsed, table.name)
            if len(rows) != row_count:
                raise CodexCliGenerationError(f"Codex CLI returned {len(rows)} rows for {table.name}; expected {row_count}.")
            generated[table.name] = self._finalize_rows(table, rows, stats)
            table_json = self.output_dir / f"{_safe_filename(table.name)}.json"
            table_json.write_text(json.dumps({"tables": {table.name: generated[table.name]}}, indent=2, default=_json_default), encoding="utf-8")
            stats["codex_tables_generated"].append(table.name)
            if row_count != rows_per_table:
                stats["codex_adaptive_row_counts"][table.name] = row_count
        generated["__stats__"] = stats
        generated["__expected_rows__"] = expected_rows
        return generated


    def generate_warehouse_elt(self, *, model, business_input, ddl_text, semantic_context, pipeline_plan, rows_per_table, generation_profile=None):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        generation_profile = generation_profile or build_warehouse_generation_profile(
            model, pipeline_plan, rows_per_table
        )
        profile_path = self.output_dir / "warehouse_generation_profile.json"
        profile_path.write_text(
            json.dumps(generation_profile, indent=2, default=_json_default),
            encoding="utf-8",
        )
        prompt = self.build_warehouse_elt_prompt(
            model=model,
            business_input=business_input,
            ddl_text=ddl_text,
            semantic_context=semantic_context,
            pipeline_plan=pipeline_plan,
            rows_per_table=rows_per_table,
            generation_profile=generation_profile,
        )
        prompt_path = self.output_dir / "warehouse_elt_prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        raw_path = self.output_dir / "warehouse_elt_raw_output.txt"
        cache_path = self.output_dir / "warehouse_elt_cache.json"
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

        parsed = None
        if self.reuse_cached and raw_path.exists() and cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
                if cache.get("prompt_sha256") == prompt_hash:
                    parsed = self.parse_json_output(
                        raw_path.read_text(encoding="utf-8"),
                        raw_path=raw_path,
                    )
            except (OSError, ValueError, json.JSONDecodeError):
                parsed = None

        if parsed is None:
            raw = self._run_codex(prompt)
            raw_path.write_text(raw, encoding="utf-8")
            parsed = self.parse_json_output(raw, raw_path=raw_path)
            cache_path.write_text(
                json.dumps({"prompt_sha256": prompt_hash}, indent=2) + "\n",
                encoding="utf-8",
            )

        if not isinstance(parsed, dict):
            raise CodexCliGenerationError("Codex CLI ETL response must be a JSON object.")
        sql_artifact = self.output_dir / "warehouse_elt_sql.json"
        sql_artifact.write_text(json.dumps({
            "staging_sql": parsed.get("staging_sql", []),
            "dimension_sql": parsed.get("dimension_sql", []),
            "fact_sql": parsed.get("fact_sql", []),
            "assumptions": parsed.get("assumptions", []),
        }, indent=2, default=_json_default), encoding="utf-8")
        return parsed

    def build_warehouse_elt_prompt(self, *, model, business_input, ddl_text, semantic_context, pipeline_plan, rows_per_table, generation_profile=None):
        safe_business_input = _redact_for_prompt(business_input or {})
        model_payload = {"tables": [self._table_payload(table) for table in model.tables]}
        generation_profile = generation_profile or build_warehouse_generation_profile(
            model, pipeline_plan, rows_per_table
        )
        semantic_payload = {
            "business_name": getattr(semantic_context, "business_name", ""),
            "business_type": getattr(semantic_context, "business_type", ""),
            "domain_terms": getattr(semantic_context, "domain_terms", []),
            "entity_terms": getattr(semantic_context, "entity_terms", []),
            "table_roles": getattr(semantic_context, "table_roles", {}),
            "column_semantics": [
                {
                    "table_name": semantic.table_name,
                    "column_name": semantic.column_name,
                    "semantic_type": semantic.semantic_type,
                    "confidence": semantic.confidence,
                    "reasons": semantic.reasons,
                }
                for semantic in getattr(semantic_context, "column_semantics", {}).values()
            ],
        }
        return "\n".join([
            "You are a senior PostgreSQL data warehouse engineer.",
            "Generate connected synthetic data using a real ELT flow.",
            "Return strict JSON only. No markdown. No explanation outside JSON.",
            "Expected JSON shape:",
            json.dumps({
                "load_table_rows": {"<raw_or_load_table_name>": [{"<column_name>": "<value>"}]},
                "staging_sql": [],
                "dimension_sql": [],
                "fact_sql": [],
                "assumptions": [],
            }, indent=2),
            "Rules:",
            "1. Generate rows only for load/raw tables.",
            "2. Do not generate staging rows independently.",
            "3. Do not generate dimension rows independently.",
            "4. Do not generate fact rows independently.",
            "5. Generate PostgreSQL INSERT ... SELECT or WITH ... INSERT transformation SQL for staging tables from raw/load tables.",
            "6. Generate PostgreSQL INSERT ... SELECT or WITH ... INSERT transformation SQL for dimensions from staging tables.",
            "7. Generate PostgreSQL INSERT ... SELECT or WITH ... INSERT transformation SQL for facts from staging/event tables joined to dimensions.",
            "8. Facts must resolve surrogate keys from dimensions through business keys.",
            "9. Respect PostgreSQL data types.",
            "10. Respect CHECK constraints.",
            "11. Respect primary keys.",
            "12. Respect foreign keys.",
            "13. Respect nullable columns.",
            "14. Do not generate CREATE TABLE, DROP TABLE, ALTER TABLE, CREATE SCHEMA, DROP SCHEMA, DELETE, TRUNCATE, GRANT, REVOKE, or database administration SQL.",
            "15. Do not generate CREATE USER, CREATE ROLE, DROP DATABASE, DROP SCHEMA, COPY PROGRAM, SECURITY DEFINER, or ALTER SYSTEM SQL.",
            "16. Use only INSERT ... SELECT or WITH ... INSERT ... SELECT transformation SQL.",
            "17. Use only known parsed model tables. Do not target unknown schemas or unknown tables.",
            "18. Generate the exact raw/load row count specified in warehouse_generation_profile.raw_table_row_counts.",
            "19. Treat the requested row count as the main business-event population, not as an identical count for every entity.",
            "20. Reuse master/parent business keys across events and child rows. Do not create a new parent entity for every event.",
            "21. Use a non-uniform distribution: some valid parent entities must be referenced multiple times while others are referenced less often.",
            "22. For one-to-many relationships, generate multiple child/detail rows for at least some parent rows when DDL constraints allow it.",
            "23. Every child foreign-key value must resolve to a generated parent business key before SQL transformations run.",
            "24. For JSON/JSONB source_payload raw tables, put the mapped staging business columns inside source_payload using the exact staging column names.",
            "25. Keep ingestion metadata outside source_payload when the raw table has dedicated metadata columns.",
            "26. Spread date and timestamp values across the requested date_span_days instead of assigning one unique date per entity in a trivial sequence.",
            "27. Reconcile derived measures and aggregates from their source rows; do not invent totals independently.",
            "28. Respect uniqueness, nullability, defaults, identity columns, CHECK constraints, and all parsed foreign keys.",
            "29. When a relationship is marked require_reuse=true, at least one parent key must appear in multiple child rows.",
            "30. Do not use domain-specific assumptions unless they are explicitly present in the YAML, DDL, semantic context, or reference data.",
            f"The main business-event target is {rows_per_table} rows; per-table counts are defined below.",
            "warehouse_generation_profile:",
            json.dumps(generation_profile, indent=2, default=_json_default),
            "business_yaml_context:",
            json.dumps(safe_business_input, indent=2, default=_json_default),
            "parsed_ddl_model:",
            json.dumps(model_payload, indent=2, default=_json_default),
            "semantic_context:",
            json.dumps(semantic_payload, indent=2, default=_json_default),
            "warehouse_pipeline_plan:",
            json.dumps(pipeline_plan, indent=2, default=_json_default),
            "phase1_postgresql_ddl:",
            ddl_text[:20000],
        ])

    def _run_codex(self, prompt):
        try:
            result = subprocess.run(
                [
                    resolve_codex_executable() if self.executable == "codex" else self.executable,
                    "exec",
                    "--skip-git-repo-check",
                    "-",
                ],
                text=True,
                input=prompt,
                capture_output=True,
                timeout=self.timeout_seconds if self.timeout_seconds and self.timeout_seconds > 0 else None,
                check=False,
                cwd=PROJECT_ROOT,
            )
        except (OSError, subprocess.TimeoutExpired, CodexRunnerError) as exc:
            raise CodexCliGenerationError(f"Codex CLI generation failed: {exc}") from exc
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise CodexCliGenerationError(f"Codex CLI exited with status {result.returncode}: {stderr}")
        return result.stdout or ""

    def build_prompt(self, *, model, table, business_input, ddl_text, rows_per_table, generated_so_far=None):
        table_payload = self._table_payload(table)
        parent_payload = self._parent_key_payload(table, generated_so_far or {})
        safe_business_input = _redact_for_prompt(business_input or {})
        return "\n".join([
            "You are generating synthetic table row data for a data modeling accelerator.",
            "Return JSON only. Do not include markdown, explanations, comments, or code fences.",
            "Required JSON shape: {\"tables\": {\"table_name\": [{\"column_name\": \"value\"}]}}.",
            f"Generate exactly {rows_per_table} rows for table {table.name}.",
            "Use the target table and constraints below. Do not invent extra columns.",
            "DDL-first rules:",
            "- Use DDL CHECK IN allowed values before any YAML values.",
            "- Use YAML allowed_values and reference_data for matching unconstrained columns.",
            "- City values must come only from YAML cities when available.",
            "- Brand values must come only from YAML brands when available.",
            "- Do not use Faker/random invented cities or brands when YAML lists exist.",
            "- Status/method/type/category columns must use YAML/DDL CHECK values only.",
            "- Numeric columns must be JSON numbers, not strings.",
            "- Integer columns must be JSON integers.",
            "- Date columns must be ISO YYYY-MM-DD strings.",
            "- Timestamp columns must be ISO timestamp strings.",
            "- Boolean columns must be true/false.",
            "- FK columns must reference generated parent keys provided in parent_context.",
            "- Calculated columns must be calculated from related quantity/count and price columns, not random.",
            "- Avoid placeholder values such as Player 001, Customer 001, Product 001, Record 001, Value 001, Unknown 001 in semantic fields.",
            "Do not use or mention PostgreSQL connection host, user, password, database, or schema values.",
            "business_yaml_context:",
            json.dumps(safe_business_input, indent=2, default=_json_default),
            "target_table_schema:",
            json.dumps(table_payload, indent=2, default=_json_default),
            "parent_context:",
            json.dumps(parent_payload, indent=2, default=_json_default),
            "parsed_ddl_excerpt:",
            ddl_text[:12000],
        ])

    def parse_json_output(self, raw_output, raw_path=None):
        cleaned = self._strip_markdown_fences(raw_output).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            if raw_path is not None:
                Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
                Path(raw_path).write_text(raw_output, encoding="utf-8")
            raise CodexCliGenerationError(f"Codex CLI returned invalid JSON: {exc}") from exc

    def _strip_markdown_fences(self, text):
        text = (text or "").strip()
        if text.startswith("```"):
            text = FENCE_RE.sub("", text).strip()
        return text

    def _extract_table_rows(self, parsed, table_name):
        if not isinstance(parsed, dict) or not isinstance(parsed.get("tables"), dict):
            raise CodexCliGenerationError("Codex CLI JSON must contain a top-level 'tables' object.")
        rows = parsed["tables"].get(table_name)
        if not isinstance(rows, list):
            raise CodexCliGenerationError(f"Codex CLI JSON does not contain a row list for table {table_name}.")
        if not all(isinstance(row, dict) for row in rows):
            raise CodexCliGenerationError(f"Codex CLI rows for {table_name} must be JSON objects.")
        return rows

    def _finalize_rows(self, table, rows, stats):
        finalized = []
        for index, row in enumerate(rows, start=1):
            clean_row = {}
            for column in table.columns:
                clean_row[column.name] = finalize_generated_value(table, column, row.get(column.name), index, clean_row, stats)
            finalized.append(clean_row)
        return finalized

    def _table_payload(self, table):
        return {
            "name": table.name,
            "columns": [
                {
                    "name": column.name,
                    "data_type": column.data_type,
                    "nullable": column.nullable,
                    "primary_key": column.is_primary_key,
                    "max_length": column.max_length,
                    "numeric_precision": column.numeric_precision,
                    "numeric_scale": column.numeric_scale,
                }
                for column in table.columns
            ],
            "primary_key": table.primary_key,
            "foreign_keys": [fk.__dict__ for fk in table.foreign_keys],
            "unique_constraints": [unique.__dict__ for unique in getattr(table, "unique_constraints", [])],
            "check_constraints": [check.__dict__ for check in getattr(table, "check_constraints", [])],
        }

    def _parent_key_payload(self, table, generated_so_far):
        payload = {}
        for fk in table.foreign_keys:
            parent_rows = generated_so_far.get(fk.parent_table, [])
            payload[fk.parent_table] = [
                {column: row.get(column) for column in fk.parent_columns}
                for row in parent_rows
            ]
        return payload

    def _row_count_for_table(self, table, requested_rows):
        for unique in getattr(table, "unique_constraints", []):
            if len(unique.columns) != 1:
                continue
            column_name = unique.columns[0]
            values = []
            for check in getattr(table, "check_constraints", []):
                if check.supported and check.operator == "IN" and check.column == column_name and check.values:
                    values.extend(check.values)
            if values:
                return min(requested_rows, len(set(values)))
        return requested_rows
