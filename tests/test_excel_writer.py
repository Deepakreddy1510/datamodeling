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
    assert workbook.sheetnames == ["customer"]
    sheet = workbook["customer"]
    assert sheet.max_row == 101
    assert sheet[1][0].value == "customer_id"
