from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from codex_runner import resolve_codex_executable
from phase2.postgres_loader import preflight_postgres
from runtime_config import derive_target_schema, resolve_output_dir
from yaml_loader import load_yaml_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate accelerator prerequisites.")
    parser.add_argument("--yaml", required=True)
    args = parser.parse_args()

    yaml_path = Path(args.yaml)
    business_input = load_yaml_file(yaml_path)
    output_dir = resolve_output_dir(yaml_path, business_input)
    schema = derive_target_schema(yaml_path, business_input)
    codex = resolve_codex_executable()
    pg = preflight_postgres(schema, require_schema_create=True, recreate_schema=True)

    print("Preflight passed")
    print(f"Codex CLI: {codex}")
    print(f"Output directory: {output_dir}")
    print(f"PostgreSQL: {pg['host']}:{pg['port']}/{pg['database']}")
    print(f"Target schema: {schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
