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
