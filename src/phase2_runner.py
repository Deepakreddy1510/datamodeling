import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from phase2.ddl_extractor import DDLExtractionError, extract_ddl
from phase2.ddl_parser import DDLParserError, parse_ddl
from phase2.codex_cli_data_generator import CodexCliDataGenerator, CodexCliGenerationError
from phase2.codex_etl_response_validator import validate_codex_etl_response
from phase2.codex_transformation_executor import execute_codex_transformation, read_existing_postgres_data
from phase2.excel_writer import write_excel
from phase2.postgres_loader import (
    PostgresLoadError,
    load_to_postgres,
    preflight_postgres,
    validate_postgres_load,
)
from phase2.report_writer import write_generation_report, write_postgres_report, write_validation_report
from phase2.semantic_context import build_semantic_context
from phase2.warehouse_pipeline_planner import build_warehouse_pipeline_plan
from phase2.lineage_validator import validate_lineage
from phase2.data_realism_validator import validate_data_realism
from phase2.warehouse_generation_profile import build_warehouse_generation_profile
from phase2.synthetic_data_generator import SyntheticDataError, generate_synthetic_data
from phase2.validator import validate_generated_data
from yaml_loader import load_yaml_file
from runtime_config import (
    derive_target_schema,
    resolve_excel_output,
    resolve_output_dir,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Phase 2 production warehouse generation, PostgreSQL ELT, validation, and Excel export"
    )
    parser.add_argument("--yaml", required=True, help="Path to business input YAML file.")
    parser.add_argument(
        "--phase1-output",
        help="Optional Phase 1 markdown path. By default it is resolved from the YAML use-case output directory.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Default: output/<business_name_slug>.",
    )
    parser.add_argument(
        "--rows-per-table", type=int, default=100, help="Base business-event row count. Default 100."
    )
    parser.add_argument(
        "--excel-output",
        help="Optional Excel path. Default: <output-dir>/<use_case>_synthetic_data.xlsx.",
    )
    load_group = parser.add_mutually_exclusive_group()
    load_group.add_argument(
        "--load-to-postgres", dest="load_to_postgres", action="store_true", help="Load to PostgreSQL (default)."
    )
    load_group.add_argument(
        "--no-load-to-postgres", dest="load_to_postgres", action="store_false", help="Skip PostgreSQL loading."
    )
    parser.set_defaults(load_to_postgres=True)
    parser.add_argument(
        "--target-schema",
        help="Optional explicit target schema. Default is derived safely from the YAML business name.",
    )
    parser.add_argument(
        "--schema-mode",
        choices=["recreate", "reuse", "append"],
        default="recreate",
        help="Target schema lifecycle. Default recreate provides clean repeatable runs.",
    )
    # Backward-compatible advanced flags. Normal product use does not need them.
    parser.add_argument("--create-schema-if-missing", action="store_true")
    parser.add_argument("--create-tables-if-missing", action="store_true")
    parser.add_argument("--truncate-before-load", action="store_true")
    parser.add_argument("--allow-insert-into-nonempty-tables", action="store_true")
    parser.add_argument("--seed", type=int, default=12345, help="Deterministic Python generator seed.")
    parser.add_argument(
        "--generation-engine",
        choices=["python", "codex-cli"],
        default="codex-cli",
        help="Generation engine. Default codex-cli.",
    )
    parser.add_argument("--allow-generator-fallback", action="store_true")
    parser.add_argument(
        "--codex-timeout-seconds",
        type=int,
        default=0,
        help="Codex timeout. Zero means no timeout.",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Ignore a matching saved Codex response and generate a new one.",
    )
    parser.add_argument(
        "--reuse-existing-postgres-data",
        action="store_true",
        help="Read, validate, and export existing target-schema data without generation.",
    )
    args = parser.parse_args()
    if not args.load_to_postgres and "--generation-engine" not in sys.argv[1:]:
        args.generation_engine = "python"
    return args


def resolve_phase1_output(path_arg, output_dir=None):
    if path_arg:
        path = Path(path_arg)
        if path.exists():
            return path
        raise FileNotFoundError(f"Phase 1 output file does not exist: {path}")
    if output_dir:
        candidates = [
            Path(output_dir) / "final_output.md",
            Path(output_dir) / "output.md",
        ]
    else:
        candidates = [Path("output/final_output.md"), Path("output/output.md")]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    expected = candidates[0] if candidates else Path("output/final_output.md")
    raise FileNotFoundError(
        f"Phase 1 output file not found. Run Phase 1 first; expected {expected}."
    )

def generate_phase2_data(args, *, model, business_input, ddl_text, semantic_context, output_dir):
    if args.generation_engine == "python":
        return generate_synthetic_data(model, args.rows_per_table, args.seed, semantic_context=semantic_context, business_input=business_input)
    generator = CodexCliDataGenerator(output_dir=output_dir / "codex_generated_data", timeout_seconds=args.codex_timeout_seconds or None)
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


def repair_derived_metrics(final_data):
    """Repair deterministic metrics using generic column relationships."""
    if not isinstance(final_data, dict):
        return final_data
    for rows in final_data.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            delay = row.get("delivery_delay_minutes", row.get("delay_minutes"))
            try:
                delayed = delay is not None and Decimal(str(delay)) > 0
            except (InvalidOperation, TypeError, ValueError):
                delayed = False
            if "delayed_delivery_count" in row:
                row["delayed_delivery_count"] = 1 if delayed else 0
            if "delayed_count" in row:
                row["delayed_count"] = 1 if delayed else 0
            if "is_delayed" in row:
                row["is_delayed"] = delayed
            if "available_quantity" in row and "on_hand_quantity" in row and "reserved_quantity" in row:
                try:
                    row["available_quantity"] = row["on_hand_quantity"] - row["reserved_quantity"]
                except TypeError:
                    pass
            if "short_received_quantity" in row and "ordered_quantity" in row and "received_quantity" in row:
                try:
                    row["short_received_quantity"] = row["ordered_quantity"] - row["received_quantity"]
                except TypeError:
                    pass
    return final_data


def run_existing_postgres_export(
    args, *, model, business_input, ddl_text, semantic_context, output_dir, phase1_output
):
    """Validate and export an already-loaded PostgreSQL warehouse without generation."""
    pipeline_plan = build_warehouse_pipeline_plan(model, semantic_context)
    generation_profile = build_warehouse_generation_profile(
        model, pipeline_plan, args.rows_per_table
    )
    execution = read_existing_postgres_data(model, target_schema=args.target_schema)
    if execution["status"] != "passed":
        validation = {
            "status": "failed",
            "errors": execution.get("errors", []),
            "generation_stats": {"generation_engine": "existing-postgres-readback"},
            "excel_written": False,
            "generation_profile": generation_profile,
        }
        write_postgres_report(output_dir / "postgres_load_report.md", True, execution)
        write_validation_report(output_dir / "validation_report.md", validation, execution)
        print(
            "Existing PostgreSQL readback failed. See output reports.",
            file=sys.stderr,
        )
        return 1

    final_data = repair_derived_metrics(execution.get("table_data", {}))
    expected_rows = {
        table.name: len(final_data.get(table.name, []))
        for table in model.tables
    }
    validation = validate_generated_data(
        model,
        final_data,
        expected_rows,
        semantic_context=semantic_context,
        business_input=business_input,
    )
    lineage_validation = validate_lineage(model, final_data, pipeline_plan)
    realism_validation = validate_data_realism(
        model, final_data, generation_profile
    )
    if lineage_validation["status"] == "failed":
        validation["status"] = "failed"
        validation.setdefault("errors", []).extend(
            lineage_validation.get("errors", [])
        )
    if realism_validation["status"] == "failed":
        validation["status"] = "failed"
        validation.setdefault("errors", []).extend(
            realism_validation.get("errors", [])
        )
    elif (
        realism_validation["status"] == "passed_with_warnings"
        and validation["status"] == "passed"
    ):
        validation["status"] = "passed_with_warnings"

    validation["generation_stats"] = {
        "generation_engine": "existing-postgres-readback"
    }
    validation["excel_written"] = False
    validation["lineage_validation"] = lineage_validation
    validation["realism_validation"] = realism_validation
    validation["generation_profile"] = generation_profile

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
        elt_execution=execution,
        lineage_validation=lineage_validation,
    )
    write_postgres_report(output_dir / "postgres_load_report.md", True, execution)
    write_validation_report(
        output_dir / "validation_report.md",
        validation,
        execution,
        lineage_validation=lineage_validation,
    )
    if validation["status"] == "failed":
        print(
            "Existing PostgreSQL data contains validation errors. See output reports.",
            file=sys.stderr,
        )
        return 1
    print(
        "Existing PostgreSQL data validated. Excel was written without invoking Codex."
    )
    return 0


def run_codex_cli_elt_flow(args, *, model, business_input, ddl_text, semantic_context, output_dir, phase1_output):
    if not args.load_to_postgres:
        raise ValueError("--generation-engine codex-cli requires --load-to-postgres because staging, dimension, and fact tables are generated by PostgreSQL SQL transformations.")
    pipeline_plan = build_warehouse_pipeline_plan(model, semantic_context)
    generation_profile = build_warehouse_generation_profile(
        model, pipeline_plan, args.rows_per_table
    )
    preflight_postgres(
        args.target_schema,
        require_schema_create=True,
        recreate_schema=(args.schema_mode == "recreate"),
    )
    generator = CodexCliDataGenerator(
        output_dir=output_dir / "codex_generated_data",
        timeout_seconds=args.codex_timeout_seconds or None,
        reuse_cached=not args.force_regenerate,
    )
    etl_response = generator.generate_warehouse_elt(
        model=model,
        business_input=business_input,
        ddl_text=ddl_text,
        semantic_context=semantic_context,
        pipeline_plan=pipeline_plan,
        rows_per_table=args.rows_per_table,
        generation_profile=generation_profile,
    )
    response_validation = validate_codex_etl_response(
        etl_response, model, pipeline_plan, generation_profile
    )
    if response_validation["status"] == "failed":
        # A structurally invalid response must not become a permanent retry loop.
        (output_dir / "codex_generated_data" / "warehouse_elt_cache.json").unlink(
            missing_ok=True
        )
        skipped_reason = "PostgreSQL execution skipped because Codex ETL response validation failed before execution."
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
            "generation_profile": generation_profile,
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
        postgres_result = {"status": "failed", "errors": response_validation["errors"], "skipped_reason": skipped_reason}
        write_postgres_report(output_dir / "postgres_load_report.md", True, postgres_result)
        write_validation_report(output_dir / "validation_report.md", validation, postgres_result)
        print("Codex ETL response validation failed; PostgreSQL execution was skipped. See output reports.", file=sys.stderr)
        return 1

    execution = execute_codex_transformation(
        model,
        etl_response,
        pipeline_plan,
        target_schema=args.target_schema,
        create_schema_if_missing=(args.schema_mode != "append") or args.create_schema_if_missing,
        create_tables_if_missing=(args.schema_mode != "append") or args.create_tables_if_missing,
        truncate_before_load=(args.schema_mode == "reuse") or args.truncate_before_load,
        allow_insert_into_nonempty_tables=(args.schema_mode == "append") or args.allow_insert_into_nonempty_tables,
        recreate_schema=(args.schema_mode == "recreate"),
    )
    if execution["status"] != "passed":
        validation = {
            "status": "failed",
            "errors": execution.get("errors", []),
            "generation_stats": {"generation_engine": "codex-cli-elt", "codex_sql_artifact": str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json")},
            "excel_written": False,
            "codex_response_validation": response_validation,
            "generation_profile": generation_profile,
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
        write_validation_report(output_dir / "validation_report.md", validation, execution)
        print("PostgreSQL ELT execution failed. See output/postgres_load_report.md.", file=sys.stderr)
        return 1

    final_data = repair_derived_metrics(execution.get("table_data", {}))
    expected_rows = {table.name: len(final_data.get(table.name, [])) for table in model.tables}
    validation = validate_generated_data(model, final_data, expected_rows, semantic_context=semantic_context, business_input=business_input)
    lineage_validation = validate_lineage(model, final_data, pipeline_plan)
    realism_validation = validate_data_realism(model, final_data, generation_profile)
    if lineage_validation["status"] == "failed":
        validation["status"] = "failed"
        validation.setdefault("errors", []).extend(lineage_validation.get("errors", []))
    if realism_validation["status"] == "failed":
        validation["status"] = "failed"
        validation.setdefault("errors", []).extend(realism_validation.get("errors", []))
    elif realism_validation["status"] == "passed_with_warnings" and validation["status"] == "passed":
        validation["status"] = "passed_with_warnings"
    validation["generation_stats"] = {
        "generation_engine": "codex-cli-elt",
        "codex_raw_output_dir": str(output_dir / "codex_generated_data"),
        "codex_sql_artifact": str(output_dir / "codex_generated_data" / "warehouse_elt_sql.json"),
    }
    validation["excel_written"] = False
    validation["codex_response_validation"] = response_validation
    validation["lineage_validation"] = lineage_validation
    validation["realism_validation"] = realism_validation
    validation["generation_profile"] = generation_profile
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
    write_validation_report(output_dir / "validation_report.md", validation, execution, lineage_validation=lineage_validation)
    if validation["status"] == "failed":
        (output_dir / "codex_generated_data" / "warehouse_elt_cache.json").unlink(
            missing_ok=True
        )
        print(
            f"Phase 2 completed with validation errors. See {output_dir}.",
            file=sys.stderr,
        )
        return 1
    print("Phase 2 codex-cli ELT completed. Excel was written from PostgreSQL readback data.")
    return 0


def main():
    args = parse_args()
    explicit_excel_output = args.excel_output
    output_dir = Path(args.output_dir) if args.output_dir else Path("output")
    args.excel_output = explicit_excel_output or str(output_dir / "synthetic_data_output.xlsx")
    if args.rows_per_table <= 0:
        print("Error: --rows-per-table must be positive.", file=sys.stderr)
        return 1

    try:
        business_input = load_yaml_file(args.yaml)
        output_dir = resolve_output_dir(args.yaml, business_input, args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output_dir = str(output_dir)
        args.excel_output = str(
            resolve_excel_output(
                args.yaml,
                business_input,
                output_dir,
                explicit_excel_output,
            )
        )
        args.target_schema = derive_target_schema(
            args.yaml, business_input, explicit_schema=args.target_schema
        )
        phase1_output = resolve_phase1_output(args.phase1_output, output_dir)
        markdown = phase1_output.read_text(encoding="utf-8")
        ddl_text = extract_ddl(markdown)
        model = parse_ddl(ddl_text)
        semantic_context = build_semantic_context(business_input, model)

        if args.reuse_existing_postgres_data:
            preflight_postgres(args.target_schema, require_schema_create=False)
            return run_existing_postgres_export(
                args,
                model=model,
                business_input=business_input,
                ddl_text=ddl_text,
                semantic_context=semantic_context,
                output_dir=output_dir,
                phase1_output=phase1_output,
            )

        if args.generation_engine == "codex-cli":
            if not args.load_to_postgres:
                raise ValueError(
                    "codex-cli ELT requires PostgreSQL. Use the default PostgreSQL mode "
                    "or select --generation-engine python --no-load-to-postgres."
                )
            return run_codex_cli_elt_flow(
                args,
                model=model,
                business_input=business_input,
                ddl_text=ddl_text,
                semantic_context=semantic_context,
                output_dir=output_dir,
                phase1_output=phase1_output,
            )

        data = generate_phase2_data(
            args,
            model=model,
            business_input=business_input,
            ddl_text=ddl_text,
            semantic_context=semantic_context,
            output_dir=output_dir,
        )
        expected_rows = data.get("__expected_rows__", args.rows_per_table)
        pre_validation = validate_generated_data(
            model,
            data,
            expected_rows,
            semantic_context=semantic_context,
            business_input=business_input,
        )
        pipeline_plan = build_warehouse_pipeline_plan(model, semantic_context)
        generation_profile = (
            data.get("__stats__", {}).get("generation_profile")
            or build_warehouse_generation_profile(model, pipeline_plan, args.rows_per_table)
        )
        lineage_validation = validate_lineage(model, data, pipeline_plan)
        realism_validation = validate_data_realism(model, data, generation_profile)
        if lineage_validation["status"] == "failed":
            pre_validation["status"] = "failed"
            pre_validation.setdefault("errors", []).extend(lineage_validation.get("errors", []))
        if realism_validation["status"] == "failed":
            pre_validation["status"] = "failed"
            pre_validation.setdefault("errors", []).extend(realism_validation.get("errors", []))
        elif realism_validation["status"] == "passed_with_warnings" and pre_validation["status"] == "passed":
            pre_validation["status"] = "passed_with_warnings"
        pre_validation["generation_stats"] = data.get("__stats__", {})
        pre_validation["generation_profile"] = generation_profile
        pre_validation["lineage_validation"] = lineage_validation
        pre_validation["realism_validation"] = realism_validation
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
                pipeline_plan=pipeline_plan,
                lineage_validation=lineage_validation,
            )
            result = {
                "status": "failed",
                "errors": pre_validation.get("errors", []),
                "skipped_reason": "PostgreSQL execution skipped because generated data validation failed.",
            }
            write_postgres_report(output_dir / "postgres_load_report.md", args.load_to_postgres, result)
            write_validation_report(
                output_dir / "validation_report.md",
                pre_validation,
                result if args.load_to_postgres else None,
                lineage_validation=lineage_validation,
            )
            print(f"Phase 2 failed validation. See {output_dir / 'validation_report.md'}.", file=sys.stderr)
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

        load_result = {}
        post_validation = None
        if args.load_to_postgres:
            preflight_postgres(args.target_schema, require_schema_create=True)
            load_result = load_to_postgres(
                model,
                data,
                target_schema=args.target_schema,
                create_schema_if_missing=True,
                create_tables_if_missing=True,
                truncate_before_load=True,
            )
            if load_result["status"] == "passed":
                expected_postgres_rows = {
                    table.name: expected_rows.get(table.name, args.rows_per_table)
                    if isinstance(expected_rows, dict)
                    else args.rows_per_table
                    for table in model.tables
                }
                post_validation = validate_postgres_load(
                    model, expected_postgres_rows, target_schema=args.target_schema
                )
        write_postgres_report(output_dir / "postgres_load_report.md", args.load_to_postgres, load_result)
        validation_post_result = post_validation or (load_result if args.load_to_postgres else None)
        write_validation_report(
            output_dir / "validation_report.md",
            pre_validation,
            validation_post_result,
            lineage_validation=lineage_validation,
        )
        if load_result.get("status") == "failed" or (
            post_validation and post_validation.get("status") != "passed"
        ):
            print(f"Phase 2 completed with PostgreSQL errors. See {output_dir}.", file=sys.stderr)
            return 1
        print(
            f"Phase 2 completed successfully. Excel: {args.excel_output}. "
            f"PostgreSQL schema: {args.target_schema}."
        )
        return 0
    except (
        DDLExtractionError,
        DDLParserError,
        SyntheticDataError,
        CodexCliGenerationError,
        PostgresLoadError,
        OSError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        message = str(exc)
        output_dir.mkdir(parents=True, exist_ok=True)
        pre_validation = {"status": "failed", "errors": [message]}
        write_generation_report(
            output_dir / "synthetic_data_generation_report.md",
            yaml_path=args.yaml,
            phase1_output=args.phase1_output or str(output_dir / "final_output.md"),
            ddl_text="",
            model=type("EmptyModel", (), {"tables": []})(),
            rows_per_table=args.rows_per_table,
            excel_output=args.excel_output,
            validation=pre_validation,
        )
        result = {
            "status": "failed",
            "errors": [message],
            "skipped_reason": "PostgreSQL execution did not complete.",
        }
        write_postgres_report(output_dir / "postgres_load_report.md", args.load_to_postgres, result)
        write_validation_report(
            output_dir / "validation_report.md",
            pre_validation,
            result if args.load_to_postgres else None,
        )
        print(f"Error: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
