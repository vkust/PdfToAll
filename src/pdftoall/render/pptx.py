"""PPTX renderer: Document model -> .pptx (python-pptx, MIT).

Layout strategy: geometry-preserving first. Every block keeps its relative
position on the slide (page bbox scaled to 16:9), text boxes are transparent and
autosize, so a PDF page reads like a slide instead of a wall of bullets.
Tables become native PowerPoint tables (editable), never images.
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Emu, Inches, Pt

from ..model import Document, Page

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
MAX_TABLE_ROWS = 12
MAX_TABLE_COLS = 8


def _scale(page: Page) -> tuple[float, float]:
    return SLIDE_W_IN / page.width, SLIDE_H_IN / page.height


def _add_text(slide, text: str, x: float, y: float, w: float, h: float, size: float, bold: bool = False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(max(w, 0.3)), Inches(max(h, 0.25)))
    tf = box.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    run = para.add_run()
    run.text = text
    run.font.size = Pt(max(6, min(size, 40)))
    run.font.bold = bold
    return box


def _add_table(slide, rows: list[list[str]], x: float, y: float, w: float):
    rows = rows[:MAX_TABLE_ROWS]
    cols = min(max(len(r) for r in rows), MAX_TABLE_COLS)
    rows = [r[:cols] for r in rows]
    shape = slide.shapes.add_table(len(rows), cols, Inches(x), Inches(y), Inches(max(w, 1.0)), Inches(0.3 * len(rows)))
    table = shape.table
    for r, row in enumerate(rows):
        for c in range(cols):
            cell = table.cell(r, c)
            cell.text = row[c] if c < len(row) else ""
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.font.bold = r == 0


def render_pptx(doc: Document, out_path: str, title_slides: bool = True) -> str:
    prs = Presentation()
    prs.slide_width = Emu(int(SLIDE_W_IN * 914400))
    prs.slide_height = Emu(int(SLIDE_H_IN * 914400))
    blank = prs.slide_layouts[6]

    if title_slides and doc.title:
        cover = prs.slides.add_slide(prs.slide_layouts[0])
        cover.shapes.title.text = doc.title
        cover.placeholders[1].text = f"Converted from PDF · {doc.page_count} pages"

    for page in doc.pages:
        slide = prs.slides.add_slide(blank)
        sx, sy = _scale(page)
        for block in page.blocks:
            x0, top, x1, bottom = block.bbox
            x, y = x0 * sx, top * sy
            w, h = max((x1 - x0) * sx, 0.6), max((bottom - top) * sy, 0.25)
            if block.kind == "table" and block.table and block.table.rows:
                _add_table(slide, block.table.normalized(), x, y, min(w, SLIDE_W_IN - x - 0.2))
            elif block.kind == "image":
                continue
            elif block.text:
                size = (block.font_size or 11) * 0.95
                _add_text(slide, block.text, x, y, w, h, size, bold=block.bold or block.kind == "heading")

    prs.save(out_path)
    return out_path
