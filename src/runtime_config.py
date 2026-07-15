from __future__ import annotations

import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_SCHEMAS = {
    "public",
    "information_schema",
    "pg_catalog",
    "pg_toast",
}


def load_project_env(*, override: bool = False) -> Path:
    """Load the project .env file explicitly, independent of the current directory."""
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(dotenv_path=env_path, override=override)
    return env_path


def slugify(value: str, *, default: str = "use_case", max_length: int = 55) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        normalized = default
    if not normalized:
        return ""
    if normalized[0].isdigit():
        normalized = f"uc_{normalized}"
    return normalized[:max_length].rstrip("_") or default


def use_case_slug(yaml_path: str | Path, business_input: dict | None = None) -> str:
    business_input = business_input or {}
    name = business_input.get("business_name") or Path(yaml_path).stem
    return slugify(name)


def resolve_output_dir(
    yaml_path: str | Path,
    business_input: dict | None = None,
    explicit_output_dir: str | Path | None = None,
) -> Path:
    if explicit_output_dir:
        return Path(explicit_output_dir)
    return PROJECT_ROOT / "output" / use_case_slug(yaml_path, business_input)


def resolve_excel_output(
    yaml_path: str | Path,
    business_input: dict | None = None,
    output_dir: str | Path | None = None,
    explicit_excel_output: str | Path | None = None,
) -> Path:
    if explicit_excel_output:
        return Path(explicit_excel_output)
    resolved_output_dir = Path(output_dir) if output_dir else resolve_output_dir(yaml_path, business_input)
    return resolved_output_dir / f"{use_case_slug(yaml_path, business_input)}_synthetic_data.xlsx"


def derive_target_schema(
    yaml_path: str | Path,
    business_input: dict | None = None,
    explicit_schema: str | None = None,
) -> str:
    """Return the approved per-use-case schema.

    Normal runner behavior derives the schema from the YAML so stale environment
    values cannot accidentally redirect a different use case. An override must be
    supplied explicitly by the caller.
    """
    load_project_env()
    explicit = (explicit_schema or "").strip()
    prefix = slugify(os.getenv("POSTGRES_SCHEMA_PREFIX", ""), default="", max_length=12)
    base = use_case_slug(yaml_path, business_input)
    schema = explicit or (f"{prefix}_{base}" if prefix else base)
    schema = slugify(schema, max_length=63)
    if schema.lower() in PROTECTED_SCHEMAS or schema.lower().startswith("pg_"):
        raise ValueError(f"Unsafe PostgreSQL target schema: {schema}")
    return schema
