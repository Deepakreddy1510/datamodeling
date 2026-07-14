import argparse
import sys
from pathlib import Path

from phase2.ddl_extractor import DDLExtractionError, extract_ddl
from phase2.ddl_parser import DDLParserError, parse_ddl
from phase2.codex_cli_data_generator import CodexCliDataGenerator, CodexCliGenerationError
from phase2.codex_etl_response_validator import validate_codex_etl_response
from phase2.codex_transformation_executor import execute_codex_transformation
from phase2.excel_writer import write_excel
from phase2.postgres_loader import PostgresLoadError, load_to_postgres, validate_postgres_load
from phase2.report_writer import write_generation_report, write_postgres_report, write_validation_report
from phase2.semantic_context import build_semantic_context
from phase2.warehouse_pipeline_planner import build_warehouse_pipeline_plan
from phase2.lineage_validator import validate_lineage
from phase2.synthetic_data_generator import SyntheticDataError, generate_synthetic_data
from phase2.validator import validate_generated_data
from yaml_loader import load_yaml_file


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 2 synthetic data generation and PostgreSQL loading")
    parser.add_argument("--yaml", required=True, help="Path to business input YAML file.")
    parser.add_argument("--phase1-output", help="Path to Phase 1 markdown output. Defaults to output/final_output.md with fallback to output/output.md.")
    parser.add_argument("--output-dir", default="output", help="Directory for Phase 2 reports.")
    parser.add_argument("--rows-per-table", type=int, default=100, help="Synthetic rows per table. Default 100.")
    parser.add_argument("--excel-output", default="output/synthetic_data_output.xlsx", help="Path for generated Excel workbook.")
    load_group = parser.add_mutually_exclusive_group()
    load_group.add_argument("--load-to-postgres", action="store_true", help="Load generated data to PostgreSQL.")
    load_group.add_argument("--no-load-to-postgres", action="store_true", help="Skip PostgreSQL loading.")
    parser.add_argument("--create-schema-if-missing", action="store_true", help="Create approved target schema if missing.")
    parser.add_argument("--create-tables-if-missing", action="store_true", help="Create target tables from parsed DDL if missing.")
    parser.add_argument("--truncate-before-load", action="store_true", help="Truncate target tables before loading.")
    parser.add_argument("--allow-insert-into-nonempty-tables", action="store_true", help="Allow inserts into non-empty target tables.")
    parser.add_argument("--seed", type=int, default=12345, help="Deterministic fake data seed.")
    parser.add_argument("--generation-engine", choices=["python", "codex-cli"], default="python", help="Synthetic data engine. Default: python.")
    parser.add_argument("--allow-generator-fallback", action="store_true", help="Fall back to the Python generator if the experimental Codex CLI generator fails.")
    parser.add_argument("--codex-timeout-seconds", type=int, default=300, help="Timeout for each Codex CLI table generation call. Default 300 seconds.")
    return parser.parse_args()


def resolve_phase1_output(path_arg):
    if path_arg:
        path = Path(path_arg)
        if path.exists():
            return path
        fallback = Path("output/output.md") if path.name == "final_output.md" else None
        if fallback and fallback.exists():
            return fallback
        raise FileNotFoundError(f"Phase 1 output file does not exist: {path}")
    final_output = Path("output/final_output.md")
    if final_output.exists():
        return final_output
    output = Path("output/output.md")
    if output.exists():
        return output
    raise FileNotFoundError("Phase 1 output file not found. Expected output/final_output.md or output/output.md.")


def generate_phase2_data(args, *, model, business_input, ddl_text, semantic_context, output_dir):
    if args.generation_engine == "python":
        return generate_synthetic_data(model, args.rows_per_table, args.seed, semantic_context=semantic_context, business_input=business_input)
    generator = CodexCliDataGenerator(output_dir=output_dir / "codex_generated_data", timeout_seconds=args.codex_timeout_seconds)
    try:
        return generator.generate_tables(
            model=model,
            business_input=business_input,
            ddl_text=ddl_text,
            rows_per_table=args.rows_per_table,
            allow_fallback=args.allow_generator_fallback,
        )
    except CodexCliGenerationError:
        if not args.allow_generator_fallback:
            raise
        data = generate_synthetic_data(model, args.rows_per_table, args.seed, semantic_context=semantic_context, business_input=business_input)
        data.setdefault("__stats__", {})["generation_engine"] = "python-fallback"
        return data


def run_codex_cli_elt_flow(args, *, model, business_input, ddl_text, semantic_context, output_dir, phase1_output):
    if not args.load_to_postgres:
        raise ValueError("--generation-engine codex-cli requires --load-to-postgres because staging, dimension, and fact tables are generated by PostgreSQL SQL transformations.")
    pipeline_plan = build_warehouse_pipeline_plan(model, semantic_context)
    generator = CodexCliDataGenerator(output_dir=output_dir / "codex_generated_data", timeout_seconds=args.codex_timeout_seconds)
    etl_response = generator.generate_warehouse_elt(
        model=model,
        business_input=business_input,
        ddl_text=ddl_text,
        semantic_context=semantic_context,
        pipeline_plan=pipeline_plan,
        rows_per_table=args.rows_per_table,
    )
    response_validation = validate_codex_etl_response(etl_response, model, pipeline_plan)
    if response_validation["status"] == "failed":
        validation = {
            "status": "failed",
            "errors": response_validation["errors"],
            "generation_stats": {
                "generation_engine": "codex-cli-elt",
                "codex_raw_output_dir": str(output_dir / "codex_generated_data"),
                "codex_sql_artifact": str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json"),
            },
            "excel_written": False,
            "codex_response_validation": response_validation,
        }
        write_generation_report(
            output_dir / "synthetic_data_generation_report.md",
            yaml_path=args.yaml,
            phase1_output=str(phase1_output),
            ddl_text=ddl_text,
            model=model,
            rows_per_table=args.rows_per_table,
            excel_output=args.excel_output,
            validation=validation,
            pipeline_plan=pipeline_plan,
            codex_assumptions=etl_response.get("assumptions", []),
            codex_sql_artifact=str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json"),
        )
        write_postgres_report(output_dir / "postgres_load_report.md", False, {})
        write_validation_report(output_dir / "validation_report.md", validation)
        return 1

    execution = execute_codex_transformation(
        model,
        etl_response,
        pipeline_plan,
        create_schema_if_missing=args.create_schema_if_missing,
        create_tables_if_missing=args.create_tables_if_missing,
        truncate_before_load=args.truncate_before_load,
        allow_insert_into_nonempty_tables=args.allow_insert_into_nonempty_tables,
    )
    if execution["status"] != "passed":
        validation = {
            "status": "failed",
            "errors": execution.get("errors", []),
            "generation_stats": {"generation_engine": "codex-cli-elt", "codex_sql_artifact": str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json")},
            "excel_written": False,
            "codex_response_validation": response_validation,
        }
        write_generation_report(
            output_dir / "synthetic_data_generation_report.md",
            yaml_path=args.yaml,
            phase1_output=str(phase1_output),
            ddl_text=ddl_text,
            model=model,
            rows_per_table=args.rows_per_table,
            excel_output=args.excel_output,
            validation=validation,
            pipeline_plan=pipeline_plan,
            codex_assumptions=etl_response.get("assumptions", []),
            codex_sql_artifact=str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json"),
        )
        write_postgres_report(output_dir / "postgres_load_report.md", True, execution)
        write_validation_report(output_dir / "validation_report.md", validation)
        return 1

    final_data = execution.get("table_data", {})
    expected_rows = {table.name: len(final_data.get(table.name, [])) for table in model.tables}
    validation = validate_generated_data(model, final_data, expected_rows, semantic_context=semantic_context, business_input=business_input)
    lineage_validation = validate_lineage(model, final_data, pipeline_plan)
    if lineage_validation["status"] == "failed":
        validation["status"] = "failed"
        validation.setdefault("errors", []).extend(lineage_validation.get("errors", []))
    validation["generation_stats"] = {
        "generation_engine": "codex-cli-elt",
        "codex_raw_output_dir": str(output_dir / "codex_generated_data"),
        "codex_sql_artifact": str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json"),
    }
    validation["excel_written"] = False
    validation["codex_response_validation"] = response_validation
    validation["lineage_validation"] = lineage_validation
    if validation["status"] != "failed":
        write_excel(model, final_data, args.excel_output)
        validation["excel_written"] = True
    write_generation_report(
        output_dir / "synthetic_data_generation_report.md",
        yaml_path=args.yaml,
        phase1_output=str(phase1_output),
        ddl_text=ddl_text,
        model=model,
        rows_per_table=args.rows_per_table,
        excel_output=args.excel_output,
        validation=validation,
        pipeline_plan=pipeline_plan,
        codex_assumptions=etl_response.get("assumptions", []),
        codex_sql_artifact=str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json"),
        elt_execution=execution,
        lineage_validation=lineage_validation,
    )
    write_postgres_report(output_dir / "postgres_load_report.md", True, execution)
    write_validation_report(output_dir / "validation_report.md", validation, lineage_validation=lineage_validation)
    if validation["status"] == "failed":
        print("Phase 2 codex-cli ELT completed with validation errors. See output reports.", file=sys.stderr)
        return 1
    print("Phase 2 codex-cli ELT completed. Excel was written from PostgreSQL readback data.")
    return 0


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.rows_per_table <= 0:
        print("Error: --rows-per-table must be positive.", file=sys.stderr)
        return 1

    try:
        business_input = load_yaml_file(args.yaml)
        phase1_output = resolve_phase1_output(args.phase1_output)
        markdown = phase1_output.read_text(encoding="utf-8")
        ddl_text = extract_ddl(markdown)
        model = parse_ddl(ddl_text)
        semantic_context = build_semantic_context(business_input, model)
        if args.generation_engine == "codex-cli":
            return run_codex_cli_elt_flow(args, model=model, business_input=business_input, ddl_text=ddl_text, semantic_context=semantic_context, output_dir=output_dir, phase1_output=phase1_output)
        data = generate_phase2_data(args, model=model, business_input=business_input, ddl_text=ddl_text, semantic_context=semantic_context, output_dir=output_dir)
        expected_rows = data.get("__expected_rows__", args.rows_per_table)
        pre_validation = validate_generated_data(model, data, expected_rows, semantic_context=semantic_context, business_input=business_input)
        pre_validation["generation_stats"] = data.get("__stats__", {})
        pre_validation["excel_written"] = False
        if pre_validation["status"] == "failed":
            write_generation_report(
                output_dir / "synthetic_data_generation_report.md",
                yaml_path=args.yaml,
                phase1_output=str(phase1_output),
                ddl_text=ddl_text,
                model=model,
                rows_per_table=args.rows_per_table,
                excel_output=args.excel_output,
                validation=pre_validation,
            )
            write_postgres_report(output_dir / "postgres_load_report.md", False, {})
            write_validation_report(output_dir / "validation_report.md", pre_validation)
            print("Phase 2 failed pre-load validation. See output/validation_report.md.", file=sys.stderr)
            return 1

        write_excel(model, data, args.excel_output)
        pre_validation["excel_written"] = True
        write_generation_report(
            output_dir / "synthetic_data_generation_report.md",
            yaml_path=args.yaml,
            phase1_output=str(phase1_output),
            ddl_text=ddl_text,
            model=model,
            rows_per_table=args.rows_per_table,
            excel_output=args.excel_output,
            validation=pre_validation,
        )

        post_validation = None
        load_result = {}
        if args.load_to_postgres:
            load_result = load_to_postgres(
                model,
                data,
                create_schema_if_missing=args.create_schema_if_missing,
                create_tables_if_missing=args.create_tables_if_missing,
                truncate_before_load=args.truncate_before_load,
                allow_insert_into_nonempty_tables=args.allow_insert_into_nonempty_tables,
            )
            if load_result["status"] == "passed":
                if isinstance(expected_rows, dict):
                    expected_postgres_rows = {table.name: expected_rows.get(table.name, args.rows_per_table) for table in model.tables}
                else:
                    expected_postgres_rows = {table.name: args.rows_per_table for table in model.tables}
                post_validation = validate_postgres_load(model, expected_postgres_rows)
        write_postgres_report(output_dir / "postgres_load_report.md", args.load_to_postgres, load_result)
        write_validation_report(output_dir / "validation_report.md", pre_validation, post_validation)
        if load_result.get("status") == "failed" or (post_validation and post_validation.get("status") != "passed"):
            print("Phase 2 completed with PostgreSQL errors. See output/postgres_load_report.md and output/validation_report.md.", file=sys.stderr)
            return 1
        print("Phase 2 completed. See output/synthetic_data_output.xlsx and Phase 2 reports.")
        return 0
    except (DDLExtractionError, DDLParserError, SyntheticDataError, CodexCliGenerationError, PostgresLoadError, OSError, ValueError, FileNotFoundError) as exc:
        message = str(exc)
        pre_validation = {"status": "failed", "errors": [message]}
        write_generation_report(
            output_dir / "synthetic_data_generation_report.md",
            yaml_path=args.yaml,
            phase1_output=args.phase1_output or "output/final_output.md",
            ddl_text="",
            model=type("EmptyModel", (), {"tables": []})(),
            rows_per_table=args.rows_per_table,
            excel_output=args.excel_output,
            validation=pre_validation,
        )
        write_postgres_report(output_dir / "postgres_load_report.md", False, {})
        write_validation_report(output_dir / "validation_report.md", pre_validation)
        print(f"Error: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
