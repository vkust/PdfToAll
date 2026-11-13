"""Facade: one call, several target formats."""

from __future__ import annotations

import os
import re
import socket
import subprocess
import time
import zipfile
from pathlib import Path

from .engines import EngineError, get_engine, unoconvert_path
from .model import Document
from .render.docx import render_docx
from .render.pptx import render_pptx
from .render.xlsx import render_xlsx

SUPPORTED = ("docx", "pptx", "xlsx")
RENDERERS = {"docx": render_docx, "pptx": render_pptx, "xlsx": render_xlsx}

# LibreOffice PDF import filters. They are *input* filters, so they must be passed
# via `unoconvert --input-filter`; `soffice --convert-to ext:filter` would treat the
# name as an export filter and fail ("no export filter" / Draw-only output).
UNO_INPUT_FILTERS = {
    "docx": "writer_pdf_import",
    "odt": "writer_pdf_import",
    "rtf": "writer_pdf_import",
    "pptx": "impress_pdf_import",
    "odp": "impress_pdf_import",
}
# When LibreOffice's PDF import is broken/absent it silently writes an error
# document instead of failing. We detect that text and raise instead of shipping it.
IMPORT_ERROR_MARKER = "encrypted and can't be opened"


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


# --------------------------------------------------------------------------- #
# LibreOffice bridge (experimental)
# --------------------------------------------------------------------------- #
def uno_port() -> int:
    return int(os.environ.get("PDFTOALL_UNO_PORT", "2003"))


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def ensure_unoserver(port: int | None = None, wait_s: float = 20.0) -> subprocess.Popen | None:
    """Start unoserver if no listener is up. Returns the process we started, if any."""
    port = port or uno_port()
    if _port_open(port):
        return None
    server = str(Path(unoconvert_path() or "").with_name("unoserver")) if unoconvert_path() else "unoserver"
    proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        [server, "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if _port_open(port):
            return proc
        time.sleep(0.25)
    proc.terminate()
    raise EngineError(f"unoserver did not start on port {port}; start it manually: unoserver --port {port}")


def _extracted_text(path: str) -> str:
    """Best-effort text of an OOXML/ODF file, for sanity checks."""
    try:
        with zipfile.ZipFile(path) as zf:
            chunks = []
            for name in zf.namelist():
                if name.endswith((".xml", ".rtf")) and any(part in name for part in ("document", "slide", "content")):
                    chunks.append(zf.read(name).decode("utf-8", "ignore"))
            return re.sub(r"<[^>]+>", " ", " ".join(chunks))
    except (zipfile.BadZipFile, OSError):
        try:
            return Path(path).read_bytes()[:20000].decode("latin-1", "ignore")
        except OSError:
            return ""


def validate_libreoffice_output(path: str) -> None:
    if not os.path.exists(path) or os.path.getsize(path) < 200:
        raise EngineError(f"LibreOffice produced no usable file at {path}")
    if IMPORT_ERROR_MARKER in _extracted_text(path).lower():
        raise EngineError(
            "LibreOffice PDF import is not working here: it returned its "
            "'PDF file is encrypted and can't be opened' error document. "
            "Install a desktop LibreOffice with the PDF import filter "
            "(libreoffice-draw + writer/impress), or use the native engine."
        )


def convert_with_libreoffice(src: str, fmt: str, out_dir: str | None = None) -> str:
    """Layout-preserving fallback through LibreOffice's PDF import filters.

    Experimental: quality is 'what LibreOffice makes of the page' — visual
    fidelity at the cost of editability. Requires `unoconvert` (pip install
    unoserver) plus a LibreOffice build whose PDF import actually works.
    """
    fmt = fmt.lower().strip(".")
    if fmt not in UNO_INPUT_FILTERS:
        raise ValueError(
            f"LibreOffice path supports {', '.join(UNO_INPUT_FILTERS)}; "
            "use the native engine for XLSX"
        )
    conv = unoconvert_path()
    if not conv:
        raise EngineError(
            "unoconvert not found. Install: apt install libreoffice libuno-python3 (python3-uno) "
            "&& python3 -m pip install unoserver"
        )

    out_dir = out_dir or os.path.dirname(os.path.abspath(src))
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, f"{Path(src).stem}.{fmt}")
    if os.path.exists(target):
        os.remove(target)

    started = ensure_unoserver()
    try:
        cmd = [
            conv,
            "--input-filter", UNO_INPUT_FILTERS[fmt],
            "--convert-to", fmt,
            os.path.abspath(src),
            target,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240, check=False)
    finally:
        if started is not None:
            started.terminate()
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise EngineError(f"unoconvert failed: {detail[:400]}")
    validate_libreoffice_output(target)
    return target


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
