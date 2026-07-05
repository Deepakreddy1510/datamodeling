import argparse
import sys
from pathlib import Path

from phase2.ddl_extractor import DDLExtractionError, extract_ddl
from phase2.ddl_parser import DDLParserError, parse_ddl
from phase2.excel_writer import write_excel
from phase2.postgres_loader import load_to_postgres, validate_postgres_load
from phase2.report_writer import write_generation_report, write_postgres_report, write_validation_report
from phase2.synthetic_data_generator import SyntheticDataError, generate_synthetic_data
from phase2.value_catalog_parser import parse_synthetic_value_catalog
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


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.rows_per_table <= 0:
        print("Error: --rows-per-table must be positive.", file=sys.stderr)
        return 1

    value_catalog = None

    try:
        load_yaml_file(args.yaml)
        phase1_output = resolve_phase1_output(args.phase1_output)
        markdown = phase1_output.read_text(encoding="utf-8")
        ddl_text = extract_ddl(markdown)
        value_catalog = parse_synthetic_value_catalog(markdown)
        model = parse_ddl(ddl_text)
        data = generate_synthetic_data(model, args.rows_per_table, args.seed, value_catalog=value_catalog)
        pre_validation = validate_generated_data(model, data, args.rows_per_table, value_catalog=value_catalog)
        pre_validation["generation_stats"] = data.get("__stats__", {})
        write_generation_report(
            output_dir / "synthetic_data_generation_report.md",
            yaml_path=args.yaml,
            phase1_output=str(phase1_output),
            ddl_text=ddl_text,
            model=model,
            rows_per_table=args.rows_per_table,
            excel_output=args.excel_output,
            validation=pre_validation,
            value_catalog=value_catalog,
        )
        if pre_validation["status"] == "failed":
            write_postgres_report(output_dir / "postgres_load_report.md", False, {})
            write_validation_report(output_dir / "validation_report.md", pre_validation)
            print("Phase 2 failed pre-load validation. See output/validation_report.md.", file=sys.stderr)
            return 1

        write_excel(model, data, args.excel_output)

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
                post_validation = validate_postgres_load(model, {table.name: args.rows_per_table for table in model.tables})
        write_postgres_report(output_dir / "postgres_load_report.md", args.load_to_postgres, load_result)
        write_validation_report(output_dir / "validation_report.md", pre_validation, post_validation)
        if load_result.get("status") == "failed" or (post_validation and post_validation.get("status") != "passed"):
            print("Phase 2 completed with PostgreSQL errors. See output/postgres_load_report.md and output/validation_report.md.", file=sys.stderr)
            return 1
        print("Phase 2 completed. See output/synthetic_data_output.xlsx and Phase 2 reports.")
        return 0
    except (DDLExtractionError, DDLParserError, SyntheticDataError, OSError, ValueError, FileNotFoundError) as exc:
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
            value_catalog=value_catalog,
        )
        write_postgres_report(output_dir / "postgres_load_report.md", False, {})
        write_validation_report(output_dir / "validation_report.md", pre_validation)
        print(f"Error: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
