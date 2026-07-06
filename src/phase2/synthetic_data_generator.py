from collections import defaultdict, deque
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal, InvalidOperation
import random
import re
import uuid

try:
    from faker import Faker
except ImportError:  # pragma: no cover - exercised when optional dependency is unavailable
    class Faker:
        _first = ["Alex", "Jordan", "Taylor", "Morgan", "Casey"]
        _last = ["Smith", "Patel", "Garcia", "Brown", "Jones"]
        _cities = ["London", "Manchester", "Bristol", "Leeds", "Glasgow"]
        _countries = ["United Kingdom", "United States", "Canada", "Australia", "Ireland"]
        _words = ["Alpha", "Nova", "Summit", "Atlas", "Vertex"]
        def __init__(self):
            self._idx = 0
        @staticmethod
        def seed(_seed):
            return None
        def _next(self, values):
            value = values[self._idx % len(values)]
            self._idx += 1
            return value
        def first_name(self):
            return self._next(self._first)
        def last_name(self):
            return self._next(self._last)
        def name(self):
            return f"{self.first_name()} {self.last_name()}"
        def city(self):
            return self._next(self._cities)
        def country(self):
            return self._next(self._countries)
        def street_address(self):
            return f"{self._idx + 1} Main Street"
        def word(self):
            return self._next(self._words).lower()
        def sentence(self, nb_words=8):
            return " ".join(self.word() for _ in range(nb_words)).capitalize() + "."

from .value_catalog_parser import get_catalog_rule


class SyntheticDataError(Exception):
    pass


GENERIC_STATUSES = ["New", "Active", "Pending", "Completed", "Inactive"]
GENERIC_SEGMENTS = ["New", "Regular", "Premium"]
GENERIC_METHODS = ["Online", "In Person", "Phone", "Partner"]
GENERIC_TYPES = ["Standard", "Preferred", "Specialty"]
SYNTHETIC_BASE_DATE = date(2026, 7, 6)


def table_generation_order(model):
    tables = {table.name: table for table in model.tables}
    indegree = {name: 0 for name in tables}
    children = defaultdict(list)
    for table in model.tables:
        for fk in table.foreign_keys:
            if fk.parent_table not in tables:
                raise SyntheticDataError(f"Foreign key on {table.name} references unknown table {fk.parent_table}.")
            children[fk.parent_table].append(table.name)
            indegree[table.name] += 1
    queue = deque([name for name, degree in indegree.items() if degree == 0])
    order = []
    while queue:
        name = queue.popleft()
        order.append(tables[name])
        for child in children[name]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(order) != len(model.tables):
        raise SyntheticDataError("Circular foreign key dependencies are not supported in Phase 2 MVP.")
    return order


def _bounded(value, column, stats):
    if isinstance(value, str) and column.max_length and len(value) > column.max_length:
        stats["truncated_values"] += 1
        return value[: column.max_length]
    return value


def _cycle(values, index, column, stats):
    if not values:
        return None
    return _bounded(values[(index - 1) % len(values)], column, stats)


def _semantic_prefix(column_name):
    base = column_name.lower()
    if base.endswith("_id"):
        base = base[:-3]
    prefix_map = {
        "customer": "CUST",
        "product": "PROD",
        "store": "STORE",
        "order": "ORDER",
        "order_item": "ORDERITEM",
        "payment": "PAYMENT",
        "delivery": "DELIVERY",
        "supplier": "SUPPLIER",
        "employee": "EMPLOYEE",
        "user": "USER",
        "account": "ACCOUNT",
        "invoice": "INVOICE",
        "transaction": "TXN",
    }
    return prefix_map.get(base, re.sub(r"[^A-Z0-9]", "", base.upper()) or "ID")


def _business_id_value(column, index):
    name = column.name.lower()
    prefix = _semantic_prefix(name)
    if name == "order_id" or name.endswith("_order_id"):
        return f"{prefix}-{_date_key_value(index)}-{index:06d}"
    return f"{prefix}-{index:06d}"


def _table_prefix(table_name):
    cleaned = re.sub(r"^(dim_|fact_|stg_|load_)", "", table_name.lower()).replace("_raw", "")
    letters = re.sub(r"[^a-z0-9]", "", cleaned).upper()
    return (letters[:12] or "ROW")


def _catalog_warning(stats, category, message):
    stats.setdefault(category, []).append(message)
    stats.setdefault("catalog_rule_warnings", []).append(message)


def _pk_value(column, index, table_name, stats):
    dtype = column.data_type.lower()
    if "uuid" in dtype:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table_name}.{column.name}.{index}"))
    if any(token in dtype for token in ["int", "serial"]):
        if column.name.lower() == "date_key" or column.name.lower().endswith("_date_key"):
            return _date_key_value(index)
        return index
    if column.name.lower().endswith("_id") and any(token in dtype for token in ["char", "text"]):
        return _bounded(_business_id_value(column, index), column, stats)
    if any(token in dtype for token in ["char", "text"]):
        return _bounded(f"{_table_prefix(table_name)}-{index:06d}", column, stats)
    return _bounded(f"{table_name}_{index:03d}", column, stats)


def _numeric_value(rng, column, stats, numeric_min=None, numeric_max=None):
    scale = column.numeric_scale if column.numeric_scale is not None else 2
    if column.numeric_precision is not None and column.numeric_scale is not None:
        integer_digits = max(column.numeric_precision - column.numeric_scale, 0)
        ddl_max = (Decimal(10) ** integer_digits) - (Decimal(1).scaleb(-column.numeric_scale) if column.numeric_scale > 0 else Decimal(1))
    else:
        ddl_max = Decimal("999.99")

    min_value = Decimal(str(numeric_min)) if numeric_min is not None else Decimal("0")
    max_value = Decimal(str(numeric_max)) if numeric_max is not None else ddl_max
    max_value = min(max_value, ddl_max)
    if max_value < min_value:
        max_value = min_value
    quantizer = Decimal(1).scaleb(-scale) if scale > 0 else Decimal(1)
    span = max_value - min_value
    if span <= 0:
        value = min_value
    else:
        steps = int((span / quantizer).to_integral_value()) if quantizer else 100
        offset = Decimal(rng.randint(0, max(steps, 1))) * quantizer
        value = min_value + offset
    stats["numeric_bounded_values"] += 1
    return value.quantize(quantizer)


def _short_email(index, column, stats, first_name="user", last_name="example"):
    local = f"{first_name}.{last_name}.{index:03d}".lower()
    value = re.sub(r"[^a-z0-9.]", "", local) + "@example.com"
    if column.max_length and len(value) > column.max_length:
        value = f"u{index}@x.co"
    return _bounded(value, column, stats)

def _is_integer_type(column):
    dtype = column.data_type.lower()
    return any(token in dtype for token in ["int", "serial"])


def _is_numeric_type(column):
    dtype = column.data_type.lower()
    return any(token in dtype for token in ["numeric", "decimal", "double", "float", "real"])


def _is_date_key_column(column):
    name = column.name.lower()
    return name == "date_key" or name.endswith("_date_key")


def _is_json_type(column):
    return column.data_type.lower() in {"json", "jsonb"}


def _date_key_value(index=1):
    synthetic_date = SYNTHETIC_BASE_DATE + timedelta(days=(index - 1) % 365)
    return int(synthetic_date.strftime("%Y%m%d"))


def _record_type_fallback(stats, column, value, reason):
    if stats is not None:
        stats.setdefault("type_normalization_warnings", []).append(
            f"{column.name}: could not normalize value {value!r}; used type-compatible fallback. Reason: {reason}"
        )


def _type_compatible_fallback(column, stats=None, value=None, reason="conversion failed"):
    dtype = column.data_type.lower()
    _record_type_fallback(stats, column, value, reason)
    if _is_integer_type(column):
        return _date_key_value() if _is_date_key_column(column) else 1
    if _is_numeric_type(column):
        scale = column.numeric_scale if column.numeric_scale is not None else 2
        quantizer = Decimal(1).scaleb(-scale) if scale > 0 else Decimal(1)
        return Decimal("0").quantize(quantizer)
    if "bool" in dtype:
        return False
    if dtype.startswith("date"):
        return SYNTHETIC_BASE_DATE
    if dtype.startswith("time") and "timestamp" not in dtype:
        return dt_time(12, 0, 0)
    if "timestamp" in dtype or "timestamptz" in dtype:
        return datetime.combine(SYNTHETIC_BASE_DATE, datetime.min.time())
    if "uuid" in dtype:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{column.name}.{value}"))
    if _is_json_type(column):
        return {"generated": True, "row_number": 1, "source": "synthetic"}
    return _bounded(str(value or ""), column, stats or {"truncated_values": 0})


def _check_constraint_value(table, column, index, stats):
    for check in getattr(table, "check_constraints", []):
        if not getattr(check, "supported", False) or check.column != column.name:
            continue
        if check.operator == "IN" and check.values:
            return normalize_value_for_column(_cycle(check.values, index, column, stats), column, stats)
        if check.operator == "BETWEEN":
            return normalize_value_for_column(check.min_value, column, stats)
        if check.operator in {">", ">="}:
            base = Decimal(str(check.min_value))
            value = base + (Decimal(1) if check.operator == ">" else Decimal(0))
            return normalize_value_for_column(value, column, stats)
        if check.operator in {"<", "<="}:
            base = Decimal(str(check.min_value))
            value = base - (Decimal(1) if check.operator == "<" else Decimal(0))
            return normalize_value_for_column(value, column, stats)
    return None


def normalize_value_for_column(value, column, stats=None):
    dtype = column.data_type.lower()
    if value is None:
        return None
    if _is_integer_type(column):
        if isinstance(value, date) and not isinstance(value, datetime):
            return int(value.strftime("%Y%m%d")) if _is_date_key_column(column) else 1
        try:
            return int(Decimal(str(value)))
        except (InvalidOperation, TypeError, ValueError):
            return _type_compatible_fallback(column, stats, value, "integer conversion failed")
    if _is_numeric_type(column):
        try:
            decimal_value = Decimal(str(value))
            if column.numeric_scale is not None:
                decimal_value = decimal_value.quantize(Decimal(1).scaleb(-column.numeric_scale) if column.numeric_scale else Decimal(1))
            return decimal_value
        except (InvalidOperation, TypeError, ValueError):
            return _type_compatible_fallback(column, stats, value, "decimal conversion failed")
    if "bool" in dtype:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"true", "yes", "1", "y"}:
            return True
        if normalized in {"false", "no", "0", "n"}:
            return False
        return bool(value)
    if dtype.startswith("date"):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError):
            return _type_compatible_fallback(column, stats, value, "date conversion failed")
    if dtype.startswith("time") and "timestamp" not in dtype:
        if isinstance(value, dt_time):
            return value
        try:
            return dt_time.fromisoformat(str(value))
        except (TypeError, ValueError):
            return _type_compatible_fallback(column, stats, value, "time conversion failed")
    if "timestamp" in dtype or "timestamptz" in dtype:
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return _type_compatible_fallback(column, stats, value, "timestamp conversion failed")
    if "uuid" in dtype:
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, TypeError):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(value)))
    if _is_json_type(column):
        if isinstance(value, (dict, list)):
            return value
        try:
            import json
            return json.loads(str(value))
        except (TypeError, ValueError):
            return {"generated": True, "row_number": 1, "source": "synthetic", "value": str(value)}
    return _bounded(str(value), column, stats or {"truncated_values": 0})

def _render_pattern(pattern, fake, table, column, index, stats, catalog, row=None):
    context = (catalog or {}).get("business_context", {}) if isinstance(catalog, dict) else {}
    date_text = (SYNTHETIC_BASE_DATE + timedelta(days=(index - 1) % 365)).strftime("%Y%m%d")
    entity_name = table.name.replace("dim_", "").replace("fact_", "").replace("stg_", "").replace("load_", "").replace("_raw", "")
    replacements = {
        "business_name": context.get("business_name", "Business"),
        "table_name": table.name,
        "column_name": column.name,
        "entity_name": entity_name,
        "number": f"{index:03d}",
        "row_number": f"{index:03d}",
        "line_number": str(((index - 1) % 5) + 1),
        "sequence": f"{index:06d}",
        "batch_number": f"BATCH-{index:06d}",
        "YYYYMMDD": date_text,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "city": fake.city(),
        "category": "Category",
        "order_id": (row or {}).get("order_id", f"ORD-{date_text}-{index:06d}"),
    }
    value = pattern
    if value == "YYYYMMDD":
        value = date_text
    value = re.sub(r"\{0[0-9]*\}", lambda match: f"{index:0{len(match.group(0)) - 2}d}", value)
    value = re.sub(r"\{(\d+)\s*-?\s*digit\s+number\}", lambda match: f"{index:0{int(match.group(1))}d}", value, flags=re.IGNORECASE)
    word_widths = {"six": 6, "eight": 8, "ten": 10, "four": 4}
    value = re.sub(
        r"\{(six|eight|ten|four)\s+digit\s+number\}",
        lambda match: f"{index:0{word_widths[match.group(1).lower()]}d}",
        value,
        flags=re.IGNORECASE,
    )
    for key, replacement in replacements.items():
        value = value.replace("{" + key + "}", str(replacement))
    if "{" in value or "}" in value:
        _catalog_warning(
            stats,
            "unsupported_catalog_patterns",
            f"{table.name}.{column.name}: unsupported value_pattern {pattern!r}; used DDL semantic fallback.",
        )
        return None
    return normalize_value_for_column(value, column, stats)



def _date_from_rule(rule_text, row, index, rng, stats):
    text = str(rule_text or "").strip().lower()
    between_match = re.search(r"between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})", text)
    if between_match:
        start = datetime.fromisoformat(between_match.group(1)).date()
        end = datetime.fromisoformat(between_match.group(2)).date()
        days = max((end - start).days, 0)
        return start + timedelta(days=rng.randint(0, days))
    relation_match = re.search(r"(before|after|same day or after|derived from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", text)
    if relation_match:
        relation, source_name = relation_match.groups()
        source = row.get(source_name)
        if isinstance(source, datetime):
            source = source.date()
        if isinstance(source, date):
            if relation == "before":
                return source - timedelta(days=1 + (index % 7))
            if relation in {"after", "same day or after"}:
                return source + timedelta(days=index % 7)
            if relation == "derived from":
                return source
    if "start <= end" in text or "effective_start_date <= effective_end_date" in text:
        return date.today() - timedelta(days=index % 365)
    if text:
        stats["date_rule_warnings"].append(f"Unsupported date_rule: {rule_text}")
    return date.today() - timedelta(days=index % 365)


def _boolean_from_rule(rule_text, row, index, stats):
    text = str(rule_text or "").strip()
    match = re.search(r"(true|false)\s+when\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(=|!=|>|<|>=|<=)\s*['\"]?([^'\"]+)['\"]?", text, re.IGNORECASE)
    if not match:
        if text:
            stats["boolean_rule_warnings"].append(f"Unsupported boolean_rule: {rule_text}")
        return index % 2 == 0
    expected_bool, column_name, operator, raw_expected = match.groups()
    actual = row.get(column_name)
    expected_decimal = _to_decimal(raw_expected)
    actual_decimal = _to_decimal(actual)
    if operator in {">", "<", ">=", "<="} and expected_decimal is not None and actual_decimal is not None:
        comparisons = {">": actual_decimal > expected_decimal, "<": actual_decimal < expected_decimal, ">=": actual_decimal >= expected_decimal, "<=": actual_decimal <= expected_decimal}
        outcome = comparisons[operator]
    elif operator == "=":
        outcome = str(actual).strip().lower() == raw_expected.strip().lower()
    else:
        outcome = str(actual).strip().lower() != raw_expected.strip().lower()
    return outcome if expected_bool.lower() == "true" else not outcome

def _catalog_value(rule, fake, rng, table, column, index, stats, catalog, row=None):
    if not rule:
        return None
    stats["catalog_columns_used"].add(f"{table.name}.{column.name}")
    allowed = rule.get("allowed_values") or []
    if allowed:
        return normalize_value_for_column(_cycle(allowed, index, column, stats), column, stats)
    examples = rule.get("value_examples") or []
    if examples:
        return normalize_value_for_column(_cycle(examples, index, column, stats), column, stats)
    pattern = rule.get("value_pattern")
    if pattern:
        rendered_value = _render_pattern(str(pattern), fake, table, column, index, stats, catalog, row)
        if rendered_value is not None:
            return rendered_value
    if rule.get("numeric_min") is not None or rule.get("numeric_max") is not None:
        if any(token in column.data_type.lower() for token in ["int", "serial"]):
            min_value = int(rule.get("numeric_min") if rule.get("numeric_min") is not None else 1)
            max_value = int(rule.get("numeric_max") if rule.get("numeric_max") is not None else 100)
            return normalize_value_for_column(rng.randint(min_value, max(max_value, min_value)), column, stats)
        return normalize_value_for_column(_numeric_value(rng, column, stats, rule.get("numeric_min"), rule.get("numeric_max")), column, stats)
    if rule.get("boolean_rule"):
        return normalize_value_for_column(_boolean_from_rule(rule.get("boolean_rule"), row or {}, index, stats), column, stats)
    if rule.get("date_rule"):
        return normalize_value_for_column(_date_from_rule(rule.get("date_rule"), row or {}, index, rng, stats), column, stats)
    return None


def _relationship_parent_for_column(column, rule, generated):
    relationship = str((rule or {}).get("relationship_rule") or "").lower()
    column_name = column.name.lower()
    explicit = re.search(r"(dim_[a-zA-Z0-9_]+)\.([a-zA-Z_][a-zA-Z0-9_]*)", relationship)
    if explicit:
        table_name, parent_column = explicit.groups()
        for generated_table in generated:
            if generated_table.lower() == table_name.lower():
                return generated_table, parent_column
    if _is_date_key_column(column):
        for generated_table in generated:
            if generated_table.lower().endswith("dim_date"):
                return generated_table, "date_key"
    if column_name.endswith("_key"):
        base = column_name[:-4]
        expected = f"dim_{base}"
        for generated_table in generated:
            if generated_table.lower().endswith(expected):
                return generated_table, column.name
    return None, None


def _apply_catalog_relationships(table, row, index, generated, value_catalog, stats):
    for column in table.columns:
        rule = get_catalog_rule(value_catalog, table.name, column.name)
        if not rule and not _is_date_key_column(column):
            continue
        parent_table, parent_column = _relationship_parent_for_column(column, rule, generated)
        if not parent_table or parent_table not in generated:
            continue
        parent_rows = generated[parent_table]
        if not parent_rows:
            continue
        parent_row = parent_rows[(index - 1) % len(parent_rows)]
        if parent_column in parent_row:
            row[column.name] = normalize_value_for_column(parent_row[parent_column], column, stats)
            stats.setdefault("relationship_rule_columns", set()).add(f"{table.name}.{column.name}")


def _unique_adjusted_value(value, column, index, stats):
    dtype = column.data_type.lower()
    if _is_integer_type(column):
        return normalize_value_for_column(index, column, stats)
    if _is_numeric_type(column):
        return normalize_value_for_column(index, column, stats)
    if dtype.startswith("date"):
        return SYNTHETIC_BASE_DATE + timedelta(days=index % 365)
    if dtype.startswith("time") and "timestamp" not in dtype:
        return dt_time((index % 23), index % 59, 0)
    if "timestamp" in dtype or "timestamptz" in dtype:
        return datetime.combine(SYNTHETIC_BASE_DATE + timedelta(days=index % 365), datetime.min.time())
    if "bool" in dtype:
        return bool(index % 2)
    return _bounded(f"{value} {index:03d}", column, stats)


def _fk_parent_for_child(table, column_name):
    for fk in table.foreign_keys:
        for child_col, parent_col in zip(fk.child_columns, fk.parent_columns):
            if child_col == column_name:
                return fk.parent_table, parent_col
    return None, None


def _is_catalog_or_check_constrained(table, column_name, value_catalog):
    rule = get_catalog_rule(value_catalog, table.name, column_name)
    if rule and rule.get("allowed_values"):
        return True
    return any(
        getattr(check, "supported", False)
        and check.column == column_name
        and check.operator == "IN"
        and check.values
        for check in getattr(table, "check_constraints", [])
    )


def _check_in_values(table, column_name):
    values = []
    for check in getattr(table, "check_constraints", []):
        if getattr(check, "supported", False) and check.column == column_name and check.operator == "IN":
            values.extend(check.values)
    return values


def _detect_constraint_capacity(table, rows_per_table):
    for unique in getattr(table, "unique_constraints", []):
        if len(unique.columns) != 1:
            continue
        column_name = unique.columns[0]
        values = _check_in_values(table, column_name)
        if values and len(set(values)) < rows_per_table:
            raise SyntheticDataError(
                f"DDL constraint capacity exceeded: {table.name}.{column_name} UNIQUE has only {len(set(values))} possible values but {rows_per_table} rows requested."
            )


def _enforce_primary_key(table, row, seen_primary_keys, index, stats, retry=0):
    if not table.primary_key:
        return
    key = tuple(row.get(col) for col in table.primary_key)
    if key not in seen_primary_keys:
        seen_primary_keys.add(key)
        return
    column_lookup = {column.name: column for column in table.columns}
    adjusted_index = index + retry + 1
    for column_name in table.primary_key:
        column = column_lookup.get(column_name)
        if column is None:
            continue
        row[column_name] = _pk_value(column, adjusted_index, table.name, stats)
    key = tuple(row.get(col) for col in table.primary_key)
    if key in seen_primary_keys and retry < 10:
        _enforce_primary_key(table, row, seen_primary_keys, adjusted_index, stats, retry + 1)
        return
    if key in seen_primary_keys:
        raise SyntheticDataError(f"Unable to generate unique primary key for {table.name} after retries.")
    stats.setdefault("primary_key_repairs", set()).add(table.name)
    seen_primary_keys.add(key)


def _try_rotate_fk_value(table, row, unique_columns, column_name, generated, seen, index):
    parent_table, parent_column = _fk_parent_for_child(table, column_name)
    if not parent_table or parent_table not in generated:
        return False
    parent_rows = generated[parent_table]
    if not parent_rows:
        return False
    for offset in range(len(parent_rows)):
        candidate = parent_rows[(index - 1 + offset) % len(parent_rows)].get(parent_column)
        row[column_name] = candidate
        if tuple(row.get(col) for col in unique_columns) not in seen:
            return True
    return False


def _enforce_unique_constraints(table, row, seen_unique, index, stats, generated, value_catalog):
    column_lookup = {column.name: column for column in table.columns}
    for unique in getattr(table, "unique_constraints", []):
        if not unique.columns:
            continue
        key = tuple(row.get(col) for col in unique.columns)
        seen = seen_unique[tuple(unique.columns)]
        if key not in seen:
            seen.add(key)
            continue
        adjusted = False
        for column_name in reversed(unique.columns):
            if _try_rotate_fk_value(table, row, unique.columns, column_name, generated, seen, index):
                stats.setdefault("fk_safe_unique_adjustments", set()).add(f"{table.name}.{','.join(unique.columns)}")
                adjusted = True
                break
        if adjusted:
            seen.add(tuple(row.get(col) for col in unique.columns))
            continue
        for column_name in reversed(unique.columns):
            column = column_lookup.get(column_name)
            if column is None or _fk_parent_for_child(table, column_name)[0] or _is_catalog_or_check_constrained(table, column_name, value_catalog):
                continue
            row[column_name] = _unique_adjusted_value(row.get(column_name), column, index, stats)
            stats.setdefault("composite_unique_adjustments", set()).add(f"{table.name}.{','.join(unique.columns)}")
            adjusted = True
            break
        if not adjusted:
            _catalog_warning(
                stats,
                "unique_adjustment_warnings",
                f"{table.name}: exhausted safe values for UNIQUE({', '.join(unique.columns)}); preserved DDL-safe FK/constrained values.",
            )
        seen.add(tuple(row.get(col) for col in unique.columns))


def _apply_lifecycle_order(row):
    if isinstance(row.get("order_date"), date) and isinstance(row.get("payment_date"), date):
        if row["payment_date"] < row["order_date"]:
            row["payment_date"] = row["order_date"]
    promised = row.get("promised_delivery_time") or row.get("promised_timestamp")
    actual = row.get("actual_delivery_time") or row.get("actual_timestamp")
    if isinstance(promised, datetime) and isinstance(actual, datetime) and actual < promised:
        delta = promised - actual
        if "actual_delivery_time" in row:
            row["actual_delivery_time"] = promised + delta
        elif "actual_timestamp" in row:
            row["actual_timestamp"] = promised + delta


def _generic_label(prefix, index):
    return f"{prefix} {index:03d}"


def _fallback_value(fake, rng, table, column, index, stats):
    name = column.name.lower()
    dtype = column.data_type.lower()
    table_base = table.name.replace("dim_", "").replace("fact_", "").replace("stg_", "").replace("load_", "").replace("_raw", "")
    title = table_base.replace("_", " ").title() or "Item"

    if "email" in name:
        return _short_email(index, column, stats, fake.first_name(), fake.last_name())
    if "phone" in name:
        return _bounded(f"+1555{index:07d}", column, stats)
    if "address" in name:
        return _bounded(fake.street_address(), column, stats)
    if "city" in name:
        return _bounded(fake.city(), column, stats)
    if "country" in name:
        return _bounded(fake.country(), column, stats)
    if _is_json_type(column):
        return {"generated": True, "row_number": index, "source": "synthetic"}
    if _is_date_key_column(column) and _is_integer_type(column):
        return _date_key_value(index)
    if name.endswith("_id") and any(token in dtype for token in ["char", "text"]):
        return _bounded(_business_id_value(column, index), column, stats)
    if any(token in name for token in ["customer_name", "employee_name", "patient_name", "person_name", "contact_name"]):
        return _bounded(fake.name(), column, stats)
    if "first_name" in name:
        return _bounded(fake.first_name(), column, stats)
    if "last_name" in name:
        return _bounded(fake.last_name(), column, stats)
    if any(token in name for token in ["product_name", "service_name", "item_name"]):
        return _bounded(f"{title} {fake.word().title()} {index:03d}", column, stats)
    if any(token in name for token in ["store_name", "branch_name", "location_name"]):
        business_name = stats.get("business_name") or title
        return _bounded(f"{business_name} {fake.city()} Location {index:03d}", column, stats)
    if name.endswith("status") or name == "status":
        return _cycle(GENERIC_STATUSES, index, column, stats)
    if "segment" in name:
        return _cycle(GENERIC_SEGMENTS, index, column, stats)
    if "method" in name:
        return _cycle(GENERIC_METHODS, index, column, stats)
    if "category" in name or name.endswith("type") or name == "type":
        return _bounded(f"{title} {GENERIC_TYPES[(index - 1) % len(GENERIC_TYPES)]}", column, stats)
    if "date" in dtype or name.endswith("date"):
        return date.today() - timedelta(days=rng.randint(0, 730))
    if dtype.startswith("time") and "timestamp" not in dtype:
        return dt_time(index % 23, index % 59, 0)
    if "timestamp" in dtype or "timestamptz" in dtype or "time" in name:
        return datetime.now().replace(microsecond=0) - timedelta(days=rng.randint(0, 730), seconds=rng.randint(0, 86400))
    if "bool" in dtype or name.startswith("is_") or name.endswith("flag"):
        return index % 2 == 0
    if any(token in dtype for token in ["int", "serial"]):
        return rng.randint(1, 1000)
    if _is_numeric_type(column):
        return _numeric_value(rng, column, stats)
    if any(word in name for word in ["amount", "price", "cost", "total", "rate", "score", "percentage", "ratio", "value"]):
        return _numeric_value(rng, column, stats, 0, 100 if any(word in name for word in ["rate", "percentage", "ratio", "score"]) else None)
    if any(word in name for word in ["quantity", "count", "number"]):
        return rng.randint(1, 25)
    if "uuid" in dtype:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table.name}.{column.name}.{index}"))
    if "code" in name:
        return _bounded(f"{table_base[:3].upper()}{index:04d}", column, stats)
    if any(word in name for word in ["description", "comment", "notes"]):
        return _bounded(fake.sentence(nb_words=8), column, stats)
    if "name" in name:
        return _bounded(_generic_label(title, index), column, stats)
    stats["generic_fallback_values"] += 1
    return _bounded(f"Value {index:03d}", column, stats)


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _apply_calculation_rule(rule, row, column, stats):
    if not rule:
        return None
    calculation = str(rule.get("calculation_rule") or "").strip()
    if not calculation:
        return None

    flag_match = re.search(
        r"(?:flag\s+)?true\s+when\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*['\"]?([^'\"]+)['\"]?",
        calculation,
        re.IGNORECASE,
    )
    if flag_match and ("bool" in column.data_type.lower() or column.name.lower().endswith("flag") or column.name.lower().startswith("is_")):
        source_name, expected = flag_match.groups()
        return str(row.get(source_name, "")).strip().lower() == expected.strip().lower()

    if "=" not in calculation:
        return None
    target, expression = [part.strip() for part in calculation.split("=", 1)]
    if target.lower() != column.name.lower():
        return None

    percentage_match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*/\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\*\s*100", expression, re.IGNORECASE)
    if percentage_match:
        numerator = _to_decimal(row.get(percentage_match.group(1)))
        denominator = _to_decimal(row.get(percentage_match.group(2)))
        if numerator is not None and denominator not in (None, Decimal("0")):
            return (numerator / denominator) * Decimal("100")
        return None

    delay_match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*-\s*([a-zA-Z_][a-zA-Z0-9_]*)", expression)
    if delay_match and "minute" in column.name.lower():
        left = row.get(delay_match.group(1))
        right = row.get(delay_match.group(2))
        if isinstance(left, datetime) and isinstance(right, datetime):
            return int((left - right).total_seconds() // 60)

    match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*([*+\-/])\s*([a-zA-Z_][a-zA-Z0-9_]*)", expression)
    if not match:
        stats["calculation_warnings"].append(f"Unsupported calculation rule for {column.name}: {calculation}")
        return None
    left_name, operator, right_name = match.groups()
    left = _to_decimal(row.get(left_name))
    right = _to_decimal(row.get(right_name))
    if left is None or right is None:
        return None
    if operator == "*":
        return left * right
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "/" and right != 0:
        return left / right
    return None

def _finalize_calculations(model, generated, value_catalog, stats):
    for table in model.tables:
        for row in generated.get(table.name, []):
            for column in table.columns:
                rule = get_catalog_rule(value_catalog, table.name, column.name)
                value = _apply_calculation_rule(rule, row, column, stats)
                if value is not None:
                    if column.numeric_precision is not None or column.numeric_scale is not None:
                        scale = column.numeric_scale or 0
                        value = Decimal(value).quantize(Decimal(1).scaleb(-scale) if scale else Decimal(1))
                    row[column.name] = _bounded(value, column, stats)
                    stats["calculated_columns"].add(f"{table.name}.{column.name}")


def generate_synthetic_data(model, rows_per_table=100, seed=12345, value_catalog=None):
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)
    generated = {}
    table_map = model.table_map()
    catalog = (value_catalog or {}).get("catalog", value_catalog or {})
    stats = {
        "truncated_values": 0,
        "numeric_bounded_values": 0,
        "length_limited_columns": [],
        "catalog_found": bool((value_catalog or {}).get("catalog_found")),
        "catalog_rule_count": (value_catalog or {}).get("rule_count", 0),
        "catalog_columns_used": set(),
        "fallback_columns_used": set(),
        "fallback_to_ddl_inference_count": 0,
        "catalog_warnings": list((value_catalog or {}).get("warnings", [])),
        "catalog_errors": list((value_catalog or {}).get("errors", [])),
        "catalog_rule_warnings": [],
        "unsupported_catalog_patterns": [],
        "unique_adjustment_warnings": [],
        "fk_safe_unique_adjustments": set(),
        "composite_unique_adjustments": set(),
        "primary_key_repairs": set(),
        "generic_fallback_values": 0,
        "calculated_columns": set(),
        "relationship_rule_columns": set(),
        "calculation_warnings": [],
        "date_rule_warnings": [],
        "boolean_rule_warnings": [],
        "type_normalization_warnings": [],
        "business_name": ((catalog or {}).get("business_context", {}) if isinstance(catalog, dict) else {}).get("business_name", ""),
    }

    for table in table_generation_order(model):
        _detect_constraint_capacity(table, rows_per_table)
        rows = []
        seen_unique = defaultdict(set)
        seen_primary_keys = set()
        for index in range(1, rows_per_table + 1):
            row = {}
            for column in table.columns:
                if column.max_length and column.name not in stats["length_limited_columns"]:
                    stats["length_limited_columns"].append(column.name)
                if column.is_primary_key:
                    rule = get_catalog_rule(value_catalog, table.name, column.name)
                    value = None
                    if rule and not _is_integer_type(column):
                        value = _catalog_value(rule, fake, rng, table, column, index, stats, catalog, row)
                    row[column.name] = value if value is not None else _pk_value(column, index, table.name, stats)
                    continue
                value = _check_constraint_value(table, column, index, stats)
                rule = get_catalog_rule(value_catalog, table.name, column.name)
                if value is None:
                    value = _catalog_value(rule, fake, rng, table, column, index, stats, catalog, row)
                if value is None:
                    stats["fallback_columns_used"].add(f"{table.name}.{column.name}")
                    stats["fallback_to_ddl_inference_count"] += 1
                    value = _fallback_value(fake, rng, table, column, index, stats)
                row[column.name] = value
            for fk in table.foreign_keys:
                parent = table_map[fk.parent_table.lower()]
                parent_rows = generated[parent.name]
                parent_row = parent_rows[(index - 1) % len(parent_rows)]
                for child_col, parent_col in zip(fk.child_columns, fk.parent_columns):
                    row[child_col] = parent_row[parent_col]
            _apply_catalog_relationships(table, row, index, generated, value_catalog, stats)
            _apply_lifecycle_order(row)
            _enforce_primary_key(table, row, seen_primary_keys, index, stats)
            _enforce_unique_constraints(table, row, seen_unique, index, stats, generated, value_catalog)
            rows.append(row)
        generated[table.name] = rows
    _finalize_calculations(model, generated, value_catalog, stats)
    stats["catalog_columns_used"] = sorted(stats["catalog_columns_used"])
    stats["fallback_columns_used"] = sorted(stats["fallback_columns_used"])
    stats["calculated_columns"] = sorted(stats["calculated_columns"])
    stats["relationship_rule_columns"] = sorted(stats["relationship_rule_columns"])
    stats["fk_safe_unique_adjustments"] = sorted(stats["fk_safe_unique_adjustments"])
    stats["composite_unique_adjustments"] = sorted(stats["composite_unique_adjustments"])
    stats["primary_key_repairs"] = sorted(stats["primary_key_repairs"])
    generated["__stats__"] = stats
    return generated
