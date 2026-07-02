from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from decimal import Decimal
import random
import uuid

from faker import Faker


class SyntheticDataError(Exception):
    pass


SOURCE_FILES = [
    "top_countries.csv",
    "top_devices.csv",
    "top_browsers.csv",
    "top_operating_systems.csv",
    "top_pages.csv",
    "top_referrers.csv",
    "top_utm_parameters.csv",
    "top_events.csv",
    "synthetic_web_sessions.csv",
]
DEVICES = ["Desktop", "Mobile", "Tablet"]
BROWSERS = ["Chrome", "Safari", "Edge", "Firefox", "Samsung Internet", "Opera"]
OPERATING_SYSTEMS = ["Windows", "macOS", "iOS", "Android", "Linux", "Chrome OS"]
PAGES = ["/", "/vehicle-search", "/used-cars", "/electric-cars", "/finance", "/valuation", "/contact", "/checkout"]
REFERRERS = ["google.com", "bing.com", "facebook.com", "autotrader.co.uk", "direct", "email_campaign"]
UTM_VALUES = ["google_cpc", "facebook_paid", "email_june", "organic_search", "direct_none", "display_retargeting"]
EVENTS = ["page_view", "search_started", "vehicle_viewed", "finance_clicked", "lead_submitted", "valuation_started", "call_clicked"]
MARKETS = ["United Kingdom", "England", "Scotland", "Wales", "Northern Ireland", "London", "Manchester", "Birmingham", "Leeds", "Glasgow"]
CAMPAIGNS = ["used_car_search", "ev_awareness", "finance_offer", "valuation_campaign", "retargeting_campaign"]
VEHICLE_SEGMENTS = ["used_petrol", "used_diesel", "used_hybrid", "used_ev", "suv", "hatchback", "premium_used"]
STATUSES = ["started", "completed", "failed", "validated", "active", "inactive", "pending"]


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
    value = values[(index - 1) % len(values)]
    return _bounded(value, column, stats)


def _pk_value(column, index, table_name, stats):
    dtype = column.data_type.lower()
    if "uuid" in dtype:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table_name}.{column.name}.{index}"))
    if any(token in dtype for token in ["int", "serial"]):
        return index
    return _bounded(f"{table_name}_{column.name}_{index:03d}", column, stats)


def _domain_value(name, column, index, table_names, stats):
    if name == "source_file_name" or ("file" in name and "name" in name):
        return _cycle(SOURCE_FILES, index, column, stats)
    if name == "target_table_name":
        return _cycle(table_names, index, column, stats)
    if "raw_device" in name or name in {"device", "device_type", "device_name"}:
        return _cycle(DEVICES, index, column, stats)
    if "raw_browser" in name or "browser" in name:
        return _cycle(BROWSERS, index, column, stats)
    if "raw_operating_system" in name or "operating_system" in name or name in {"os", "os_name"}:
        return _cycle(OPERATING_SYSTEMS, index, column, stats)
    if "raw_page" in name or name in {"page", "page_path", "landing_page"}:
        return _cycle(PAGES, index, column, stats)
    if "raw_referrer" in name or "referrer" in name:
        return _cycle(REFERRERS, index, column, stats)
    if "raw_utm" in name or "utm" in name:
        return _cycle(UTM_VALUES, index, column, stats)
    if "raw_event" in name or "event" in name:
        return _cycle(EVENTS, index, column, stats)
    if "campaign_theme" in name or name in {"campaign", "campaign_name"}:
        return _cycle(CAMPAIGNS, index, column, stats)
    if "vehicle_segment" in name or "segment" in name:
        return _cycle(VEHICLE_SEGMENTS, index, column, stats)
    if "country" in name or "market" in name or "region" in name:
        return _cycle(MARKETS, index, column, stats)
    if name == "load_status" or name.endswith("status") or name == "status":
        return _cycle(STATUSES, index, column, stats)
    return None


def _short_email(index, column, stats):
    if column.max_length and column.max_length < 18:
        return _bounded(f"u{index}@x.co", column, stats)
    domain = "example.com"
    value = f"user{index:03d}@{domain}"
    return _bounded(value, column, stats)


def _value_for_column(fake, rng, table, column, index, table_names, stats):
    name = column.name.lower()
    dtype = column.data_type.lower()
    if column.is_primary_key:
        return _pk_value(column, index, table.name, stats)

    domain_value = _domain_value(name, column, index, table_names, stats)
    if domain_value is not None:
        return domain_value

    if "email" in name:
        return _short_email(index, column, stats)
    if "phone" in name:
        return _bounded(f"+4412345{index:05d}", column, stats)
    if "person_name" in name or name in {"contact_name", "customer_name"}:
        return _bounded(fake.name(), column, stats)
    if "first_name" in name:
        return _bounded(fake.first_name(), column, stats)
    if "last_name" in name:
        return _bounded(fake.last_name(), column, stats)
    if "address" in name:
        return _bounded(fake.street_address(), column, stats)
    if "city" in name:
        return _bounded(_cycle(MARKETS[-5:], index, column, stats), column, stats)
    if "name" in name:
        return _bounded(f"{column.name}_{index:03d}", column, stats)
    if "date" in dtype or "date" in name:
        return date.today() - timedelta(days=rng.randint(0, 730))
    if "timestamp" in dtype or "time" in name:
        return datetime.now().replace(microsecond=0) - timedelta(days=rng.randint(0, 730), seconds=rng.randint(0, 86400))
    if "bool" in dtype:
        return index % 2 == 0
    if any(token in dtype for token in ["numeric", "decimal", "double", "float"]):
        return Decimal(f"{rng.randint(1, 9999)}.{rng.randint(0, 99):02d}")
    if any(word in name for word in ["amount", "price", "cost", "total"]):
        return Decimal(f"{rng.randint(1, 9999)}.{rng.randint(0, 99):02d}")
    if any(token in dtype for token in ["int", "serial"]):
        return rng.randint(1, 1000)
    if "uuid" in dtype:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table.name}.{column.name}.{index}"))
    if any(word in name for word in ["description", "comment", "notes"]):
        return _bounded(fake.sentence(nb_words=8), column, stats)
    return _bounded(f"{column.name}_{index:03d}", column, stats)


def generate_synthetic_data(model, rows_per_table=100, seed=12345):
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)
    generated = {}
    table_map = model.table_map()
    table_names = [table.name for table in model.tables]
    stats = {"truncated_values": 0, "length_limited_columns": []}

    for table in table_generation_order(model):
        rows = []
        for index in range(1, rows_per_table + 1):
            row = {}
            for column in table.columns:
                if column.max_length and column.name not in stats["length_limited_columns"]:
                    stats["length_limited_columns"].append(column.name)
                row[column.name] = _value_for_column(fake, rng, table, column, index, table_names, stats)
            for fk in table.foreign_keys:
                parent = table_map[fk.parent_table.lower()]
                parent_rows = generated[parent.name]
                parent_row = parent_rows[(index - 1) % len(parent_rows)]
                for child_col, parent_col in zip(fk.child_columns, fk.parent_columns):
                    row[child_col] = parent_row[parent_col]
            rows.append(row)
        generated[table.name] = rows
    generated["__stats__"] = stats
    return generated
