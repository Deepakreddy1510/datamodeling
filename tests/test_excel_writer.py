import pytest

openpyxl = pytest.importorskip("openpyxl")
load_workbook = openpyxl.load_workbook

from phase2.ddl_parser import parse_ddl
from phase2.excel_writer import write_excel
from phase2.synthetic_data_generator import generate_synthetic_data


def test_write_excel_one_sheet_per_table(tmp_path):
    model = parse_ddl("CREATE TABLE customer (customer_id integer PRIMARY KEY, customer_name text NOT NULL);")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    output = tmp_path / "synthetic.xlsx"
    write_excel(model, data, output)
    workbook = load_workbook(output)
<<<<<<< HEAD
    assert workbook.sheetnames == ["Model_Summary", "customer"]
    summary = workbook["Model_Summary"]
    assert summary["A1"].value == "Synthetic Data Warehouse — Model Summary"
    sheet = workbook["customer"]
    assert sheet.max_row == 101
    assert sheet[1][0].value == "customer_id"
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter.ref == sheet.dimensions
    assert sheet.column_dimensions["A"].width >= 12


def test_write_excel_serializes_dict_and_list_values_as_json(tmp_path):
    model = parse_ddl("CREATE TABLE payloads (payload_id integer PRIMARY KEY, source_payload jsonb, tags jsonb);")
    data = {
        "payloads": [
            {
                "payload_id": 1,
                "source_payload": {"city": "Bengaluru", "active": True},
                "tags": ["fresh", "priority"],
            }
        ]
    }
    output = tmp_path / "payloads.xlsx"
    write_excel(model, data, output)
    workbook = load_workbook(output)
    sheet = workbook["payloads"]
    assert sheet.cell(2, 2).value == '{"active": true, "city": "Bengaluru"}'
    assert sheet.cell(2, 3).value == '["fresh", "priority"]'


def test_write_excel_converts_uuid_and_blocks_formula_injection(tmp_path):
    from uuid import UUID

    model = parse_ddl("CREATE TABLE demo (demo_id uuid PRIMARY KEY, label text);")
    data = {
        "demo": [
            {
                "demo_id": UUID("10000000-0000-4000-8000-000000000001"),
                "label": "=HYPERLINK(\"https://example.com\")",
            }
        ]
    }
    output = tmp_path / "uuid.xlsx"
    write_excel(model, data, output)
    workbook = load_workbook(output)
    sheet = workbook["demo"]
    assert sheet.cell(2, 1).value == "10000000-0000-4000-8000-000000000001"
    assert sheet.cell(2, 2).value.startswith("'=")
=======
    assert workbook.sheetnames == ["customer"]
    sheet = workbook["customer"]
    assert sheet.max_row == 101
    assert sheet[1][0].value == "customer_id"
>>>>>>> personal/main
