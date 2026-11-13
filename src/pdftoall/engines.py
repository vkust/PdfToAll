"""Engine registry and adapters.

The native engine is always available and MIT-clean. The neural engines
(docling, marker, MinerU) and the LibreOffice bridge are optional: each adapter
reports `available()` and raises a clear EngineError with an install hint
otherwise. Nothing here downloads models at import time.
"""

from __future__ import annotations

import importlib.util
import shutil
from collections.abc import Callable
from dataclasses import dataclass

from .model import Document


class EngineError(RuntimeError):
    """Raised when an engine is missing or fails."""


@dataclass(frozen=True)
class EngineInfo:
    name: str
    label: str
    license: str
    kind: str            # "native" | "neural" | "office-bridge"
    notes: str
    parse: Callable[[str], Document] | None = None


def _module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


# ---------------------------------------------------------------- native
def _parse_native(path: str) -> Document:
    from .ingest import parse_pdf

    return parse_pdf(path, engine="native")


# ---------------------------------------------------------------- docling
def _parse_docling(path: str) -> Document:
    """docling -> Document. Layout/reading-order quality is much higher than
    native on multi-column pages; DOCX/PPTX still rendered by us."""
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dep
        raise EngineError("docling not installed: pip install 'pdftoall[docling]'") from exc

    from .model import Block, Document, Page, Table

    result = DocumentConverter().convert(path)
    dl_doc = result.document
    pages: list[Page] = []
    current = Page(number=1, width=595.0, height=842.0)
    for item, _level in dl_doc.iterate_items():
        label = str(getattr(item, "label", "text")).lower()
        text = getattr(item, "text", "") or ""
        page_no = 1
        prov = getattr(item, "prov", None) or []
        if prov:
            page_no = int(getattr(prov[0], "page_no", 1))
        if page_no != current.number:
            pages.append(current)
            current = Page(number=page_no, width=current.width, height=current.height)
        if "table" in label:
            rows = []
            try:
                for row in item.data.grid:  # type: ignore[attr-defined]
                    rows.append([c.text for c in row])
            except Exception:
                rows = [[text]] if text else []
            current.blocks.append(Block(kind="table", table=Table(rows=rows)))
        elif "title" in label or "section" in label:
            current.blocks.append(Block(kind="heading", text=text, level=1))
        else:
            current.blocks.append(Block(kind="paragraph", text=text))
    pages.append(current)
    doc = Document(pages=pages, source=path, engine="docling", title=getattr(dl_doc, "name", "") or "")
    doc.scanned = doc.char_count < 40 * max(1, doc.page_count)
    return doc


# ---------------------------------------------------------------- marker
def _parse_marker(path: str) -> Document:
    """marker -> Document. Higher accuracy than docling on degraded scans,
    CPU mode works without a GPU. Model weights are OpenRAIL-M."""
    try:
        from marker.converters.pdf import PdfConverter  # type: ignore
        from marker.models import create_model_dict  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dep
        raise EngineError("marker not installed: pip install 'pdftoall[marker]'") from exc

    from .model import Block, Document, Page

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(path)
    markdown = rendered.markdown if hasattr(rendered, "markdown") else str(rendered)
    pages = [Page(number=1, width=595.0, height=842.0)]
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            pages[0].blocks.append(Block(kind="heading", text=line.lstrip("# ").strip(), level=min(level, 4)))
        elif line.startswith(("- ", "* ")):
            pages[0].blocks.append(Block(kind="bullet", text=line[2:].strip()))
        else:
            pages[0].blocks.append(Block(kind="paragraph", text=line))
    doc = Document(pages=pages, source=path, engine="marker", title="")
    doc.scanned = doc.char_count < 40
    return doc


# ---------------------------------------------------------------- registry
ENGINES: dict[str, EngineInfo] = {
    "native": EngineInfo(
        name="native",
        label="Native (pdfplumber)",
        license="MIT",
        kind="native",
        notes="Zero model downloads, ~50 ms/page, best for born-digital PDFs with simple layout.",
        parse=_parse_native,
    ),
    "docling": EngineInfo(
        name="docling",
        label="docling (IBM)",
        license="MIT",
        kind="neural",
        notes="Layout, reading order, table structure, formulas, OCR. ~0.5 GB models, needs ~2-4 GB RAM.",
        parse=_parse_docling,
    ),
    "marker": EngineInfo(
        name="marker",
        label="marker (Datalab)",
        license="Apache-2.0 code / OpenRAIL-M weights",
        kind="neural",
        notes="Highest accuracy, CPU or GPU. ~1.5 GB models, needs ~4 GB RAM.",
        parse=_parse_marker,
    ),
}


def available_engines() -> dict[str, bool]:
    avail = {"native": True}
    avail["docling"] = _module("docling")
    avail["marker"] = _module("marker")
    return avail


def get_engine(name: str) -> EngineInfo:
    if name not in ENGINES:
        raise EngineError(f"unknown engine '{name}'; known: {', '.join(ENGINES)}")
    return ENGINES[name]


def unoconvert_path() -> str | None:
    """unoconvert (from unoserver) is the only reliable way to force a PDF *import*
    filter; plain `soffice --convert-to` cannot express input filters."""
    return shutil.which("unoconvert")
