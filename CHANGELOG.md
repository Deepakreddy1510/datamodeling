# Changelog

## 3.0.0

- Added two-command production workflow with per-use-case outputs and schemas.
- Added Codex `--skip-git-repo-check` support for Phase 1 and Phase 2.
- Added PostgreSQL connectivity and privilege preflight before Codex ELT generation.
- Added atomic clean schema recreation for repeatable company runs.
- Added automatic target schema derivation from the business YAML.
- Added prompt-fingerprint caching and automatic retry reuse.
- Added implicit referenced-primary-key inference for bare `REFERENCES table` clauses.
- Fixed PostgreSQL `JOIN LATERAL` validation.
- Fixed nullable foreign-key realism validation.
- Added UUID and PostgreSQL-type Excel normalization and formula-injection protection.
- Added project-root `.env` loading independent of the terminal working directory.
- Added corrected inference-friendly Air India use-case YAML.
- Added setup and standalone deployment preflight scripts.
- Expanded regression coverage to 110 passing tests.
