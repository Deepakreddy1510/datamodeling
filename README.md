<<<<<<< HEAD
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
=======
# AI Data Model Accelerator MVP

A simple file-based accelerator that turns a business YAML input into scored readiness outputs and, when ready, a generated data model through Codex CLI.

## What This MVP Uses

- YAML input
- Python CLI
- PyYAML
- Codex CLI execution with `codex exec -`
- Markdown prompt templates
- JSON output files
- Markdown reports

## What This MVP Does Not Use

- No frontend
- No database
- No OpenAI API key
- No direct OpenAI API call
- No `openai` Python package
- No `.env` API-key handling

## Requirement

Codex CLI must be installed and authenticated before running real Codex mode.

## Setup: Windows

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy input\business_input_sample.yaml input\business_input.yaml
python src\main.py --input input\business_input.yaml
```

## Setup: Mac/Linux

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp input/business_input_sample.yaml input/business_input.yaml
python src/main.py --input input/business_input.yaml
```

## Input Files

`input/business_input_sample.yaml` is committed as a starter template.

Copy it to `input/business_input.yaml` before running. The real input file is ignored by Git because it may contain business-specific information.

## Run Commands

Real Codex CLI mode:

```bash
python src/main.py --input input/business_input.yaml
```

Optional output directory:

```bash
python src/main.py --input input/business_input.yaml --output-dir output
```

Provider option, only `codex_cli` is supported:

```bash
python src/main.py --input input/business_input.yaml --provider codex_cli
```

If `--provider openai` is used, the program stops with:

```text
OpenAI provider is not implemented in this MVP. Use --provider codex_cli.
```

## Mock Codex Testing

Mock mode does not call real Codex CLI.

Below-90 branch:

```bash
python src/main.py --input input/business_input.yaml --mock-codex --mock-ai-score 60
```

Above-90 branch:

```bash
python src/main.py --input input/business_input.yaml --mock-codex --mock-ai-score 100
```

Default mock score:

```bash
python src/main.py --input input/business_input.yaml --mock-codex --mock-ai-score 86
```

## Clean Output Behavior

The CLI safely removes only known generated output files before each run to prevent stale files such as an old `final_output.md` from confusing users.

Supported flag:

```bash
python src/main.py --input input/business_input.yaml --clean-output
```

Cleaning is enabled by default for the known generated output files.

## Generated Output Files

Created as applicable under `output/`:

- `input.json`
- `rule_based_score.json`
- `codex_semantic_review_prompt.md`
- `codex_semantic_review_response_raw.txt`
- `codex_semantic_review_response.json`
- `final_readiness_score.json`
- `improvement_suggestions.md`
- `codex_generation_prompt.md`
- `codex_generation_response_raw.txt`
- `codex_generation_response.json`
- `final_output.md`
- `validation_errors.json`
- `validation_errors.md`
- `error.json`

## Scoring Formula

Python calculates the final score:

```text
final_score = 0.70 * rule_based_score + 0.30 * ai_review_score
```

Decision logic:

```text
final_score >= 90 => ready_for_generation
final_score < 90  => needs_improvement
```

Codex does not decide the final score.

## AI Additions / Assumptions Rule

`final_output.md` must always contain:

```markdown
# AI Additions / Assumptions
```

If Codex does not return this section, Python appends:

```markdown
# AI Additions / Assumptions

No AI additions section was returned by Codex.
```

## Negative Validation Test

If required fields are missing, the pipeline stops before Codex execution and writes both:

- `output/validation_errors.json`
- `output/validation_errors.md`

The Markdown file is intended for human-readable review and includes the invalid fields, issues, and next step command.

## Troubleshooting

- Missing input file: copy the sample YAML to `input/business_input.yaml`.
- Empty YAML file: add required business fields.
- Invalid YAML syntax: fix indentation and YAML formatting.
- Missing required fields: inspect `output/validation_errors.json` and `output/validation_errors.md`.
- Codex CLI not installed/authenticated: install and authenticate Codex CLI before real mode.
- Codex CLI non-zero exit: inspect terminal stderr and `output/error.json`.
- Invalid Codex JSON: raw output is saved before parsing for debugging.

## Phase 2 Synthetic Data and PostgreSQL Load

Phase 2 is a separate command that runs after Phase 1 has generated a data model markdown file. It reads the business YAML and the Phase 1 output, extracts PostgreSQL DDL, generates safe synthetic data, writes the same generated data to Excel, and optionally loads it into PostgreSQL.

Phase 2 does **not** change or replace the existing Phase 1 command. A combined Phase 1 + Phase 2 command can be added later after Phase 2 is stable.

### Phase 2 Dry Run

Dry run generates Excel and markdown reports, but does not connect to PostgreSQL:

```bash
python src/phase2_runner.py --yaml input/business_input.yaml --phase1-output output/final_output.md --rows-per-table 100 --excel-output output/synthetic_data_output.xlsx --no-load-to-postgres
```

If `output/final_output.md` is missing and no explicit Phase 1 output path is supplied, Phase 2 falls back to `output/output.md`.

### Phase 2 PostgreSQL Load

```bash
python src/phase2_runner.py --yaml input/business_input.yaml --phase1-output output/final_output.md --rows-per-table 100 --excel-output output/synthetic_data_output.xlsx --load-to-postgres --create-schema-if-missing --create-tables-if-missing
```

### Required PostgreSQL Environment Variables

Use environment variables or a local `.env` file. Do not hardcode database credentials.

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=datamodeling
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_TARGET_SCHEMA=your_approved_schema
POSTGRES_SSLMODE=prefer
```

`POSTGRES_SSLMODE` is optional and defaults to `prefer`.

### Phase 2 Output Files

Created under `output/` by default:

- `synthetic_data_output.xlsx`
- `synthetic_data_generation_report.md`
- `postgres_load_report.md`
- `validation_report.md`

### Phase 2 Safety Notes

- PostgreSQL loading only happens when `--load-to-postgres` is passed.
- Phase 2 refuses to load into the `public` schema.
- `POSTGRES_TARGET_SCHEMA` is required for PostgreSQL loading.
- Phase 2 does not drop tables.
- Phase 2 does not truncate tables unless `--truncate-before-load` is explicitly passed.
- Phase 2 does not insert into non-empty tables unless `--allow-insert-into-nonempty-tables` is passed.
- Phase 2 does not create schemas unless `--create-schema-if-missing` is passed.
- Phase 2 does not create tables unless `--create-tables-if-missing` is passed.
- PostgreSQL loads use transactions and roll back on failure.
- Generated data is fake synthetic data only.
>>>>>>> personal/main
