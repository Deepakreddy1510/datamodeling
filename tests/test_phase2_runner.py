import sys
import types

sys.modules.setdefault("openpyxl", types.SimpleNamespace(Workbook=object))
sys.modules.setdefault("openpyxl.styles", types.SimpleNamespace(Font=lambda **kwargs: None))
import phase2_runner


def test_phase2_dry_run_handles_date_key_catalog_patterns(tmp_path, monkeypatch):
    yaml_path = tmp_path / "business.yaml"
    yaml_path.write_text(
        """
business_name: Demo
business_type: Retail
business_description: Demo analytical model.
model_purpose: Reporting
main_business_processes: [Sales]
key_business_entities: [Date, Sales]
business_relationships: [Sales occur on dates]
entity_attributes: {Date: [date_key], Sales: [sales_key, order_date_key]}
reporting_requirements: [Sales by date]
target_database: PostgreSQL
expected_output: Data warehouse
""",
        encoding="utf-8",
    )
    phase1_output = tmp_path / "final_output.md"
    phase1_output.write_text(
        """
# SQL DDL
```sql
CREATE TABLE dim_date (date_key integer PRIMARY KEY, full_date date);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  order_date_key integer
);
```

# Synthetic Data Value Catalog
BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{
  "business_context": {"business_name": "Demo"},
  "table_column_rules": [
    {"table_name": "dim_date", "column_name": "date_key", "value_pattern": "YYYYMMDD"},
    {"table_name": "dim_date", "column_name": "full_date", "date_rule": "between 2026-07-06 and 2026-07-10"},
    {"table_name": "fact_sales", "column_name": "order_date_key", "relationship_rule": "choose existing dim_date.date_key"}
  ],
  "business_rules": [],
  "generation_assumptions": []
}
END_SYNTHETIC_VALUE_CATALOG_JSON
""",
        encoding="utf-8",
    )
    excel_output = tmp_path / "synthetic.xlsx"
    output_dir = tmp_path / "reports"
    wrote_excel = {}
    monkeypatch.setattr(phase2_runner, "write_excel", lambda model, data, path: wrote_excel.setdefault("path", path))
    monkeypatch.setattr(sys, "argv", [
        "phase2_runner.py",
        "--yaml", str(yaml_path),
        "--phase1-output", str(phase1_output),
        "--output-dir", str(output_dir),
        "--rows-per-table", "3",
        "--excel-output", str(excel_output),
        "--no-load-to-postgres",
    ])

    assert phase2_runner.main() == 0
    assert wrote_excel["path"] == str(excel_output)
    assert (output_dir / "synthetic_data_generation_report.md").exists()
    assert (output_dir / "validation_report.md").exists()
