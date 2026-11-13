"""DOCX renderer: Document model -> .docx (python-docx, MIT)."""

from __future__ import annotations

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from ..model import Document


def render_docx(doc: Document, out_path: str) -> str:
    d = DocxDocument()
    normal = d.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    if doc.title:
        d.core_properties.title = doc.title
    d.core_properties.comments = f"Converted from PDF by PdfToAll (engine: {doc.engine})"

    for page in doc.pages:
        for block in page.blocks:
            if block.kind == "heading":
                level = min(max(block.level or 1, 1), 4)
                d.add_heading(block.text, level=level)
            elif block.kind == "bullet":
                d.add_paragraph(block.text, style="List Bullet")
            elif block.kind == "caption":
                p = d.add_paragraph(block.text)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.italic = True
                    run.font.size = Pt(9)
            elif block.kind == "table" and block.table and block.table.rows:
                rows = block.table.normalized()
                table = d.add_table(rows=len(rows), cols=len(rows[0]))
                table.style = "Table Grid"
                for r, row in enumerate(rows):
                    for c, cell in enumerate(row):
                        cell_par = table.cell(r, c).paragraphs[0]
                        run = cell_par.add_run(cell)
                        if r == 0:
                            run.bold = True
            elif block.text:
                d.add_paragraph(block.text)

        if page.number != doc.pages[-1].number:
            d.add_page_break()

    d.save(out_path)
    return out_path
