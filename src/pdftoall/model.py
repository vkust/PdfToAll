"""Unified intermediate document model.

Every engine (native pdfplumber, docling, marker, LibreOffice) parses a PDF into
this model; every renderer (DOCX, PPTX, XLSX) consumes it. The model is
deliberately small: what the three Office targets actually need.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BlockKind = Literal["heading", "paragraph", "bullet", "table", "caption", "image", "footer"]


@dataclass
class Table:
    rows: list[list[str]] = field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    @property
    def n_cols(self) -> int:
        return max((len(r) for r in self.rows), default=0)

    def normalized(self) -> list[list[str]]:
        """Pad rows to a rectangle so DOCX/PPTX/XLSX writers never see ragged input."""
        w = self.n_cols
        return [r + [""] * (w - len(r)) for r in self.rows]


@dataclass
class Block:
    kind: BlockKind
    text: str = ""
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    level: int = 0           # heading level (1..3)
    font_size: float = 0.0
    bold: bool = False
    table: Table | None = None


@dataclass
class Page:
    number: int
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        parts = []
        for b in self.blocks:
            if b.kind == "table" and b.table:
                parts.extend("\t".join(r) for r in b.table.rows)
            elif b.text:
                parts.append(b.text)
        return "\n".join(parts)

    @property
    def tables(self) -> list[Table]:
        return [b.table for b in self.blocks if b.kind == "table" and b.table]

    def headings(self) -> list[Block]:
        return [b for b in self.blocks if b.kind == "heading"]


@dataclass
class Document:
    pages: list[Page] = field(default_factory=list)
    source: str = ""
    engine: str = "native"
    title: str = ""
    scanned: bool = False

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def tables(self) -> list[Table]:
        return [t for p in self.pages for t in p.tables]

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)

    def summary(self) -> dict:
        return {
            "source": self.source,
            "engine": self.engine,
            "pages": self.page_count,
            "chars": self.char_count,
            "tables": len(self.tables),
            "scanned": self.scanned,
        }
