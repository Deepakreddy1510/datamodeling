# Data Modelling Accelerator V3

Production-hardened two-phase accelerator for turning a business YAML file into:

- conceptual, logical, and physical PostgreSQL models;
- raw/load, staging, dimension, fact, and reporting structures;
- relational synthetic data;
- PostgreSQL ELT execution and readback validation;
- a formatted Excel workbook;
- generation, validation, lineage, realism, and PostgreSQL reports.

The implementation is generic. It derives the model and generation behavior from the YAML and generated DDL rather than relying on FreshCart- or Air India-specific table logic.

## One-time setup

### WSL, Ubuntu, macOS, or Linux

```bash
cd datamodelling-accelerator-v3
./setup.sh
source .venv/bin/activate
```

Equivalent manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Codex CLI must be installed and authenticated:

```bash
codex --version
```

No `git init` is required. Both Phase 1 and Phase 2 invoke Codex with `--skip-git-repo-check`.

## PostgreSQL configuration

The local `.env` file contains the configured connection details. It is ignored by Git.

Required settings:

```text
POSTGRES_HOST=...
POSTGRES_PORT=...
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_SSLMODE=prefer
POSTGRES_CONNECT_TIMEOUT=15
```

The normal runner ignores stale `POSTGRES_TARGET_SCHEMA` environment values and derives an isolated, PostgreSQL-safe schema from `business_name`, for example:

```text
Air India Cabin Capacity Optimization
→ air_india_cabin_capacity_optimization
```

This prevents one use case from overwriting another. An approved explicit schema can be supplied deliberately with `--target-schema approved_schema`.

Before company deployment, rotate any password that has previously been shared through chat, terminal history, email, or tickets.

## Normal product workflow

For Air India, only these two commands are required after setup.

### Phase 1

```bash
python src/main.py \
  --input input/air_india_cabin_capacity_optimization.yaml
```

### Phase 2 with 15 base rows

```bash
python src/phase2_runner.py \
  --yaml input/air_india_cabin_capacity_optimization.yaml \
  --rows-per-table 15
```

Phase 2 defaults to:

- Codex CLI warehouse ELT generation;
- PostgreSQL preflight before spending Codex generation time;
- one isolated schema per YAML;
- atomic clean schema recreation;
- missing schema and table creation;
- raw/load insertion;
- staging, dimension, and fact SQL execution;
- PostgreSQL readback;
- FK, constraint, lineage, calculation, date, realism, and row-count validation;
- formatted Excel generation;
- automatic reuse of an unchanged valid Codex response after a failed retry.

## Automatic output locations

Outputs are isolated by use case:

```text
output/<business_name_slug>/
```

Air India example:

```text
output/air_india_cabin_capacity_optimization/
├── final_output.md
├── air_india_cabin_capacity_optimization_synthetic_data.xlsx
├── validation_report.md
├── postgres_load_report.md
├── synthetic_data_generation_report.md
├── generation_quality_report.md
└── codex_generated_data/
```

Phase 2 automatically finds the matching Phase 1 `final_output.md`. No `--phase1-output`, `--output-dir`, or `--excel-output` arguments are required for normal use.

## Optional preflight command

Phase 2 already runs its own preflight. The standalone command is useful for deployment checks:

```bash
PYTHONPATH=src python scripts/preflight.py \
  --yaml input/air_india_cabin_capacity_optimization.yaml
```

It validates:

- YAML readability;
- Codex CLI availability;
- PostgreSQL connectivity;
- database/schema permissions;
- the derived target schema;
- the resolved output directory.

## Repeatable schema behavior

Default schema mode is `recreate`. The target use-case schema is dropped and recreated inside the PostgreSQL transaction only after:

1. the YAML and Phase 1 DDL have parsed;
2. PostgreSQL preflight has passed;
3. the Codex response has passed structural and SQL safety validation.

If the transaction fails, PostgreSQL rolls the DDL and data changes back.

Advanced modes:

```bash
--schema-mode recreate   # default clean repeatable run
--schema-mode reuse      # retain schema, truncate/reload model tables
--schema-mode append     # advanced append behavior
```

The accelerator refuses protected schemas such as `public`, `pg_catalog`, `information_schema`, and names starting with `pg_`.

## Recovery behavior

Phase 2 saves:

- the warehouse prompt;
- the raw Codex response;
- generated SQL;
- a SHA-256 prompt fingerprint.

If the same YAML, DDL, row count, and generation profile are rerun, Phase 2 automatically reuses the matching saved response. This avoids another Codex call when a downstream database or Excel issue is retried.

Force a new Codex response only when required:

```bash
python src/phase2_runner.py \
  --yaml input/air_india_cabin_capacity_optimization.yaml \
  --rows-per-table 15 \
  --force-regenerate
```

## Local Excel-only mode

The normal Codex ELT path uses PostgreSQL because staging, dimension, and fact rows are produced by SQL transformations.

For a local Python-generated workbook without PostgreSQL:

```bash
python src/phase2_runner.py \
  --yaml input/air_india_cabin_capacity_optimization.yaml \
  --rows-per-table 15 \
  --generation-engine python \
  --no-load-to-postgres
```

When `--no-load-to-postgres` is used without specifying an engine, Phase 2 automatically selects the Python engine.

## Permanent fixes included in V3

- Codex works outside a Git repository.
- PostgreSQL is checked before Phase 2 invokes Codex.
- Output folders and schemas are isolated per use case.
- Repeat runs no longer require manual schema drops.
- `REFERENCES schema.table` can infer the referenced primary key.
- PostgreSQL `JOIN LATERAL` functions are not misclassified as tables.
- Nullable FKs follow PostgreSQL `MATCH SIMPLE` behavior.
- UUID, JSON/JSONB, arrays, bytes, enums, timezone-aware values, and decimals are Excel-safe.
- Generated strings beginning with formula characters are escaped before Excel export.
- Matching saved Codex responses are reused automatically.
- Connection settings are loaded from the project `.env` regardless of current working directory.
- Clear per-use-case report paths are written on success and failure.

## Tests

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python -m compileall -q src tests
python -m pytest -q
```

The packaged release is expected to pass the full unit test suite before delivery.

## YAML design

A use-case YAML should describe:

- business name and type;
- business description and model purpose;
- business processes;
- entities and attributes;
- relationships;
- reporting requirements;
- expected outputs.

Dimension and fact table names do not need to be hardcoded in the YAML. Phase 1 infers an appropriate analytical model from the business requirements.
