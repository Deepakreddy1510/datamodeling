import datetime
from pathlib import Path

from openpyxl import Workbook


def _excel_safe_value(value):
    """Convert Python values into Excel-safe values."""
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    if isinstance(value, datetime.time):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    return value


def write_excel(model, data, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    for table in model.tables:
        worksheet = workbook.create_sheet(title=table.name[:31])
        headers = [column.name for column in table.columns]
        worksheet.append(headers)

        for row in data.get(table.name, []):
            worksheet.append(
                [_excel_safe_value(row.get(column.name)) for column in table.columns]
            )

    workbook.save(path)