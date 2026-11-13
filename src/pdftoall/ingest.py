"""Native PDF ingest: pdfplumber -> Document model.

MIT-only dependency chain (pdfplumber -> pdfminer.six), no PyMuPDF, so the
default path stays safe for a commercial closed-source product.

Heuristics, deliberately simple and explainable:
  * words -> lines (same top, +/- tolerance)
  * lines -> blocks (small vertical gap, similar font size)
  * font size >= 1.18x body size, or bold short line  -> heading
  * leading bullet glyph / "- " / "1."                -> bullet
  * page.find_tables()                                 -> table blocks
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass

import pdfplumber

from .model import Block, Document, Page, Table

BULLET_PREFIXES = ("•", "·", "●", "▪", "-", "*", "—", "\u2013")
# ZapfDingbats/Symbol bullets render as ordinary letters ("l", "n", "u") in the
# text layer; pdfplumber reports them as their own short line.
BULLET_GLYPHS = {"l", "n", "u", "m", "q", "¡", "Ø", "·", "•"}
GAP_FACTOR = 1.55      # vertical gap / font size above which a new block starts
HEADING_RATIO = 1.18


@dataclass
class _Line:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float
    bold: bool
    marker: bool = False


def _lines_from_chars(chars: list[dict], y_tol: float = 2.0) -> list[_Line]:
    """Group characters into visual lines, keeping font size and weight."""
    rows: list[list[dict]] = []
    for ch in sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"])):
        if not ch.get("text", "").strip():
            continue
        for row in rows:
            if abs(row[-1]["top"] - ch["top"]) <= y_tol:
                row.append(ch)
                break
        else:
            rows.append([ch])

    lines: list[_Line] = []
    for row in rows:
        row.sort(key=lambda c: c["x0"])
        # rebuild text respecting spaces implied by gaps
        buf: list[str] = []
        for i, ch in enumerate(row):
            if i:
                prev = row[i - 1]
                gap = ch["x0"] - prev["x1"]
                if gap > max(1.0, ch["size"] * 0.22) and not buf[-1].endswith(" "):
                    buf.append(" ")
            buf.append(ch["text"])
        text = "".join(buf).strip()
        if not text:
            continue
        sizes = [c["size"] for c in row]
        fonts = [c.get("fontname", "") for c in row]
        lines.append(
            _Line(
                text=text,
                x0=min(c["x0"] for c in row),
                x1=max(c["x1"] for c in row),
                top=min(c["top"] for c in row),
                bottom=max(c["bottom"] for c in row),
                size=round(statistics.median(sizes), 1),
                bold=sum("bold" in f.lower() for f in fonts) > len(fonts) / 2,
            )
        )
    lines.sort(key=lambda ln: (ln.top, ln.x0))
    for line in lines:
        if len(line.text) <= 2 and (line.text in BULLET_GLYPHS or "dingbat" in line.text.lower()):
            line.marker = True
    return _merge_markers(lines)


def _merge_markers(lines: list[_Line]) -> list[_Line]:
    """Fold a standalone bullet glyph into the text line that follows it."""
    out: list[_Line] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if line.marker and nxt is not None and abs(nxt.top - line.top) <= max(line.size, nxt.size) * 0.9:
            marker = line.text if line.text in BULLET_PREFIXES else "•"
            nxt.text = f"{marker} {nxt.text}"
            nxt.x0 = min(nxt.x0, line.x0)
            nxt.top = min(nxt.top, line.top)
            nxt.bottom = max(nxt.bottom, line.bottom)
            i += 2 if not nxt.marker else 1
            out.append(nxt)
            continue
        if line.marker:
            line.text = "•"
        out.append(line)
        i += 1
    return out


def _body_size(lines: list[_Line]) -> float:
    """Most common font size weighted by how much text it carries."""
    weight: dict[float, int] = {}
    for line in lines:
        if line.marker:
            continue
        weight[round(line.size, 1)] = weight.get(round(line.size, 1), 0) + len(line.text)
    return max(weight.items(), key=lambda kv: kv[1])[0] if weight else 10.0


def _is_bullet(text: str) -> bool:
    t = text.lstrip()
    if t.startswith(BULLET_PREFIXES):
        return True
    head = t.split(" ", 1)[0]
    return head.rstrip(".)").isdigit() and len(head) <= 3 and t[len(head):len(head) + 2] in (". ", ") ")


def _inside(x: float, y: float, bbox: tuple[float, float, float, float], pad: float = 1.0) -> bool:
    x0, top, x1, bottom = bbox
    return x0 - pad <= x <= x1 + pad and top - pad <= y <= bottom + pad


def _blocks_from_lines(lines: list[_Line], body_size: float) -> list[Block]:
    blocks: list[Block] = []
    cur: list[_Line] = []

    def flush() -> None:
        if not cur:
            return
        text = " ".join(ln.text for ln in cur).strip()
        text = " ".join(text.split())
        size = statistics.median([ln.size for ln in cur])
        bold = all(ln.bold for ln in cur)
        if _is_bullet(text):
            kind, level = "bullet", 0
            text = text.lstrip("".join(BULLET_PREFIXES) + " ").strip()
        elif size >= body_size * HEADING_RATIO:
            ratio = size / body_size
            kind, level = "heading", (1 if ratio >= 1.65 else 2 if ratio >= 1.35 else 3)
        elif size < body_size * 0.9 and len(text) < 80 and text.lower().startswith(("figure", "fig.", "table", "рис", "табл")):
            kind, level = "caption", 0
        else:
            kind, level = "paragraph", 0
        if bold and kind == "paragraph" and len(text) < 90 and not text.endswith("."):
            kind, level = "heading", 3
        blocks.append(
            Block(
                kind=kind,
                text=text,
                bbox=(min(ln.x0 for ln in cur), cur[0].top, max(ln.x1 for ln in cur), cur[-1].bottom),
                level=level,
                font_size=round(size, 1),
                bold=bold,
            )
        )

    for line in lines:
        if not cur:
            cur = [line]
            continue
        prev = cur[-1]
        gap = line.top - prev.bottom
        line_gap_ok = gap <= max(prev.size, line.size) * 0.95
        same_style = abs(line.size - prev.size) <= 0.6
        same_para = (
            line_gap_ok
            and same_style
            and not _is_bullet(line.text)
            and not prev.text.endswith(("!", "?"))
        )
        if same_para:
            cur.append(line)
        else:
            flush()
            cur = [line]
    flush()
    return blocks


def parse_pdf(path: str, engine: str = "native") -> Document:
    """Parse a born-digital PDF into the unified model."""
    pages: list[Page] = []
    with pdfplumber.open(path) as pdf:
        meta_title = (pdf.metadata or {}).get("Title") or ""
        for pno, page in enumerate(pdf.pages, start=1):
            words = page.chars
            tables: list[Table] = []
            table_boxes: list[tuple[float, float, float, float]] = []
            try:
                for found in page.find_tables():
                    rows = [[(" ".join((c or "").split())) for c in row] for row in found.extract()]
                    rows = [r for r in rows if any(cell for cell in r)]
                    if not rows:
                        continue
                    bbox = tuple(round(v, 2) for v in found.bbox)
                    tables.append(Table(rows=rows, bbox=bbox))
                    table_boxes.append(found.bbox)
            except Exception as exc:  # table detection is best-effort; text still parses
                logging.getLogger(__name__).debug("table detection failed on page %s: %s", pno, exc)

            if table_boxes:
                words = [
                    c for c in words
                    if not any(_inside((c["x0"] + c["x1"]) / 2, (c["top"] + c["bottom"]) / 2, b) for b in table_boxes)
                ]

            lines = _lines_from_chars(words)
            body = _body_size(lines)
            blocks = _blocks_from_lines(lines, body)

            for t in tables:
                blocks.append(Block(kind="table", bbox=t.bbox or (0.0, 0.0, 0.0, 0.0), table=t))
            blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))

            pages.append(Page(number=pno, width=float(page.width), height=float(page.height), blocks=blocks))

    doc = Document(pages=pages, source=path, engine=engine, title=meta_title)
    chars = doc.char_count
    doc.scanned = chars < 40 * max(1, doc.page_count)
    return doc
