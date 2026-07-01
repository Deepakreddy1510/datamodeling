import re
import sqlparse

from .models import Column, DDLModel, ForeignKey, Table


class DDLParserError(Exception):
    pass


CREATE_SCHEMA_RE = re.compile(r"CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w\".]+)", re.IGNORECASE)
CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w\".]+)\s*\((.*)\)\s*;?\s*$", re.IGNORECASE | re.DOTALL)
SUPPORTED_TYPE_RE = re.compile(
    r"^(smallint|integer|int|bigint|serial|bigserial|uuid|varchar|character\s+varying|text|date|timestamp(?:\s+with(?:out)?\s+time\s+zone)?|boolean|bool|numeric|decimal|float|double\s+precision)(?:\s*\([^)]*\))?",
    re.IGNORECASE,
)


def _clean_identifier(identifier):
    return identifier.strip().strip('"')


def _split_qualified_name(name):
    parts = [_clean_identifier(part) for part in name.split(".")]
    if len(parts) == 1:
        return None, parts[0]
    if len(parts) == 2:
        return parts[0], parts[1]
    raise DDLParserError(f"Unsupported qualified identifier: {name}")


def _split_top_level_commas(text):
    parts = []
    current = []
    depth = 0
    in_quote = False
    for char in text:
        if char == '"':
            in_quote = not in_quote
        elif not in_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    if current:
        parts.append("".join(current).strip())
    return [part for part in parts if part]


def _parse_column_list(text):
    return [_clean_identifier(item) for item in text.split(",") if item.strip()]


def _parse_references(text):
    match = re.search(r"REFERENCES\s+([\w\".]+)\s*\(([^)]+)\)", text, re.IGNORECASE)
    if not match:
        raise DDLParserError(f"Unsupported REFERENCES clause: {text}")
    _, table_name = _split_qualified_name(match.group(1))
    return table_name, _parse_column_list(match.group(2))


def _parse_table_constraint(part, table):
    text = re.sub(r"^CONSTRAINT\s+[\w\"]+\s+", "", part.strip(), flags=re.IGNORECASE)
    pk_match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", text, re.IGNORECASE)
    if pk_match:
        table.primary_key = _parse_column_list(pk_match.group(1))
        return
    fk_match = re.search(r"FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+([\w\".]+)\s*\(([^)]+)\)", text, re.IGNORECASE)
    if fk_match:
        _, parent_table = _split_qualified_name(fk_match.group(2))
        table.foreign_keys.append(ForeignKey(table.name, _parse_column_list(fk_match.group(1)), parent_table, _parse_column_list(fk_match.group(3))))
        return
    raise DDLParserError(f"Unsupported table constraint: {part}")


def _parse_column(part, table):
    match = re.match(r"([\w\"]+)\s+(.+)$", part.strip(), re.DOTALL)
    if not match:
        raise DDLParserError(f"Unsupported column definition: {part}")
    name = _clean_identifier(match.group(1))
    rest = match.group(2).strip()
    type_match = SUPPORTED_TYPE_RE.match(rest)
    if not type_match:
        raise DDLParserError(f"Unsupported data type for column {name}: {rest}")
    data_type = type_match.group(0).strip()
    constraints = rest[type_match.end():]
    column = Column(
        name=name,
        data_type=data_type,
        nullable=not re.search(r"\bNOT\s+NULL\b", constraints, re.IGNORECASE),
        is_primary_key=bool(re.search(r"\bPRIMARY\s+KEY\b", constraints, re.IGNORECASE)),
    )
    ref_match = re.search(r"\bREFERENCES\b", constraints, re.IGNORECASE)
    if ref_match:
        parent_table, parent_columns = _parse_references(constraints)
        column.references_table = parent_table
        column.references_column = parent_columns[0]
        table.foreign_keys.append(ForeignKey(table.name, [name], parent_table, [parent_columns[0]]))
    if column.is_primary_key:
        table.primary_key.append(name)
        column.nullable = False
    table.columns.append(column)


def parse_ddl(ddl_text):
    model = DDLModel()
    statements = [statement.strip() for statement in sqlparse.split(ddl_text) if statement.strip()]
    for statement in statements:
        schema_match = CREATE_SCHEMA_RE.match(statement)
        if schema_match:
            schema = _clean_identifier(schema_match.group(1))
            if schema.lower() not in [item.lower() for item in model.schemas]:
                model.schemas.append(schema)
            continue

        table_match = CREATE_TABLE_RE.match(statement)
        if table_match:
            schema, table_name = _split_qualified_name(table_match.group(1))
            table = Table(name=table_name, schema=schema)
            for part in _split_top_level_commas(table_match.group(2)):
                normalized = part.strip()
                if re.match(r"^(CONSTRAINT\s+[\w\"]+\s+)?(PRIMARY\s+KEY|FOREIGN\s+KEY)\b", normalized, re.IGNORECASE):
                    _parse_table_constraint(normalized, table)
                else:
                    _parse_column(normalized, table)
            for column in table.columns:
                if column.name in table.primary_key:
                    column.is_primary_key = True
                    column.nullable = False
            if not table.columns:
                raise DDLParserError(f"CREATE TABLE {table.full_name} has no columns.")
            model.tables.append(table)
            continue

        if re.search(r"\bCREATE\b", statement, re.IGNORECASE):
            raise DDLParserError(f"Unsupported DDL statement: {statement[:120]}")
    if not model.tables:
        raise DDLParserError("No CREATE TABLE statements were parsed from DDL.")
    return model
