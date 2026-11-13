"""Facade: one call, several target formats."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from .engines import EngineError, get_engine, soffice_path
from .model import Document
from .render.docx import render_docx
from .render.pptx import render_pptx
from .render.xlsx import render_xlsx

SUPPORTED = ("docx", "pptx", "xlsx")
RENDERERS = {"docx": render_docx, "pptx": render_pptx, "xlsx": render_xlsx}
LIBREOFFICE_FILTERS = {
    "docx": "writer_pdf_import",
    "odt": "writer_pdf_import",
    "rtf": "writer_pdf_import",
    "pptx": "impress_pdf_import",
    "odp": "impress_pdf_import",
}


def parse(src: str, engine: str = "native") -> Document:
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    return get_engine(engine).parse(src)  # type: ignore[misc]


def convert(
    src: str,
    out_dir: str | None = None,
    formats: tuple[str, ...] = SUPPORTED,
    engine: str = "native",
    stem: str | None = None,
) -> dict[str, str]:
    """PDF -> {format: output_path}. Returns only formats actually produced."""
    doc = parse(src, engine=engine)
    out_dir = out_dir or os.path.dirname(os.path.abspath(src))
    os.makedirs(out_dir, exist_ok=True)
    stem = stem or Path(src).stem
    results: dict[str, str] = {}
    for fmt in formats:
        fmt = fmt.lower().strip(".")
        if fmt not in RENDERERS:
            raise ValueError(f"unsupported target '{fmt}'; supported: {', '.join(SUPPORTED)}")
        path = os.path.join(out_dir, f"{stem}.{fmt}")
        RENDERERS[fmt](doc, path)
        results[fmt] = path
    return results


def convert_with_libreoffice(src: str, fmt: str, out_dir: str | None = None) -> str:
    """Fast, layout-preserving path: LibreOffice PDF import filters.

    Quality is 'what LibreOffice makes of the page' — good visual fidelity,
    poor editability. Useful as fallback and as a quality baseline.
    """
    fmt = fmt.lower().strip(".")
    if fmt not in LIBREOFFICE_FILTERS:
        raise ValueError(f"LibreOffice path supports {', '.join(LIBREOFFICE_FILTERS)}")
    soffice = soffice_path()
    if not soffice:
        raise EngineError("LibreOffice not found; install libreoffice-writer/impress or run the Docker image")

    out_dir = out_dir or os.path.dirname(os.path.abspath(src))
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_profile:
        cmd = [
            soffice,
            f"-env:UserInstallation=file://{tmp_profile}",
            "--headless", "--norestore",
            "--convert-to", f"{fmt}:{LIBREOFFICE_FILTERS[fmt]}",
            "--outdir", out_dir, os.path.abspath(src),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    expected = os.path.join(out_dir, f"{Path(src).stem}.{fmt}")
    if proc.returncode != 0 or not os.path.exists(expected):
        raise EngineError(f"LibreOffice conversion failed: {proc.stderr.strip()[:400] or proc.stdout.strip()[:400]}")
    return expected


def detect(path: str) -> dict:
    """Cheap pre-flight: is this a scan (needs OCR) or born-digital?"""
    from .ingest import parse_pdf

    doc = parse_pdf(path)
    return {
        "pages": doc.page_count,
        "chars": doc.char_count,
        "tables": len(doc.tables),
        "scanned": doc.scanned,
        "recommended_engine": "docling" if doc.scanned else "native",
    }
