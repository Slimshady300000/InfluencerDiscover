from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font


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
                row["creator"],
                row["platform"],
                row["followers"],
                row["recent_views"],
                row["engagement_rate"],
                row["score"],
                row["contact"],
            ]
        )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
