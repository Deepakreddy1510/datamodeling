# V3 Production Release Manifest

## Normal commands

```bash
python src/main.py --input input/air_india_cabin_capacity_optimization.yaml
python src/phase2_runner.py --yaml input/air_india_cabin_capacity_optimization.yaml --rows-per-table 15
```

## Included production safeguards

- Per-use-case output directory and PostgreSQL schema.
- PostgreSQL preflight before Phase 2 Codex generation.
- Atomic target-schema recreation for repeatable runs.
- No Git repository requirement for Codex CLI.
- Cached Codex-response recovery based on prompt fingerprints.
- Bare PostgreSQL `REFERENCES table` support.
- PostgreSQL `LATERAL` SQL validation support.
- Nullable FK validation aligned with PostgreSQL semantics.
- UUID and complex PostgreSQL value handling for Excel.
- Formula-injection protection in Excel text cells.
- Project-root `.env` loading.
- Protected-schema blocking.
- Corrected Air India input YAML.

## Verification completed

- Python source lint: passed.
- Python compilation: passed.
- Unit/regression tests: 110 passed.
- YAML parsing for Air India input: passed.
- PostgreSQL configuration parsing: passed.

The remote PostgreSQL endpoint and real Codex account are environment-dependent and are therefore checked automatically at runtime by Phase 2 preflight.
