from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import re
import subprocess

from .warehouse_lineage_planner import build_warehouse_lineage_plan
from .synthetic_data_generator import finalize_generated_value, table_generation_order, _apply_lineage_derivation, _finalize_row_values


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
    def __init__(self, output_dir="output/codex_generated_data", timeout_seconds=300, executable="codex"):
        self.output_dir = Path(output_dir)
        self.timeout_seconds = timeout_seconds
        self.executable = executable

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
        warehouse_plan = build_warehouse_lineage_plan(model)
        lineage = {
            "entities": warehouse_plan.entities,
            "raw_to_staging": warehouse_plan.raw_to_staging,
            "staging_to_dimension": warehouse_plan.staging_to_dimension,
            "fact_to_dimension": warehouse_plan.fact_to_dimension,
        }
        stats.update(warehouse_plan.stats())
        stats.update({
            "lineage_derivations": set(),
            "lineage_fact_key_resolutions": set(),
        })
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
                warehouse_plan=warehouse_plan,
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
            generated[table.name] = self._finalize_rows(table, rows, stats, generated, lineage)
            table_json = self.output_dir / f"{_safe_filename(table.name)}.json"
            table_json.write_text(json.dumps({"tables": {table.name: generated[table.name]}}, indent=2, default=_json_default), encoding="utf-8")
            stats["codex_tables_generated"].append(table.name)
            if row_count != rows_per_table:
                stats["codex_adaptive_row_counts"][table.name] = row_count
        generated["__stats__"] = stats
        generated["__expected_rows__"] = expected_rows
        return generated

    def _run_codex(self, prompt):
        try:
            result = subprocess.run(
                [self.executable, "exec", prompt],
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CodexCliGenerationError(f"Codex CLI generation failed: {exc}") from exc
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise CodexCliGenerationError(f"Codex CLI exited with status {result.returncode}: {stderr}")
        return result.stdout or ""

    def build_prompt(self, *, model, table, business_input, ddl_text, rows_per_table, generated_so_far=None, warehouse_plan=None):
        table_payload = self._table_payload(table)
        parent_payload = self._parent_key_payload(table, generated_so_far or {})
        safe_business_input = _redact_for_prompt(business_input or {})
        return "\n".join([
            "You are generating synthetic table row data for a data modeling accelerator.",
            "Act like a senior data architect designing a connected analytical warehouse.",
            "Return JSON only. Do not include markdown, explanations, comments, or code fences.",
            "Required JSON shape: {\"tables\": {\"table_name\": [{\"column_name\": \"value\"}]}}.",
            f"Generate exactly {rows_per_table} rows for table {table.name}.",
            "Use the target table and constraints below. Do not invent extra columns.",
            "Warehouse-lineage rules:",
            "- Treat raw/load rows as source records.",
            "- Staging rows must be derived from raw/load rows when source context exists.",
            "- Dimension rows must be derived from staging rows when source context exists.",
            "- Fact rows must use dimension keys that correspond to the same business keys from source/staging rows.",
            "- Do not independently invent unrelated raw, staging, dimension, and fact values.",
            "- If asked for canonical source records, use shape {\"canonical_records\": {\"entity\": [{...}]}}; Python materializes final tables.",
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
            "warehouse_lineage_plan:",
            json.dumps(warehouse_plan.stats() if warehouse_plan is not None else {}, indent=2, default=_json_default),
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

    def _finalize_rows(self, table, rows, stats, generated_so_far=None, lineage=None):
        finalized = []
        for index, row in enumerate(rows, start=1):
            clean_row = {}
            for column in table.columns:
                clean_row[column.name] = finalize_generated_value(table, column, row.get(column.name), index, clean_row, stats)
            if lineage is not None:
                _apply_lineage_derivation(table, clean_row, index, generated_so_far or {}, lineage, stats)
                _finalize_row_values(table, clean_row, index, stats)
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
