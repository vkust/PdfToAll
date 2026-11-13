"""XLSX renderer: Document model -> .xlsx (openpyxl, MIT).

One worksheet per detected table (plus an index sheet), so numeric data stays
usable for further work instead of being flattened into text.
"""

from __future__ import annotations

import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..model import Document

HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _safe_title(name: str) -> str:
    name = re.sub(r"[\[\]:*?/\\]", "_", name).strip() or "Sheet"
    return name[:31]


def _looks_numeric(v: str) -> bool:
    v = v.replace(" ", "").replace("\u00a0", "")
    if not v or len(v) > 24:
        return False
    v = v.replace(",", ".")
    return bool(re.fullmatch(r"[-+]?\d+(\.\d+)?%?", v))


def _cell_value(v: str):
    if not _looks_numeric(v):
        return v
    raw = v.replace(" ", "").replace("\u00a0", "").replace(",", ".").rstrip("%")
    try:
        return float(raw)
    except ValueError:
        return v


def render_xlsx(doc: Document, out_path: str) -> str:
    wb = Workbook()
    index = wb.active
    index.title = "Index"
    index.append(["Page", "Block", "Type", "Text / Table size"])
    for cell in index[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT

    table_no = 0
    for page in doc.pages:
        for bi, block in enumerate(page.blocks, start=1):
            label = ""
            if block.kind == "table" and block.table and block.table.rows:
                table_no += 1
                ws = wb.create_sheet(_safe_title(f"P{page.number}_T{table_no}"))
                for row in block.table.normalized():
                    ws.append([_cell_value(c) for c in row])
                for c in range(1, ws.max_column + 1):
                    ws.cell(row=1, column=c).fill = HEADER_FILL
                    ws.cell(row=1, column=c).font = HEADER_FONT
                    width = max((len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, ws.max_row + 1)), default=8)
                    ws.column_dimensions[get_column_letter(c)].width = min(max(width + 2, 10), 60)
                for row in ws.iter_rows(min_row=2):
                    for cell in row:
                        if isinstance(cell.value, float):
                            cell.number_format = "#,##0.##"
                ws.freeze_panes = "A2"
                label = f"{len(block.table.rows)}x{block.table.n_cols} table"
            else:
                label = (block.text or "")[:120]
            index.append([page.number, bi, block.kind, label])

    for c, width in zip("ABCD", (8, 8, 14, 90), strict=False):
        index.column_dimensions[c].width = width
    for row in index.iter_rows(min_row=2, max_col=4):
        row[3].alignment = Alignment(wrap_text=False, vertical="top")
    index.freeze_panes = "A2"

    wb.save(out_path)
    return out_path
