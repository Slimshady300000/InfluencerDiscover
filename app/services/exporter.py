from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

FORMULA_PREFIXES = ("=", "+", "-", "@")


def build_candidate_workbook(rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Candidates"
    headers = ["Creator", "Platform", "Followers", "Recent Views", "Engagement Rate", "Score", "Contact"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(
            [
                _safe_cell_value(row["creator"]),
                _safe_cell_value(row["platform"]),
                row["followers"],
                row["recent_views"],
                row["engagement_rate"],
                row["score"],
                _safe_cell_value(row["contact"]),
            ]
        )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _safe_cell_value(value):
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value
