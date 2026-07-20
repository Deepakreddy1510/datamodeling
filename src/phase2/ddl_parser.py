<<<<<<< HEAD
import copy
=======
>>>>>>> personal/main
import re

try:
    import sqlparse
except ImportError:  # pragma: no cover - exercised when optional dependency is unavailable
    sqlparse = None

from .models import CheckConstraint, Column, DDLModel, ForeignKey, Table, UniqueConstraint


class DDLParserError(Exception):
    pass


CREATE_SCHEMA_RE = re.compile(r"CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w\".]+)", re.IGNORECASE)
CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w\".]+)\s*\((.*)\)\s*;?\s*$", re.IGNORECASE | re.DOTALL)
<<<<<<< HEAD
LIKE_TABLE_RE = re.compile(
    r'^LIKE\s+([\w\".]+)(?P<options>(?:\s+(?:INCLUDING|EXCLUDING)\s+(?:COMMENTS|COMPRESSION|CONSTRAINTS|DEFAULTS|GENERATED|IDENTITY|INDEXES|STATISTICS|STORAGE|ALL))*)\s*$',
    re.IGNORECASE,
)
=======
>>>>>>> personal/main
SUPPORTED_TYPE_RE = re.compile(
    r"^(character\s+varying|varchar|character|char|text|smallserial|smallint|integer|int|bigserial|bigint|serial|uuid|jsonb|json|date|time|timestamptz|timestamp(?:\s+with(?:out)?\s+time\s+zone)?|boolean|bool|numeric|decimal|double\s+precision|real|float)(?:\s*\([^)]*\))?(?=\s|,|$)",
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
<<<<<<< HEAD
    match = re.search(
        r'REFERENCES\s+([\w".]+)(?:\s*\(([^)]+)\))?',
        text,
        re.IGNORECASE,
    )
    if not match:
        raise DDLParserError(f"Unsupported REFERENCES clause: {text}")
    _, table_name = _split_qualified_name(match.group(1))
    parent_columns = _parse_column_list(match.group(2)) if match.group(2) else []
    return table_name, parent_columns
=======
    match = re.search(r"REFERENCES\s+([\w\".]+)\s*\(([^)]+)\)", text, re.IGNORECASE)
    if not match:
        raise DDLParserError(f"Unsupported REFERENCES clause: {text}")
    _, table_name = _split_qualified_name(match.group(1))
    return table_name, _parse_column_list(match.group(2))

>>>>>>> personal/main


def _constraint_name(original):
    match = re.match(r'CONSTRAINT\s+([\w"]+)\s+', original, re.IGNORECASE)
    return _clean_identifier(match.group(1)) if match else None


def _parse_check_expression(expression, name=None):
    text = expression.strip()
    if text.upper().startswith("CHECK"):
        text = text[text.find("(") + 1: text.rfind(")")].strip()
    normalized_text = re.sub(r"::\s*\w+(?:\[\])?", "", text)
    normalized_text = re.sub(r"\(\s*([\w\"]+)\s*\)", r"\1", normalized_text)
    in_match = re.fullmatch(r'([\w"]+)\s+IN\s*\((.+)\)', normalized_text, re.IGNORECASE | re.DOTALL)
    if in_match:
        values = [item.strip().strip("'").strip('"') for item in _split_top_level_commas(in_match.group(2))]
        return CheckConstraint(expression=text, column=_clean_identifier(in_match.group(1)), operator="IN", values=values, name=name, supported=True)
    any_match = re.fullmatch(r'([\w"]+)\s*=\s*ANY\s*\(\s*ARRAY\s*\[(.+)\]\s*\)', normalized_text, re.IGNORECASE | re.DOTALL)
    if any_match:
        values = [item.strip().strip("'").strip('"') for item in _split_top_level_commas(any_match.group(2))]
        return CheckConstraint(expression=text, column=_clean_identifier(any_match.group(1)), operator="IN", values=values, name=name, supported=True)
    between_match = re.fullmatch(r'([\w"]+)\s+BETWEEN\s+(-?\d+(?:\.\d+)?)\s+AND\s+(-?\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if between_match:
        return CheckConstraint(expression=text, column=_clean_identifier(between_match.group(1)), operator="BETWEEN", min_value=between_match.group(2), max_value=between_match.group(3), name=name, supported=True)
    compare_match = re.fullmatch(r'([\w"]+)\s*(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if compare_match:
        return CheckConstraint(expression=text, column=_clean_identifier(compare_match.group(1)), operator=compare_match.group(2), min_value=compare_match.group(3), max_value=compare_match.group(3), name=name, supported=True)
    return CheckConstraint(expression=text, name=name, supported=False)

def _parse_table_constraint(part, table):
    original = part.strip()
    constraint_name = _constraint_name(original)
    text = re.sub(r"^CONSTRAINT\s+[\w\"]+\s+", "", original, flags=re.IGNORECASE)
    pk_match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", text, re.IGNORECASE)
    if pk_match:
        table.primary_key = _parse_column_list(pk_match.group(1))
        return
<<<<<<< HEAD
    fk_match = re.search(
        r'FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+([\w".]+)(?:\s*\(([^)]+)\))?',
        text,
        re.IGNORECASE,
    )
    if fk_match:
        _, parent_table = _split_qualified_name(fk_match.group(2))
        parent_columns = _parse_column_list(fk_match.group(3)) if fk_match.group(3) else []
        table.foreign_keys.append(
            ForeignKey(
                table.name,
                _parse_column_list(fk_match.group(1)),
                parent_table,
                parent_columns,
            )
        )
=======
    fk_match = re.search(r"FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+([\w\".]+)\s*\(([^)]+)\)", text, re.IGNORECASE)
    if fk_match:
        _, parent_table = _split_qualified_name(fk_match.group(2))
        table.foreign_keys.append(ForeignKey(table.name, _parse_column_list(fk_match.group(1)), parent_table, _parse_column_list(fk_match.group(3))))
>>>>>>> personal/main
        return
    unique_match = re.search(r"UNIQUE\s*\(([^)]+)\)", text, re.IGNORECASE)
    if unique_match:
        table.unique_constraints.append(UniqueConstraint(_parse_column_list(unique_match.group(1)), name=constraint_name))
        return
    check_match = re.search(r"CHECK\s*\(", text, re.IGNORECASE)
    if check_match:
        check = _parse_check_expression(text, name=constraint_name)
        table.check_constraints.append(check)
        if not check.supported:
            table.ignored_constraints.append(f"CHECK: {original}")
            table.warnings.append(f"Unsupported CHECK constraint ignored safely: {original}")
        return
    if re.match(r"^CONSTRAINT\b", original, re.IGNORECASE):
        table.ignored_constraints.append(f"UNSUPPORTED: {original}")
        table.warnings.append(f"Unsupported table constraint ignored safely: {original}")
        return
    raise DDLParserError(f"Unsupported table constraint: {part}")


<<<<<<< HEAD
def _copy_like_table(part, table, model):
    """Apply PostgreSQL CREATE TABLE ... (LIKE source INCLUDING/EXCLUDING ...)."""
    match = LIKE_TABLE_RE.fullmatch(part.strip())
    if not match:
        return False

    source_schema, source_name = _split_qualified_name(match.group(1))
    candidates = [source_name.lower()]
    if source_schema:
        candidates.insert(0, f"{source_schema}.{source_name}".lower())
    table_map = model.table_map()
    source = next((table_map[name] for name in candidates if name in table_map), None)
    if source is None:
        raise DDLParserError(
            f"CREATE TABLE {table.full_name} uses LIKE for unknown or not-yet-parsed "
            f"table {match.group(1)}."
        )

    options = match.group("options").upper()
    include_all = "INCLUDING ALL" in options
    excluded = {name.upper() for name in re.findall(r"EXCLUDING\s+(\w+)", options, re.IGNORECASE)}

    # PostgreSQL LIKE always copies column names/types/not-null. Other properties
    # are copied only when requested, with INCLUDING ALL acting as the superset.
    table.columns.extend(copy.deepcopy(source.columns))
    if not include_all and "CONSTRAINTS" not in options:
        for column in table.columns:
            column.is_primary_key = False
    if include_all or "CONSTRAINTS" in options:
        if "CONSTRAINTS" not in excluded and "ALL" not in excluded:
            table.primary_key = copy.deepcopy(source.primary_key)
            copied_foreign_keys = copy.deepcopy(source.foreign_keys)
            for foreign_key in copied_foreign_keys:
                foreign_key.child_table = table.name
            table.foreign_keys.extend(copied_foreign_keys)
            table.unique_constraints.extend(copy.deepcopy(source.unique_constraints))
            table.check_constraints.extend(copy.deepcopy(source.check_constraints))
    if not include_all and "DEFAULTS" not in options:
        for column in table.columns:
            column.default = None
    if "DEFAULTS" in excluded or "ALL" in excluded:
        for column in table.columns:
            column.default = None
    if not include_all and "IDENTITY" not in options:
        # Identity metadata is represented by the parser as a missing/defaulted
        # integer PK and is rebuilt safely by postgres_loader._column_ddl.
        pass

    table.ignored_constraints.extend(copy.deepcopy(source.ignored_constraints))
    table.warnings.extend(copy.deepcopy(source.warnings))
    return True


=======
>>>>>>> personal/main
def _parse_column(part, table):
    match = re.match(r"([\w\"]+)\s+(.+)$", part.strip(), re.DOTALL)
    if not match:
        raise DDLParserError(f"Unsupported column definition: {part}")
    name = _clean_identifier(match.group(1))
    rest = match.group(2).strip()
    type_match = SUPPORTED_TYPE_RE.match(rest)
    if not type_match:
        raise DDLParserError(f"Unsupported data type in table {table.full_name}, column {name}: {rest}")
    data_type = type_match.group(0).strip()
    constraints = rest[type_match.end():]
    length_match = re.match(r"^(?:varchar|character\s+varying|char|character)\s*\((\d+)\)", data_type, re.IGNORECASE)
    max_length = int(length_match.group(1)) if length_match else None
    numeric_match = re.match(r"^(?:numeric|decimal)\s*\((\d+)\s*,\s*(\d+)\)", data_type, re.IGNORECASE)
    numeric_precision = int(numeric_match.group(1)) if numeric_match else None
    numeric_scale = int(numeric_match.group(2)) if numeric_match else None
    default_match = re.search(r"\bDEFAULT\s+(.+?)(?=\s+NULL\b|\s+NOT\s+NULL|\s+PRIMARY\s+KEY|\s+UNIQUE\b|\s+REFERENCES\b|\s+CHECK\b|\s+COLLATE\b|\s+GENERATED\b|\s+IDENTITY\b|$)", constraints, re.IGNORECASE | re.DOTALL)
    column = Column(
        name=name,
        data_type=data_type,
        nullable=not re.search(r"\bNOT\s+NULL\b", constraints, re.IGNORECASE),
        is_primary_key=bool(re.search(r"\bPRIMARY\s+KEY\b", constraints, re.IGNORECASE)),
        max_length=max_length,
        numeric_precision=numeric_precision,
        numeric_scale=numeric_scale,
        default=default_match.group(1).strip() if default_match else None,
    )
    ref_match = re.search(r"\bREFERENCES\b", constraints, re.IGNORECASE)
    if ref_match:
        parent_table, parent_columns = _parse_references(constraints)
        column.references_table = parent_table
<<<<<<< HEAD
        column.references_column = parent_columns[0] if parent_columns else None
        table.foreign_keys.append(ForeignKey(table.name, [name], parent_table, parent_columns))
=======
        column.references_column = parent_columns[0]
        table.foreign_keys.append(ForeignKey(table.name, [name], parent_table, [parent_columns[0]]))
>>>>>>> personal/main
    if re.search(r"\bUNIQUE\b", constraints, re.IGNORECASE):
        table.unique_constraints.append(UniqueConstraint([name]))
    inline_check = re.search(r"\bCHECK\s*\((.+)\)", constraints, re.IGNORECASE | re.DOTALL)
    if inline_check:
        check = _parse_check_expression(f"CHECK ({inline_check.group(1)})")
        table.check_constraints.append(check)
        if not check.supported:
            table.ignored_constraints.append(f"CHECK: {name} {inline_check.group(0)}")
            table.warnings.append(f"Unsupported CHECK constraint ignored safely for column {name}.")
    if column.is_primary_key:
        table.primary_key.append(name)
        column.nullable = False
    table.columns.append(column)


def _split_statements(ddl_text):
    if sqlparse is not None:
        return [statement.strip() for statement in sqlparse.split(ddl_text) if statement.strip()]
    statements = []
    current = []
    depth = 0
    in_quote = False
    for char in ddl_text:
        if char == "'":
            in_quote = not in_quote
        elif not in_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == ";" and depth == 0:
                statements.append("".join(current).strip() + ";")
                current = []
                continue
        current.append(char)
    if current and "".join(current).strip():
        statements.append("".join(current).strip())
    return statements


<<<<<<< HEAD

def _resolve_implicit_reference_columns(model):
    """Resolve REFERENCES table clauses that omit the primary-key column list."""
    table_map = model.table_map()
    for table in model.tables:
        for foreign_key in table.foreign_keys:
            if foreign_key.parent_columns:
                continue
            parent = table_map.get(foreign_key.parent_table.lower())
            if parent is None:
                raise DDLParserError(
                    f"Foreign key on {table.name} references unknown table "
                    f"{foreign_key.parent_table}."
                )
            if not parent.primary_key:
                raise DDLParserError(
                    f"REFERENCES {foreign_key.parent_table} omits a column list, "
                    "but the referenced table has no parsed primary key."
                )
            if len(foreign_key.child_columns) != len(parent.primary_key):
                raise DDLParserError(
                    f"Foreign key on {table.name} has {len(foreign_key.child_columns)} "
                    f"column(s), but {foreign_key.parent_table} has a "
                    f"{len(parent.primary_key)}-column primary key."
                )
            foreign_key.parent_columns = list(parent.primary_key)
            for child_column, parent_column in zip(
                foreign_key.child_columns, foreign_key.parent_columns
            ):
                column = next(
                    (item for item in table.columns if item.name == child_column),
                    None,
                )
                if column is not None:
                    column.references_table = foreign_key.parent_table
                    column.references_column = parent_column


=======
>>>>>>> personal/main
def parse_ddl(ddl_text):
    model = DDLModel()
    statements = _split_statements(ddl_text)
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
<<<<<<< HEAD
                if _copy_like_table(normalized, table, model):
                    continue
=======
>>>>>>> personal/main
                if re.match(r"^CONSTRAINT\b|^(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK)\b", normalized, re.IGNORECASE):
                    _parse_table_constraint(normalized, table)
                else:
                    _parse_column(normalized, table)
            for column in table.columns:
                if column.name in table.primary_key:
                    column.is_primary_key = True
                    column.nullable = False
            if not table.columns:
                raise DDLParserError(f"CREATE TABLE {table.full_name} has no columns.")
            model.warnings.extend(table.warnings)
            model.tables.append(table)
            continue

        if re.search(r"\bCREATE\b", statement, re.IGNORECASE):
            raise DDLParserError(f"Unsupported DDL statement: {statement[:120]}")
    if not model.tables:
        raise DDLParserError("No CREATE TABLE statements were parsed from DDL.")
<<<<<<< HEAD
    _resolve_implicit_reference_columns(model)
=======
>>>>>>> personal/main
    return model
