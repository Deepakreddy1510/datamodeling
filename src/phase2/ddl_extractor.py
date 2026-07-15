import re

try:
    import sqlparse
except ImportError:  # pragma: no cover - exercised when optional dependency is unavailable
    sqlparse = None


class DDLExtractionError(Exception):
    pass


SQL_FENCE_RE = re.compile(r"```(?:sql|postgresql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
DDL_START_RE = re.compile(r"\bCREATE\s+(?:SCHEMA|TABLE)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)
SQL_DDL_HEADING_RE = re.compile(r"^#{1,6}\s+.*(?:SQL\s+DDL|PostgreSQL\s+DDL|Physical\s+DDL).*$", re.IGNORECASE | re.MULTILINE)


def _split_sql_statements(text):
    if sqlparse is not None:
        return sqlparse.split(text)
    statements = []
    current = []
    depth = 0
    in_quote = False
    for char in text:
        if char == "'":
            in_quote = not in_quote
        elif not in_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == ";" and depth == 0:
                statements.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    if current and "".join(current).strip():
        statements.append("".join(current).strip())
    return statements


def extract_ddl(markdown_text):
    candidates = []
    for match in SQL_FENCE_RE.finditer(markdown_text):
        block = match.group(1).strip()
        if DDL_START_RE.search(block):
            candidates.append(block)

    if not candidates:
        heading = SQL_DDL_HEADING_RE.search(markdown_text)
        if heading:
            start = heading.end()
            next_heading = HEADING_RE.search(markdown_text, start)
            section = markdown_text[start: next_heading.start() if next_heading else len(markdown_text)]
            if DDL_START_RE.search(section):
                candidates.append(section.strip())

    if not candidates and DDL_START_RE.search(markdown_text):
        candidates.append(markdown_text)

    statements = []
    for candidate in candidates:
        for statement in _split_sql_statements(candidate):
            cleaned = statement.strip()
            if DDL_START_RE.search(cleaned):
                statements.append(cleaned if cleaned.endswith(";") else cleaned + ";")

    if not statements:
        raise DDLExtractionError("No CREATE SCHEMA or CREATE TABLE DDL statements found in Phase 1 output.")
    return "\n\n".join(statements)
