from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from decimal import Decimal
import random
import uuid

from faker import Faker


class SyntheticDataError(Exception):
    pass


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


def _pk_value(column, index, table_name):
    dtype = column.data_type.lower()
    if "uuid" in dtype:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table_name}.{column.name}.{index}"))
    if any(token in dtype for token in ["int", "serial"]):
        return index
    return f"{table_name}_{column.name}_{index:03d}"


def _value_for_column(fake, rng, table, column, index):
    name = column.name.lower()
    dtype = column.data_type.lower()
    if column.is_primary_key:
        return _pk_value(column, index, table.name)
    if "email" in name:
        return fake.unique.safe_email()
    if "first_name" in name:
        return fake.first_name()
    if "last_name" in name:
        return fake.last_name()
    if "name" in name:
        return fake.company() if any(word in name for word in ["company", "store", "vendor"]) else fake.name()
    if "phone" in name:
        return fake.phone_number()[:30]
    if "address" in name:
        return fake.street_address()
    if "city" in name:
        return fake.city()
    if "state" in name or "region" in name:
        return fake.state()
    if "postal" in name or "zip" in name:
        return fake.postcode()
    if "country" in name:
        return fake.country()
    if "status" in name:
        return rng.choice(["active", "inactive", "pending", "complete"])
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
        return fake.sentence(nb_words=8)
    return f"{column.name}_{index:03d}"


def generate_synthetic_data(model, rows_per_table=100, seed=12345):
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)
    generated = {}
    table_map = model.table_map()

    for table in table_generation_order(model):
        rows = []
        for index in range(1, rows_per_table + 1):
            row = {}
            for column in table.columns:
                row[column.name] = _value_for_column(fake, rng, table, column, index)
            for fk in table.foreign_keys:
                parent = table_map[fk.parent_table.lower()]
                parent_rows = generated[parent.name]
                parent_row = parent_rows[(index - 1) % len(parent_rows)]
                for child_col, parent_col in zip(fk.child_columns, fk.parent_columns):
                    row[child_col] = parent_row[parent_col]
            rows.append(row)
        generated[table.name] = rows
    return generated
