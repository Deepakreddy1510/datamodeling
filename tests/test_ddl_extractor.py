from phase2.ddl_extractor import extract_ddl


def test_extracts_sql_fenced_create_statements():
    markdown = """
# SQL DDL
```sql
CREATE SCHEMA analytics;
CREATE TABLE analytics.customer (customer_id integer PRIMARY KEY, name text);
```
"""
    ddl = extract_ddl(markdown)
    assert "CREATE SCHEMA analytics" in ddl
    assert "CREATE TABLE analytics.customer" in ddl
