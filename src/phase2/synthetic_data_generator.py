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

from .semantic_context import build_semantic_context
from .reference_data_resolver import ReferenceDataResolver
from .warehouse_pipeline_planner import build_warehouse_pipeline_plan
from .warehouse_generation_profile import build_warehouse_generation_profile, TECHNICAL_COLUMNS


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


def _generation_warning(stats, category, message):
    stats.setdefault(category, []).append(message)


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
        check_column = str(getattr(check, "column", "") or "").strip().strip('"').lower()
        column_name = column.name.strip().strip('"').lower()
        if not getattr(check, "supported", False) or check_column != column_name:
            continue
        if check.operator == "IN" and check.values:
            stats.setdefault("check_in_value_sources", set()).add(f"{table.name}.{column.name}")
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


def _column_checks(table, column):
    column_name = column.name.strip().strip('"').lower()
    return [
        check for check in getattr(table, "check_constraints", [])
        if getattr(check, "supported", False)
        and str(getattr(check, "column", "") or "").strip().strip('"').lower() == column_name
    ]


def _first_check_in_values(table, column):
    for check in _column_checks(table, column):
        if check.operator == "IN" and check.values:
            return check.values
    return []


def _constraint_floor(check):
    if check.operator == ">":
        return Decimal(str(check.min_value)) + Decimal("1")
    if check.operator == ">=":
        return Decimal(str(check.min_value))
    return None


def _constraint_ceiling(check):
    if check.operator == "<":
        return Decimal(str(check.min_value)) - Decimal("1")
    if check.operator == "<=":
        return Decimal(str(check.min_value))
    return None


def _constraint_compatible_value(column, checks, index, stats):
    between = next((check for check in checks if check.operator == "BETWEEN"), None)
    if between:
        min_value = Decimal(str(between.min_value))
        max_value = Decimal(str(between.max_value))
        span = max_value - min_value
        value = min_value if span <= 0 else min_value + Decimal((index - 1) % (int(span) + 1))
        return normalize_value_for_column(value, column, stats)

    floors = [floor for floor in (_constraint_floor(check) for check in checks) if floor is not None]
    ceilings = [ceiling for ceiling in (_constraint_ceiling(check) for check in checks) if ceiling is not None]
    if floors or ceilings:
        floor = max(floors) if floors else Decimal("0")
        ceiling = min(ceilings) if ceilings else floor + Decimal("100")
        if ceiling < floor:
            ceiling = floor
        return normalize_value_for_column(floor, column, stats)
    return None


def _satisfies_numeric_constraints(value, checks):
    decimal_value = _to_decimal(value)
    if decimal_value is None:
        return False
    for check in checks:
        if check.operator == "BETWEEN":
            if not (Decimal(str(check.min_value)) <= decimal_value <= Decimal(str(check.max_value))):
                return False
        elif check.operator == ">":
            if not decimal_value > Decimal(str(check.min_value)):
                return False
        elif check.operator == ">=":
            if not decimal_value >= Decimal(str(check.min_value)):
                return False
        elif check.operator == "<":
            if not decimal_value < Decimal(str(check.min_value)):
                return False
        elif check.operator == "<=":
            if not decimal_value <= Decimal(str(check.min_value)):
                return False
    return True


def finalize_generated_value(table, column, value, row_index, row_context, stats):
    """Central DDL guard for every generated cell before it is stored."""
    original = value
    checks = _column_checks(table, column)
    check_in_values = _first_check_in_values(table, column)
    if check_in_values:
        if str(value) not in {str(item) for item in check_in_values}:
            stats.setdefault("check_in_value_sources", set()).add(f"{table.name}.{column.name}")
            value = _cycle(check_in_values, row_index, column, stats)
        value = normalize_value_for_column(value, column, stats)
    else:
        normalized = normalize_value_for_column(value, column, stats)
        if normalized != original:
            stats.setdefault("ddl_type_corrections", set()).add(f"{table.name}.{column.name}")
        value = normalized

    constraint_value = _constraint_compatible_value(column, checks, row_index, stats)
    if constraint_value is not None and not _satisfies_numeric_constraints(value, checks):
        stats.setdefault("ddl_type_corrections", set()).add(f"{table.name}.{column.name}")
        value = constraint_value

    name = column.name.lower()
    if isinstance(value, date) and not isinstance(value, datetime) and "end" in name:
        start_value = next(
            (candidate for key, candidate in row_context.items() if "start" in key.lower() and isinstance(candidate, date) and not isinstance(candidate, datetime)),
            None,
        )
        if start_value and value < start_value:
            value = start_value + timedelta(days=row_index % 30)
            stats.setdefault("date_rule_corrections", set()).add(f"{table.name}.{column.name}")

    if isinstance(value, str) and column.max_length and len(value) > column.max_length:
        stats.setdefault("varchar_length_corrections", set()).add(f"{table.name}.{column.name}")
        value = _bounded(value, column, stats)
    return value


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
        return _type_compatible_fallback(column, stats, value, "boolean conversion failed")
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
    suffix = f" {index:03d}"
    if isinstance(value, str) and value.strip():
        base = value.strip()
    else:
        semantic = column.name.lower()
        if any(token in semantic for token in ["city", "location", "area"]):
            base = "Location"
        elif "region" in semantic:
            base = "Region"
        elif any(token in semantic for token in ["category", "segment", "type"]):
            base = semantic.replace("_", " ").title()
        elif any(token in semantic for token in ["name", "title", "label"]):
            base = semantic.replace("_", " ").title()
        else:
            base = "Value"
    if column.max_length:
        base = base[: max(column.max_length - len(suffix), 1)]
    return _bounded(f"{base}{suffix}", column, stats)


def _fk_parent_for_child(table, column_name):
    for fk in table.foreign_keys:
        for child_col, parent_col in zip(fk.child_columns, fk.parent_columns):
            if child_col == column_name:
                return fk.parent_table, parent_col
    return None, None


def _is_check_in_constrained(table, column_name):
    return any(
        getattr(check, "supported", False)
        and check.column == column_name
        and check.operator == "IN"
        and check.values
        for check in getattr(table, "check_constraints", [])
    )


def _is_sticky_domain_anchor(column_name):
    """Prefer stable anchor columns as a last resort during UNIQUE repair."""
    name = column_name.lower()
    return any(anchor in name for anchor in ["country", "currency", "tenant", "market", "locale"])


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


def _enforce_unique_constraints(table, row, seen_unique, index, stats, generated):
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
        candidate_columns = []
        sticky_columns = []
        for column_name in reversed(unique.columns):
            column = column_lookup.get(column_name)
            if column is None or _fk_parent_for_child(table, column_name)[0] or _is_check_in_constrained(table, column_name):
                continue
            if _is_sticky_domain_anchor(column_name):
                sticky_columns.append((column_name, column))
            else:
                candidate_columns.append((column_name, column))
        for column_name, column in candidate_columns + sticky_columns:
            original = row.get(column_name)
            for retry in range(0, 25):
                row[column_name] = _unique_adjusted_value(original, column, index + retry, stats)
                if tuple(row.get(col) for col in unique.columns) not in seen:
                    stats.setdefault("composite_unique_adjustments", set()).add(f"{table.name}.{','.join(unique.columns)}")
                    adjusted = True
                    break
            if adjusted:
                break
        if not adjusted:
            _generation_warning(
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


def _entity_base(table_name):
    return re.sub(r"^(load_|stg_|dim_|fact_)", "", table_name.lower()).replace("_raw", "")


def _shared_entity_key(table_name):
    base = _entity_base(table_name)
    parts = [part for part in base.split("_") if part not in {"raw", "fact"}]
    return parts[-1] if parts else base


def _reuse_entity_values(table, row, index, entity_store, stats):
    """Reuse same-named business attributes across load/stg/dim layers."""
    base = _shared_entity_key(table.name)
    reusable_names = {
        column.name for column in table.columns
        if not column.is_primary_key and not column.name.lower().endswith(("_key", "_id"))
    }
    if not reusable_names:
        return
    stored = entity_store.setdefault(base, {})
    row_store = stored.setdefault(index, {})
    reused = 0
    for name in reusable_names:
        if name in row_store:
            original = row_store[name]
            column = next((candidate for candidate in table.columns if candidate.name == name), None)
            row[name] = finalize_generated_value(table, column, original, index, row, stats) if column else original
            if row[name] != original:
                stats.setdefault("incompatible_reuse_corrections", set()).add(f"{table.name}.{name}")
            reused += 1
        elif name in row:
            row_store[name] = row[name]
    if reused:
        stats.setdefault("entity_reuse_events", set()).add(f"{table.name}:{base}:{reused}")


def _context_phrase(semantic_context, fallback="Item"):
    terms = []
    if semantic_context is not None:
        terms.extend(getattr(semantic_context, "domain_terms", [])[:2])
        terms.extend(getattr(semantic_context, "entity_terms", [])[:1])
    cleaned = [term.replace("_", " ").title() for term in terms if term]
    return " ".join(cleaned[:3]) or fallback


def _semantic_type_for(semantic_context, table, column):
    if semantic_context is None:
        return None
    semantic = semantic_context.semantic_for(table.name, column.name)
    return semantic.semantic_type if semantic else None


def _name_parts_from_row(row):
    for key, value in row.items():
        lowered = key.lower()
        if "name" in lowered and isinstance(value, str) and " " in value:
            parts = value.split()
            return parts[0], parts[-1]
    first = next((value for key, value in row.items() if key.lower().endswith("first_name") and isinstance(value, str)), None)
    last = next((value for key, value in row.items() if key.lower().endswith("last_name") and isinstance(value, str)), None)
    return first, last


def _apply_semantic_consistency(table, row, index, stats):
    first, last = _name_parts_from_row(row)
    for column in table.columns:
        name = column.name.lower()
        if "email" in name and first and last:
            row[column.name] = finalize_generated_value(table, column, _short_email(index, column, stats, first, last), index, row, stats)
    order_like = row.get("order_date") or row.get("created_at")
    payment_like = row.get("payment_date")
    if isinstance(order_like, date) and isinstance(payment_like, date) and payment_like < order_like:
        row["payment_date"] = order_like


def _fallback_value(fake, rng, table, column, index, stats, semantic_context=None, reference_resolver=None):
    name = column.name.lower()
    dtype = column.data_type.lower()
    table_base = table.name.replace("dim_", "").replace("fact_", "").replace("stg_", "").replace("load_", "").replace("_raw", "")
    title = table_base.replace("_", " ").title() or "Item"
    semantic_type = _semantic_type_for(semantic_context, table, column)
    context_label = _context_phrase(semantic_context, title)

    # DDL data types win before semantic or reference-data generation.
    if "bool" in dtype:
        return index % 2 == 0
    if dtype.startswith("date"):
        if semantic_type == "birth_date" or "birth" in name:
            return date(1970 + (index % 35), ((index - 1) % 12) + 1, ((index - 1) % 28) + 1)
        return SYNTHETIC_BASE_DATE - timedelta(days=rng.randint(0, 730))
    if dtype.startswith("time") and "timestamp" not in dtype:
        return dt_time(index % 23, index % 59, 0)
    if "timestamp" in dtype or "timestamptz" in dtype:
        return datetime.combine(SYNTHETIC_BASE_DATE, dt_time(index % 23, index % 59, 0)) - timedelta(days=rng.randint(0, 730))
    if _is_integer_type(column):
        if any(word in name for word in ["quantity", "count", "number", "score", "rank"]):
            return rng.randint(1, 25)
        return rng.randint(1, 1000)
    if _is_numeric_type(column):
        if any(word in name for word in ["rate", "percentage", "ratio", "score"]):
            upper_bound = 100
        elif any(word in name for word in ["amount", "price", "cost", "revenue", "total", "margin", "value"]):
            upper_bound = 10000
        else:
            upper_bound = 1000
        return _numeric_value(rng, column, stats, 0, upper_bound)

    if reference_resolver is not None and any(token in dtype for token in ["char", "text"]) and semantic_type in {"status", "category", "type", "method", "role", "position", "priority", "country", "nationality"}:
        reference_values, reference_key = reference_resolver.resolve(table.name, column.name, semantic_type)
        if reference_values:
            stats.setdefault("reference_data_matches", set()).add(f"{table.name}.{column.name} -> {reference_key}")
            return _cycle(reference_values, index, column, stats)

    if semantic_type == "json" or _is_json_type(column):
        return {"generated": True, "row_number": index, "source": "synthetic", "semantic": table_base}
    if semantic_type == "email" or "email" in name:
        return _short_email(index, column, stats, fake.first_name(), fake.last_name())
    if semantic_type == "phone" or "phone" in name:
        return _bounded(f"+1555{index:07d}", column, stats)
    if semantic_type == "address" or "address" in name:
        return _bounded(fake.street_address(), column, stats)
    if semantic_type == "city" or "city" in name:
        return _bounded(fake.city(), column, stats)
    if semantic_type == "country" or "country" in name:
        return _bounded(fake.country(), column, stats)
    if _is_date_key_column(column) and _is_integer_type(column):
        return _date_key_value(index)
    if name.endswith("_id") and any(token in dtype for token in ["char", "text"]):
        return _bounded(_business_id_value(column, index), column, stats)
    if semantic_type == "person_name" or any(token in name for token in ["customer_name", "employee_name", "patient_name", "person_name", "contact_name"]):
        return _bounded(fake.name(), column, stats)
    if "first_name" in name:
        return _bounded(fake.first_name(), column, stats)
    if "last_name" in name:
        return _bounded(fake.last_name(), column, stats)
    if semantic_type in {"product_name", "service_name"} or any(token in name for token in ["product_name", "service_name", "item_name"]):
        return _bounded(f"{context_label} {fake.word().title()} {index:03d}", column, stats)
    if any(token in name for token in ["store_name", "branch_name", "location_name", "company_name", "organization_name"]):
        return _bounded(f"{context_label} {fake.city()} {title} {index:03d}", column, stats)
    if semantic_type == "status" or name.endswith("status") or name == "status":
        return _cycle(GENERIC_STATUSES, index, column, stats)
    if semantic_type == "category" and "segment" in name:
        return _cycle(GENERIC_SEGMENTS, index, column, stats)
    if semantic_type == "method" or "method" in name:
        return _cycle(GENERIC_METHODS, index, column, stats)
    if semantic_type in {"role", "position"} or name in {"role", "position"} or name.endswith(("_role", "_position")):
        return _cycle(["Lead", "Associate", "Specialist", "Coordinator", "Manager"], index, column, stats)
    if semantic_type == "nationality" or "nationality" in name:
        return _bounded(fake.country(), column, stats)
    if semantic_type == "category" or "category" in name or name.endswith("type") or name == "type":
        return _bounded(f"{context_label} {GENERIC_TYPES[(index - 1) % len(GENERIC_TYPES)]}", column, stats)
    if "time" in name:
        return datetime.combine(SYNTHETIC_BASE_DATE, dt_time(index % 23, index % 59, 0)) - timedelta(days=rng.randint(0, 730))
    if name.startswith("is_") or name.endswith("flag"):
        return index % 2 == 0
    if not any(token in dtype for token in ["char", "text"]) and any(word in name for word in ["amount", "price", "cost", "total", "rate", "score", "percentage", "ratio", "value"]):
        return _numeric_value(rng, column, stats, 0, 100 if any(word in name for word in ["rate", "percentage", "ratio", "score"]) else None)
    if not any(token in dtype for token in ["char", "text"]) and any(word in name for word in ["quantity", "count", "number"]):
        return rng.randint(1, 25)
    if "uuid" in dtype:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table.name}.{column.name}.{index}"))
    if "code" in name:
        return _bounded(f"{table_base[:3].upper()}{index:04d}", column, stats)
    if any(word in name for word in ["description", "comment", "notes"]):
        return _bounded(fake.sentence(nb_words=8), column, stats)
    if "name" in name:
        if any(token in name for token in ["company", "organization", "organisation", "product", "service", "item"]):
            return _bounded(f"{context_label} {fake.word().title()} {index:03d}", column, stats)
        return _bounded(fake.name(), column, stats)
    if any(token in dtype for token in ["char", "text"]):
        return _bounded(f"Synthetic {context_label} {fake.word().title()} {index:03d}", column, stats)
    stats["generic_fallback_values"] += 1
    return _bounded(f"Synthetic {context_label} {index:03d}", column, stats)


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _infer_calculated_value(row, column):
    name = column.name.lower()
    quantity = _to_decimal(row.get("quantity"))
    if quantity is None:
        quantity = next((_to_decimal(value) for key, value in row.items() if any(token in key.lower() for token in ["quantity", "count", "sold"]) and _to_decimal(value) is not None), None)
    unit_price = _to_decimal(row.get("unit_price"))
    price = _to_decimal(row.get("price"))
    if price is None:
        price = next((_to_decimal(value) for key, value in row.items() if "price" in key.lower() and _to_decimal(value) is not None), None)
    cost = _to_decimal(row.get("cost"))
    revenue = _to_decimal(row.get("revenue"))

    if name in {"line_total_amount", "line_total", "total_amount"} and quantity is not None and unit_price is not None:
        return quantity * unit_price
    if "amount" in name and quantity is not None and price is not None:
        return quantity * price
    if "revenue" in name and quantity is not None and price is not None:
        return quantity * price
    if "margin" in name and revenue is not None and cost is not None:
        return revenue - cost
    if "delay" in name and "minute" in name:
        actual = row.get("actual_delivery_time") or row.get("actual_timestamp") or row.get("end_time")
        promised = row.get("promised_delivery_time") or row.get("promised_timestamp") or row.get("start_time")
        if isinstance(actual, datetime) and isinstance(promised, datetime):
            return max(0, int((actual - promised).total_seconds() // 60))
    if name in {"is_delayed", "delayed_flag"}:
        delay = _to_decimal(row.get("delivery_delay_minutes") or row.get("delay_minutes"))
        if delay is not None:
            return delay > 0
    if name in {"is_current", "current_flag"}:
        return row.get("effective_end_date") in (None, "")
    return None


def _finalize_calculations(model, generated, stats):
    for table in model.tables:
        for row_index, row in enumerate(generated.get(table.name, []), start=1):
            for column in table.columns:
                value = _infer_calculated_value(row, column)
                if value is not None:
                    if column.numeric_precision is not None or column.numeric_scale is not None:
                        scale = column.numeric_scale or 0
                        value = Decimal(value).quantize(Decimal(1).scaleb(-scale) if scale else Decimal(1))
                    row[column.name] = finalize_generated_value(table, column, _bounded(value, column, stats), row_index, row, stats)
                    stats.setdefault("calculation_corrections", set()).add(f"{table.name}.{column.name}")
                    stats["calculated_columns"].add(f"{table.name}.{column.name}")


def _finalize_row_values(table, row, index, stats):
    for column in table.columns:
        row[column.name] = finalize_generated_value(table, column, row.get(column.name), index, row, stats)


def _json_compatible(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


def _align_raw_payloads_with_staging(model, generated, pipeline_plan, stats):
    """Populate generic raw JSON envelopes from their mapped staging records."""
    table_map = {table.name: table for table in model.tables}
    aligned = set()
    for staging_name in pipeline_plan.get("staging_tables", []):
        staging = table_map[staging_name]
        sources = [
            source for source in pipeline_plan.get("lineage", {}).get(staging_name, [])
            if source in pipeline_plan.get("raw_tables", [])
        ]
        for raw_name in sources:
            raw = table_map[raw_name]
            if not any(
                column.name.lower() == "source_payload"
                and column.data_type.lower() in {"json", "jsonb"}
                for column in raw.columns
            ):
                continue
            raw_rows = generated.get(raw_name, [])
            staging_rows = generated.get(staging_name, [])
            if not raw_rows or not staging_rows:
                continue
            payload_columns = [
                column.name for column in staging.columns
                if column.name.lower() not in TECHNICAL_COLUMNS
                and not column.name.lower().endswith("_key")
            ]
            for index, raw_row in enumerate(raw_rows):
                staging_row = staging_rows[index % len(staging_rows)]
                raw_row["source_payload"] = _json_compatible({
                    column: staging_row.get(column) for column in payload_columns
                })
            aligned.add(f"{raw_name} -> {staging_name}")
    if aligned:
        stats.setdefault("raw_payload_alignment_events", set()).update(aligned)


def generate_synthetic_data(model, rows_per_table=100, seed=12345, semantic_context=None, business_input=None):
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)
    generated = {}
    table_map = model.table_map()
    if semantic_context is None:
        semantic_context = build_semantic_context(business_input or {}, model)
    pipeline_plan = build_warehouse_pipeline_plan(model, semantic_context)
    use_warehouse_profile = bool(pipeline_plan.get("raw_tables") and pipeline_plan.get("staging_tables"))
    generation_profile = (
        build_warehouse_generation_profile(model, pipeline_plan, rows_per_table)
        if use_warehouse_profile
        else None
    )
    table_row_counts = (
        generation_profile.get("table_row_counts", {})
        if generation_profile
        else {table.name: rows_per_table for table in model.tables}
    )
    reference_resolver = ReferenceDataResolver(business_input or {})
    entity_store = {}
    stats = {
        "truncated_values": 0,
        "numeric_bounded_values": 0,
        "length_limited_columns": [],
        "fallback_columns_used": set(),
        "fallback_to_ddl_inference_count": 0,
        "unique_adjustment_warnings": [],
        "fk_safe_unique_adjustments": set(),
        "composite_unique_adjustments": set(),
        "primary_key_repairs": set(),
        "generic_fallback_values": 0,
        "calculated_columns": set(),
        "calculation_warnings": [],
        "type_normalization_warnings": [],
        "semantic_types": {},
        "semantic_context_terms": list(getattr(semantic_context, "domain_terms", [])[:10]),
        "reference_data_matches": set(),
        "entity_reuse_events": set(),
        "relationship_generation_events": set(),
        "check_in_value_sources": set(),
        "ddl_type_corrections": set(),
        "varchar_length_corrections": set(),
        "incompatible_reuse_corrections": set(),
        "calculation_corrections": set(),
        "date_rule_corrections": set(),
        "raw_payload_alignment_events": set(),
        "generation_profile": generation_profile or {},
    }
    for semantic in getattr(semantic_context, "column_semantics", {}).values():
        stats["semantic_types"].setdefault(semantic.semantic_type, 0)
        stats["semantic_types"][semantic.semantic_type] += 1

    for table in table_generation_order(model):
        table_rows = table_row_counts.get(table.name, rows_per_table)
        _detect_constraint_capacity(table, table_rows)
        rows = []
        seen_unique = defaultdict(set)
        seen_primary_keys = set()
        for index in range(1, table_rows + 1):
            row = {}
            for column in table.columns:
                if column.max_length and column.name not in stats["length_limited_columns"]:
                    stats["length_limited_columns"].append(column.name)
                if column.is_primary_key:
                    row[column.name] = _pk_value(column, index, table.name, stats)
                    continue
                value = _check_constraint_value(table, column, index, stats)
                if value is None:
                    stats["fallback_columns_used"].add(f"{table.name}.{column.name}")
                    stats["fallback_to_ddl_inference_count"] += 1
                    value = _fallback_value(fake, rng, table, column, index, stats, semantic_context, reference_resolver)
                row[column.name] = value
            for fk in table.foreign_keys:
                parent = table_map[fk.parent_table.lower()]
                parent_rows = generated[parent.name]
                parent_row = parent_rows[(index - 1) % len(parent_rows)]
                for child_col, parent_col in zip(fk.child_columns, fk.parent_columns):
                    row[child_col] = parent_row[parent_col]
                    stats.setdefault("relationship_generation_events", set()).add(f"{table.name}.{child_col} -> {parent.name}.{parent_col}")
            _reuse_entity_values(table, row, index, entity_store, stats)
            _apply_semantic_consistency(table, row, index, stats)
            _apply_lifecycle_order(row)
            _finalize_row_values(table, row, index, stats)
            _enforce_primary_key(table, row, seen_primary_keys, index, stats)
            _enforce_unique_constraints(table, row, seen_unique, index, stats, generated)
            _finalize_row_values(table, row, index, stats)
            rows.append(row)
        generated[table.name] = rows
    _finalize_calculations(model, generated, stats)
    if use_warehouse_profile:
        _align_raw_payloads_with_staging(model, generated, pipeline_plan, stats)
    stats["fallback_columns_used"] = sorted(stats["fallback_columns_used"])
    stats["calculated_columns"] = sorted(stats["calculated_columns"])
    stats["fk_safe_unique_adjustments"] = sorted(stats["fk_safe_unique_adjustments"])
    stats["composite_unique_adjustments"] = sorted(stats["composite_unique_adjustments"])
    stats["primary_key_repairs"] = sorted(stats["primary_key_repairs"])
    stats["reference_data_matches"] = sorted(stats["reference_data_matches"])
    stats["entity_reuse_events"] = sorted(stats["entity_reuse_events"])
    stats["relationship_generation_events"] = sorted(stats["relationship_generation_events"])
    stats["check_in_value_sources"] = sorted(stats["check_in_value_sources"])
    stats["ddl_type_corrections"] = sorted(stats["ddl_type_corrections"])
    stats["varchar_length_corrections"] = sorted(stats["varchar_length_corrections"])
    stats["incompatible_reuse_corrections"] = sorted(stats["incompatible_reuse_corrections"])
    stats["calculation_corrections"] = sorted(stats["calculation_corrections"])
    stats["date_rule_corrections"] = sorted(stats["date_rule_corrections"])
    stats["raw_payload_alignment_events"] = sorted(stats["raw_payload_alignment_events"])
    generated["__stats__"] = stats
    generated["__expected_rows__"] = table_row_counts
    return generated
