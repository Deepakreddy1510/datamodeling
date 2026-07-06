from datetime import date, datetime, time
from decimal import Decimal
import json
from pathlib import Path
import re

from openpyxl import Workbook
from openpyxl.styles import Font

INVALID_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")


def _safe_sheet_name(name, used):
    base = INVALID_SHEET_CHARS.sub("_", name)[:31] or "Sheet"
    candidate = base
    suffix = 1
    while candidate in used:
        tail = f"_{suffix}"
        candidate = f"{base[:31 - len(tail)]}{tail}"
        suffix += 1
    used.add(candidate)
    return candidate


def _excel_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, (date, datetime, time)):
        return value
    return value


def write_excel(model, data, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    workbook.remove(workbook.active)
    used = set()
    for table in model.tables:
        sheet = workbook.create_sheet(_safe_sheet_name(table.name, used))
        columns = table.column_names()
        sheet.append(columns)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for row in data.get(table.name, []):
            sheet.append([_excel_value(row.get(column)) for column in columns])
    workbook.save(path)
    return path
