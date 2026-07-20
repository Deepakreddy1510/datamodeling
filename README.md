# Data Modeling Accelerator

A production-ready, two-phase accelerator that converts a business use-case YAML file into a complete analytical data warehouse.

The accelerator generates:

- Conceptual data models
- Logical data models
- Physical PostgreSQL data models
- Raw or load tables
- Staging tables
- Dimension tables
- Fact tables
- Reporting views
- PostgreSQL DDL scripts
- Relational synthetic data
- PostgreSQL ELT execution
- Data-quality and lineage validation
- PostgreSQL readback validation
- Formatted Excel workbooks
- Generation, validation, and database load reports

The implementation is generic. Models, tables, relationships, synthetic data, and transformation logic are derived from the supplied YAML and generated DDL rather than from hardcoded use-case-specific rules.

---

## Table of Contents

1. [How the Accelerator Works](#how-the-accelerator-works)
2. [Prerequisites](#prerequisites)
3. [Clone the Repository](#clone-the-repository)
4. [Create the Python Environment](#create-the-python-environment)
5. [Configure PostgreSQL](#configure-postgresql)
6. [Prepare the Business YAML](#prepare-the-business-yaml)
7. [Run the Preflight Check](#run-the-preflight-check)
8. [Run Phase 1](#run-phase-1)
9. [Review Phase 1 Output](#review-phase-1-output)
10. [Run Phase 2](#run-phase-2)
11. [Review Phase 2 Output](#review-phase-2-output)
12. [Output Folder Structure](#output-folder-structure)
13. [PostgreSQL Schema Behaviour](#postgresql-schema-behaviour)
14. [Recovery and Response Reuse](#recovery-and-response-reuse)
15. [Local Excel-Only Mode](#local-excel-only-mode)
16. [Validation](#validation)
17. [Running Tests](#running-tests)
18. [Troubleshooting](#troubleshooting)
19. [Security Guidelines](#security-guidelines)
20. [Success Criteria](#success-criteria)
21. [Quick Command Reference](#quick-command-reference)

---

## How the Accelerator Works

The accelerator follows a two-phase workflow.

### Phase 1: Data Model Generation

Phase 1 reads the business YAML file and generates:

- Conceptual model
- Logical model
- Physical PostgreSQL model
- Table definitions
- Relationships
- Constraints
- Raw or load layer
- Staging layer
- Dimension layer
- Fact layer
- Reporting views
- PostgreSQL DDL
- Generation-quality report

### Phase 2: Synthetic Data, ELT, Validation, and Excel

Phase 2 reads:

- The original business YAML
- The Phase 1 generated model
- The PostgreSQL DDL

It then performs:

1. PostgreSQL connectivity checks
2. Synthetic data generation
3. Raw or load table population
4. Staging transformations
5. Dimension loading
6. Fact loading
7. Reporting-view creation
8. Foreign-key validation
9. Constraint validation
10. Lineage validation
11. Calculation validation
12. Date validation
13. Realism validation
14. PostgreSQL readback
15. Excel workbook generation
16. Validation-report generation

The complete workflow is:

```text
Business YAML
    ↓
Phase 1 model generation
    ↓
Conceptual, logical, and physical models
    ↓
PostgreSQL DDL
    ↓
Phase 2 synthetic data generation
    ↓
Raw or load tables
    ↓
Staging tables
    ↓
Dimension and fact tables
    ↓
Reporting views
    ↓
PostgreSQL validation
    ↓
Excel workbook from PostgreSQL readback
```

---

## Prerequisites

The recommended environment is:

- Windows with Ubuntu WSL
- Ubuntu or another supported Linux distribution
- macOS
- Visual Studio Code
- Git
- Python 3
- Python virtual environment support
- Codex CLI
- PostgreSQL access

Verify the required tools:

```bash
git --version
python3 --version
codex --version
```

Codex CLI must be installed and authenticated before running the accelerator in Codex mode.

No `git init` command is required. The accelerator invokes Codex with Git repository checks disabled where supported by the project configuration.

---

## Clone the Repository

Define the repository information:

```bash
REPOSITORY_URL="https://github.com/organization-name/repository-name.git"
BRANCH_NAME="branch-name"
PROJECT_DIR="datamodeling-accelerator"
```

Clone the required branch:

```bash
mkdir -p ~/projects
cd ~/projects

git clone \
  --branch "$BRANCH_NAME" \
  "$REPOSITORY_URL" \
  "$PROJECT_DIR"
```

Enter the project folder:

```bash
cd "$PROJECT_DIR"
```

Verify the current location and branch:

```bash
pwd
git branch --show-current
```

Expected project path format:

```text
/home/username/projects/datamodeling-accelerator
```

---

## Open the Project in Visual Studio Code

From the project directory:

```bash
code . -r
```

When using Windows with WSL, confirm that Visual Studio Code shows:

```text
WSL: Ubuntu
```

The terminal should use a Linux path similar to:

```text
username@computer-name:~/projects/datamodeling-accelerator$
```

If the terminal opens in a Windows directory, return to the project:

```bash
cd ~/projects/datamodeling-accelerator
```

---

## Create the Python Environment

### Automated setup

If the repository contains `setup.sh`, run:

```bash
chmod +x setup.sh
./setup.sh
source .venv/bin/activate
```

### Manual setup

Create the virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Upgrade `pip`:

```bash
python -m pip install --upgrade pip
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Set the Python source path:

```bash
export PYTHONPATH="$PWD/src"
```

If Codex CLI is installed in a user-level npm directory, add it to `PATH`:

```bash
export PATH="$HOME/.npm-global/bin:$PATH"
```

Verify the environment:

```bash
pwd
python --version
which python
which codex
codex --version
echo "$PYTHONPATH"
git branch --show-current
```

The Python path should point to the project virtual environment:

```text
.../datamodeling-accelerator/.venv/bin/python
```

---

## Configure PostgreSQL

The project should provide an example environment file:

```text
.env.example
```

Create a local `.env` file:

```bash
cp .env.example .env
```

Update `.env` with the approved PostgreSQL connection details:

```text
POSTGRES_HOST=database-host
POSTGRES_PORT=5432
POSTGRES_DB=database-name
POSTGRES_USER=database-user
POSTGRES_PASSWORD=database-password
POSTGRES_SSLMODE=prefer
POSTGRES_CONNECT_TIMEOUT=15
```

A secure terminal-based method can also be used:

```bash
read -s -p "PostgreSQL password: " PG_PASS
echo

cat > .env <<EOF
POSTGRES_HOST=database-host
POSTGRES_PORT=5432
POSTGRES_DB=database-name
POSTGRES_USER=database-user
POSTGRES_PASSWORD=$PG_PASS
POSTGRES_SSLMODE=prefer
POSTGRES_CONNECT_TIMEOUT=15
EOF

unset PG_PASS
echo ".env created"
```

The `.env` file must remain local and must not be committed to Git.

---

## PostgreSQL Environment Variables

| Variable | Required | Description |
|---|---:|---|
| `POSTGRES_HOST` | Yes | PostgreSQL server hostname |
| `POSTGRES_PORT` | Yes | PostgreSQL server port |
| `POSTGRES_DB` | Yes | Target database name |
| `POSTGRES_USER` | Yes | Database username |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `POSTGRES_SSLMODE` | No | PostgreSQL SSL mode; defaults to `prefer` |
| `POSTGRES_CONNECT_TIMEOUT` | No | Connection timeout in seconds |

The normal runner derives the target schema from the YAML `business_name`.

For example:

```text
Business name from YAML
    ↓
Normalized PostgreSQL-safe schema name
```

The schema name is converted to lowercase snake case and isolated from other use cases.

An approved schema can be supplied explicitly:

```bash
--target-schema approved_schema_name
```

---

## Prepare the Business YAML

Business YAML files are stored under:

```text
input/
```

Recommended naming format:

```text
input/use_case_name.yaml
```

A use-case YAML should describe:

- Business name
- Business type
- Business description
- Model purpose
- Main business processes
- Business entities
- Entity attributes
- Relationships
- Business rules
- Reporting requirements
- Synthetic-data requirements
- Expected outputs

Example structure:

```yaml
business_name: Generic Business Use Case

business_type: Business Domain

target_database: PostgreSQL

business_description: >
  Describe the business operation, the data being captured,
  and the business decisions supported by the model.

model_purpose: >
  Describe what the analytical model must help users understand.

main_business_processes:
  - Business process one
  - Business process two
  - Business process three

key_business_entities:
  - entity_name: Primary Entity
    description: Description of the entity.
    attributes:
      - primary_entity_id
      - entity_name
      - entity_status
      - created_date

business_relationships:
  - parent_entity: Primary Entity
    child_entity: Related Entity
    relationship_type: one-to-many

business_rules:
  - A required business rule.
  - Another required business rule.

reporting_requirements:
  - Operational reporting requirement
  - Analytical reporting requirement
  - Executive reporting requirement

synthetic_data:
  rows_per_table: 10
  realistic_values: true
  avoid_placeholders: true

expected_output:
  - conceptual_model
  - logical_model
  - physical_model
  - postgresql_ddl
  - synthetic_data
  - excel_output
  - postgresql_load
```

Dimension and fact table names do not need to be manually hardcoded in the YAML. Phase 1 derives an appropriate analytical design from the business requirements.

---

## Define the Use-Case Variable

To avoid repeating the YAML name in every command:

```bash
USE_CASE="use_case_name"
```

The corresponding YAML file should be:

```text
input/use_case_name.yaml
```

---

## Run the Preflight Check

Run the standalone preflight command before Phase 1:

```bash
PYTHONPATH=src python scripts/preflight.py \
  --yaml "input/${USE_CASE}.yaml"
```

The preflight check validates:

- YAML file existence
- YAML readability
- YAML structure
- Required environment configuration
- Codex CLI availability
- PostgreSQL connectivity
- Database permissions
- Schema permissions
- Derived schema name
- Output directory resolution

Phase 2 also performs its own PostgreSQL preflight automatically.

---

## Run Phase 1

Phase 1 generates the data model.

```bash
python src/main.py \
  --input "input/${USE_CASE}.yaml"
```

Before rerunning Phase 1, remove the previous use-case output when a clean run is required:

```bash
rm -rf "output/${USE_CASE}"
```

Then run Phase 1 again:

```bash
python src/main.py \
  --input "input/${USE_CASE}.yaml"
```

A successful Phase 1 run creates an output directory under:

```text
output/<business_name_slug>/
```

---

## Review Phase 1 Output

Find the most recent Phase 1 output directory:

```bash
OUTPUT_DIR="$(
  dirname "$(
    find output \
      -maxdepth 2 \
      -name final_output.md \
      -printf '%T@ %p\n' \
      | sort -nr \
      | head -1 \
      | cut -d' ' -f2-
  )"
)"
```

Display the resolved directory:

```bash
echo "$OUTPUT_DIR"
```

List its files:

```bash
ls -lh "$OUTPUT_DIR"
```

Important Phase 1 files include:

```text
final_output.md
generation_quality_report.md
```

### `final_output.md`

Contains the generated:

- Conceptual model
- Logical model
- Physical model
- PostgreSQL DDL
- Raw or load tables
- Staging tables
- Dimensions
- Facts
- Reporting views
- Relationships
- Constraints

### `generation_quality_report.md`

Validates whether the generated model includes the required warehouse layers and structures.

Review it for:

```text
Final status: passed
```

---

## Verify the Generated Warehouse Layers

Check for raw or load tables:

```bash
grep -RinE \
  "create table.*load_|load_.*_raw|load_" \
  "$OUTPUT_DIR" \
  | head -30
```

Check for staging tables:

```bash
grep -RinE \
  "create table.*stg_|stg_" \
  "$OUTPUT_DIR" \
  | head -30
```

Check for dimensions:

```bash
grep -RinE \
  "create table.*dim_|dim_" \
  "$OUTPUT_DIR" \
  | head -30
```

Check for facts:

```bash
grep -RinE \
  "create table.*fact_|fact_" \
  "$OUTPUT_DIR" \
  | head -30
```

Check for reporting views:

```bash
grep -RinE \
  "create.*view|reporting" \
  "$OUTPUT_DIR" \
  | head -30
```

Expected warehouse flow:

```text
load_*_raw
    ↓
stg_*
    ↓
dim_* and fact_*
    ↓
reporting views
```

---

## Run Phase 2

Phase 2 generates data, executes the ELT workflow, validates PostgreSQL, and creates the Excel workbook.

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15
```

Replace `15` with the required number of base rows.

Example:

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 100
```

Phase 2 automatically locates the matching Phase 1 `final_output.md`.

For normal execution, these arguments are not required:

```text
--phase1-output
--output-dir
--excel-output
```

A successful run should report that:

- The PostgreSQL transaction was committed
- Validation passed
- The Excel workbook was written from PostgreSQL readback data

---

## Phase 2 Default Behaviour

Phase 2 performs the following automatically:

- Loads project configuration from `.env`
- Finds the matching Phase 1 output
- Runs PostgreSQL preflight
- Derives an isolated target schema
- Validates generated SQL safety
- Recreates or prepares the target schema
- Creates missing database objects
- Inserts raw or load data
- Executes staging SQL
- Executes dimension SQL
- Executes fact SQL
- Creates reporting views
- Reads data back from PostgreSQL
- Validates table counts
- Validates foreign keys
- Validates constraints
- Validates lineage
- Validates calculations
- Validates dates
- Validates data realism
- Generates the Excel workbook
- Writes detailed reports

---

## Review Phase 2 Output

Search the generated reports:

```bash
grep -inE \
  "final status|transaction status|passed|failed|error|warning|lineage|excel written|committed|rolled_back" \
  "$OUTPUT_DIR/validation_report.md" \
  "$OUTPUT_DIR/postgres_load_report.md" \
  "$OUTPUT_DIR/synthetic_data_generation_report.md"
```

Expected successful results include:

```text
Final status: passed
Transaction status: committed
Lineage validation: passed
Excel written
```

Investigate results containing:

```text
failed
error
warning
rolled_back
lineage failed
missing
duplicate
not present
constraint
value too long
```

---

## Output Folder Structure

Outputs are isolated by use case:

```text
output/<business_name_slug>/
```

Typical output structure:

```text
output/<business_name_slug>/
├── final_output.md
├── generation_quality_report.md
├── validation_report.md
├── postgres_load_report.md
├── synthetic_data_generation_report.md
├── <business_name_slug>_synthetic_data.xlsx
└── codex_generated_data/
```

Additional generated files may include:

```text
codex_generated_data/
├── warehouse_prompt.md
├── codex_response_raw.txt
├── generated_sql.json
├── generated_data.json
└── prompt_fingerprint.txt
```

---

## Output File Descriptions

### `final_output.md`

Contains the complete generated data model and PostgreSQL DDL.

### `generation_quality_report.md`

Checks whether Phase 1 generated the required model components and warehouse layers.

### `validation_report.md`

Contains validation results for:

- Data types
- Foreign keys
- Constraints
- Duplicate keys
- Missing values
- Lineage
- Calculations
- Date logic
- Fact and dimension relationships
- Row counts
- Data realism

### `postgres_load_report.md`

Contains:

- Target schema
- Created tables
- Loaded tables
- Inserted row counts
- Transaction status
- Database errors
- Commit or rollback status

### `synthetic_data_generation_report.md`

Contains:

- Synthetic-data generation status
- Tables generated
- Row counts
- Generation warnings
- Validation findings

### Excel workbook

Contains data generated and read back from PostgreSQL after ELT execution.

---

## Find the Excel Workbook

```bash
find "$OUTPUT_DIR" \
  -maxdepth 1 \
  -type f \
  -name "*.xlsx" \
  -printf '%p  %s bytes\n'
```

When using WSL, copy the workbook to Windows Downloads:

```bash
WINDOWS_USERNAME="username"

mkdir -p "/mnt/c/Users/${WINDOWS_USERNAME}/Downloads/data_model_outputs"

cp "$OUTPUT_DIR"/*.xlsx \
  "/mnt/c/Users/${WINDOWS_USERNAME}/Downloads/data_model_outputs/"
```

Open the folder in Windows Explorer:

```bash
explorer.exe "C:\\Users\\${WINDOWS_USERNAME}\\Downloads\\data_model_outputs"
```

The WSL output directory can also be opened using:

```bash
explorer.exe "$(wslpath -w "$OUTPUT_DIR")"
```

---

## PostgreSQL Schema Behaviour

The default schema mode is:

```text
recreate
```

The target schema is derived from the YAML `business_name`.

Before the target schema is recreated, the accelerator confirms that:

1. The YAML can be parsed
2. The Phase 1 output can be parsed
3. PostgreSQL preflight passes
4. The Codex response passes structural validation
5. Generated SQL passes safety validation

Schema and data changes occur inside a PostgreSQL transaction.

If execution fails, PostgreSQL rolls back the transaction.

### Available schema modes

```bash
--schema-mode recreate
```

Drops and recreates the isolated use-case schema inside the transaction.

```bash
--schema-mode reuse
```

Retains the schema and reloads the relevant model tables.

```bash
--schema-mode append
```

Uses advanced append behaviour where supported.

### Protected schemas

The accelerator refuses unsafe or protected schemas such as:

```text
public
pg_catalog
information_schema
```

It also rejects schema names beginning with:

```text
pg_
```

---

## Use an Explicit Approved Schema

When an explicitly approved schema is required:

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15 \
  --target-schema approved_schema_name
```

Use this option only when the schema has been reviewed and approved.

---

## Recovery and Response Reuse

Phase 2 stores information required for safe retries:

- Warehouse-generation prompt
- Raw Codex response
- Generated SQL
- Generated data
- Prompt fingerprint
- YAML and DDL context
- Generation profile
- Row-count configuration

A SHA-256 fingerprint is used to identify unchanged generation requests.

When the following inputs remain unchanged:

- Business YAML
- Phase 1 DDL
- Requested row count
- Generation profile

Phase 2 can reuse the matching saved Codex response.

This avoids unnecessary regeneration when retrying after:

- Database connectivity failures
- PostgreSQL permission issues
- Excel-generation issues
- Temporary downstream failures

Force a new Codex response only when required:

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15 \
  --force-regenerate
```

---

## Local Excel-Only Mode

The normal Codex ELT path uses PostgreSQL because staging, dimension, and fact rows are produced using SQL transformations.

For local Python-generated data without PostgreSQL:

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15 \
  --generation-engine python \
  --no-load-to-postgres
```

When `--no-load-to-postgres` is supplied without an explicit generation engine, Phase 2 may automatically select the Python generation engine based on the current implementation.

Excel-only mode is useful for:

- Local demonstrations
- YAML testing
- Early model inspection
- Environments without database access

Excel-only mode does not validate the complete PostgreSQL ELT workflow.

---

## Verify PostgreSQL Tables

Use the following script to list tables and row counts.

Set the schema first:

```bash
TARGET_SCHEMA="approved_schema_name"
```

Run:

```bash
python - <<'PY'
from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(".env"), override=True)

schema = os.environ.get("TARGET_SCHEMA", "approved_schema_name")

connection = psycopg.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
    connect_timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "15")),
)

try:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (schema,),
        )

        tables = [row[0] for row in cursor.fetchall()]

        print(f"Schema: {schema}")
        print(f"Table count: {len(tables)}")
        print()

        for table in tables:
            qualified_table = (
                f'"{schema.replace(chr(34), chr(34) * 2)}".'
                f'"{table.replace(chr(34), chr(34) * 2)}"'
            )
            cursor.execute(f"SELECT COUNT(*) FROM {qualified_table}")
            row_count = cursor.fetchone()[0]
            print(f"{table}: {row_count} rows")
finally:
    connection.close()
PY
```

Alternatively, export the schema before running:

```bash
export TARGET_SCHEMA="approved_schema_name"
```

---

## Validation

The accelerator validates the complete warehouse pipeline.

### Structural validation

Checks:

- Required Phase 1 sections
- Valid DDL structure
- Required warehouse layers
- Table definitions
- Primary keys
- Foreign keys
- Reporting objects

### SQL safety validation

Checks generated SQL before database execution.

Unsafe or invalid SQL is rejected before schema recreation.

### Foreign-key validation

Checks:

- Referenced tables
- Referenced columns
- Parent-key existence
- Child-key values
- Nullable relationships
- PostgreSQL `MATCH SIMPLE` behaviour

### Lineage validation

Checks that:

- Staging data comes from approved raw or load sources
- Dimensions come from approved upstream layers
- Facts come from approved staging or dimension sources
- Generated values can be traced through the warehouse

### Calculation validation

Checks:

- Derived values
- Aggregations
- Amount calculations
- Quantities
- Totals
- Business-rule calculations

### Date validation

Checks:

- Start and completion dates
- Effective date ranges
- Expiry dates
- Transaction dates
- Future and past date consistency

### Realism validation

Checks for:

- Placeholder values
- Repeated unrealistic values
- Invalid status combinations
- Invalid date combinations
- Inconsistent business relationships
- Unreasonable numeric values

### Excel safety

The workbook writer safely handles:

- UUID values
- JSON and JSONB values
- PostgreSQL arrays
- Byte values
- Enums
- Decimal values
- Timezone-aware dates
- Formula-like string prefixes

Generated strings beginning with spreadsheet formula characters are escaped before Excel export.

---

## Running Tests

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Set the source path:

```bash
export PYTHONPATH="$PWD/src"
```

Compile the source and test files:

```bash
python -m compileall -q src tests
```

Run the complete test suite:

```bash
python -m pytest -q
```

Run tests with verbose output:

```bash
python -m pytest -v
```

The release should pass the complete test suite before deployment or delivery.

---

## Troubleshooting

### `source` or `export` is not recognized

Cause:

The command is being run in Windows Command Prompt or PowerShell instead of Linux or WSL.

Fix:

```bash
wsl -d Ubuntu
cd ~/projects/datamodeling-accelerator
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
```

---

### Terminal starts in `/mnt/c/Windows`

Cause:

The WSL terminal opened from a Windows directory.

Fix:

```bash
cd ~/projects/datamodeling-accelerator
```

---

### `externally-managed-environment`

Cause:

Dependencies are being installed globally instead of inside a virtual environment.

Fix:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Do not use:

```text
--break-system-packages
```

---

### `ModuleNotFoundError`

Cause:

The virtual environment is inactive, a dependency is missing, or `PYTHONPATH` is not configured.

Fix:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
```

Verify:

```bash
which python
echo "$PYTHONPATH"
```

---

### Codex CLI is unavailable

Check:

```bash
which codex
codex --version
```

If the executable is installed under a user npm directory:

```bash
export PATH="$HOME/.npm-global/bin:$PATH"
```

Authenticate Codex CLI before running the accelerator.

---

### Phase 1 quality validation fails

Possible cause:

The generated model is missing a required warehouse layer.

Check:

```bash
cat "$OUTPUT_DIR/generation_quality_report.md"
```

Verify that the YAML clearly requests:

- Raw or load tables
- Staging tables
- Dimensions
- Facts
- Reporting views
- PostgreSQL DDL
- Relationships and constraints

Then rerun Phase 1.

---

### Raw or load tables are missing

Check:

```bash
grep -RinE \
  "create table.*load_|load_.*_raw|load_" \
  "$OUTPUT_DIR"
```

The expected flow is:

```text
raw or load → staging → dimensions and facts → reporting
```

Update the YAML requirements if the raw or load layer is not clearly requested.

---

### PostgreSQL connection fails

Verify `.env`:

```bash
grep -E \
  "POSTGRES_HOST|POSTGRES_PORT|POSTGRES_DB|POSTGRES_USER|POSTGRES_SSLMODE" \
  .env
```

Do not print the database password.

Check:

- Hostname
- Port
- Database
- Username
- Network access
- VPN requirements
- Firewall rules
- SSL mode
- Database permissions

---

### Phase 2 validation fails

Search the reports:

```bash
grep -inE \
  "failed|error|warning|lineage|missing|duplicate|not present|constraint|value too long|rolled_back" \
  "$OUTPUT_DIR/validation_report.md" \
  "$OUTPUT_DIR/postgres_load_report.md" \
  "$OUTPUT_DIR/synthetic_data_generation_report.md"
```

Common causes include:

- Invalid SQL
- Missing source tables
- Incorrect lineage
- Duplicate business keys
- Missing foreign-key parents
- Invalid date ordering
- String values longer than the target column
- Invalid calculations
- Fact and dimension mismatch
- PostgreSQL constraint violations

---

### Excel workbook is not generated

Search for workbooks:

```bash
find output \
  -maxdepth 3 \
  -type f \
  -name "*.xlsx" \
  -printf '%p  %s bytes\n'
```

If no workbook exists, inspect:

```text
validation_report.md
postgres_load_report.md
synthetic_data_generation_report.md
```

The Excel workbook is normally generated only after successful PostgreSQL readback.

---

### Output is not visible in Windows

The project output is stored inside WSL.

Open it with:

```bash
explorer.exe "$(wslpath -w "$PWD/output")"
```

---

### Transaction was rolled back

A rollback means PostgreSQL did not commit the schema or data changes.

Inspect:

```bash
cat "$OUTPUT_DIR/postgres_load_report.md"
```

Correct the reported issue and rerun Phase 2.

When the prompt fingerprint still matches, the accelerator may reuse the existing Codex response automatically.

---

## Security Guidelines

Never commit:

```text
.env
.env.*
.venv/
output/
*.xlsx
*.xls
*.csv
database passwords
access tokens
API keys
generated business data
```

Recommended `.gitignore` entries:

```gitignore
# Python
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/

# Environment files
.env
.env.*
!.env.example

# Generated output
output/
*.xlsx
*.xls
*.csv

# Operating-system files
.DS_Store
Thumbs.db

# Editor files
.vscode/
.idea/
```

Before committing, check for sensitive or generated files:

```bash
git diff --cached --name-only \
  | grep -E '(^|/)(\.env|\.venv|venv|output|.*\.xlsx|.*\.xls|.*\.csv)$' \
  && echo "STOP: sensitive or generated file is staged" \
  || echo "OK: no obvious sensitive or generated files are staged"
```

Rotate credentials that have been exposed through:

- Chat messages
- Terminal output
- Terminal history
- Email
- Tickets
- Screenshots
- Demo recordings
- Committed files

Do not display `.env` while recording a demonstration.

---

## Recommended User Workflow

A new user should follow this order:

1. Clone the approved repository branch
2. Open the project in WSL or Linux
3. Create and activate `.venv`
4. Install dependencies
5. Configure `.env`
6. Create or select the business YAML
7. Run preflight
8. Run Phase 1
9. Review `generation_quality_report.md`
10. Review `final_output.md`
11. Run Phase 2
12. Review all validation reports
13. Confirm the PostgreSQL transaction was committed
14. Confirm tables contain rows
15. Confirm the Excel workbook exists
16. Use the generated warehouse for reporting or AI-agent analytics

---

## Success Criteria

The accelerator run is successful when:

- The YAML passes preflight validation
- Codex CLI is available
- PostgreSQL connectivity passes
- Phase 1 completes successfully
- `final_output.md` is created
- `generation_quality_report.md` passes
- Raw or load tables are present
- Staging tables are present
- Dimension tables are present
- Fact tables are present
- Reporting views are present
- Phase 2 completes successfully
- PostgreSQL transaction status is `committed`
- `validation_report.md` passes
- `synthetic_data_generation_report.md` passes
- `postgres_load_report.md` confirms successful loading
- PostgreSQL tables contain rows
- The Excel workbook is created from PostgreSQL readback

---

## Quick Command Reference

### Enter the project

```bash
cd ~/projects/datamodeling-accelerator
```

### Activate the environment

```bash
source .venv/bin/activate
```

### Configure the source path

```bash
export PYTHONPATH="$PWD/src"
```

### Define the use case

```bash
USE_CASE="use_case_name"
```

### Run preflight

```bash
PYTHONPATH=src python scripts/preflight.py \
  --yaml "input/${USE_CASE}.yaml"
```

### Run Phase 1

```bash
python src/main.py \
  --input "input/${USE_CASE}.yaml"
```

### Run Phase 2

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15
```

### Force regeneration

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15 \
  --force-regenerate
```

### Run without PostgreSQL

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15 \
  --generation-engine python \
  --no-load-to-postgres
```

### Run tests

```bash
python -m compileall -q src tests
python -m pytest -q
```

### Find generated Excel files

```bash
find output \
  -maxdepth 3 \
  -type f \
  -name "*.xlsx" \
  -printf '%p  %s bytes\n'
```

### Open the output folder from WSL

```bash
explorer.exe "$(wslpath -w "$PWD/output")"
```

---

## Summary

The Data Modeling Accelerator converts a structured business YAML file into a complete PostgreSQL analytical warehouse.

It provides:

- AI-assisted data-model generation
- Generic business-domain support
- Raw-to-staging-to-warehouse transformations
- Synthetic relational data
- PostgreSQL ELT execution
- Isolated schemas per use case
- Transactional database loading
- Data-quality validation
- Lineage validation
- Calculation and date validation
- PostgreSQL readback
- Excel workbook generation
- Recovery and response reuse
- Detailed operational reports

The recommended execution environment is:

```text
Visual Studio Code
    +
Ubuntu WSL, Linux, or macOS
    +
Python virtual environment
    +
Codex CLI
    +
PostgreSQL
```

The standard user workflow requires two primary commands after setup:

```bash
python src/main.py \
  --input "input/${USE_CASE}.yaml"
```

```bash
python src/phase2_runner.py \
  --yaml "input/${USE_CASE}.yaml" \
  --rows-per-table 15
```
