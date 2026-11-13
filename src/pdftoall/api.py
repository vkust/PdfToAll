"""Local HTTP API — the bridge a Tauri/Electron UI talks to.

Runs on 127.0.0.1 only by default: documents never leave the machine.

    uvicorn pdftoall.api:app --port 8765
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import __version__
from .convert import SUPPORTED, convert, convert_with_libreoffice, detect
from .engines import EngineError, available_engines

app = FastAPI(title="PdfToAll", version=__version__)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "engines": available_engines()}


@app.post("/detect")
async def detect_endpoint(file: UploadFile = File(...)) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, _safe_name(file.filename))
        Path(src).write_bytes(await file.read())
        try:
            return detect(src)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/convert")
async def convert_endpoint(
    file: UploadFile = File(...),
    formats: str = Form("docx,pptx,xlsx"),
    engine: str = Form("native"),
    libreoffice: bool = Form(False),
):
    """Returns one Office file, or a zip when several formats are requested."""
    wanted = tuple(f.strip().lower() for f in formats.split(",") if f.strip())
    bad = [f for f in wanted if f not in SUPPORTED]
    if bad:
        raise HTTPException(status_code=422, detail=f"unsupported formats: {bad}; supported: {list(SUPPORTED)}")

    tmp = tempfile.mkdtemp(prefix="pdftoall-")
    src = os.path.join(tmp, _safe_name(file.filename))
    Path(src).write_bytes(await file.read())
    try:
        if libreoffice:
            produced = {f: convert_with_libreoffice(src, f, tmp) for f in wanted}
        else:
            produced = convert(src, tmp, wanted, engine=engine)
    except EngineError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if len(produced) == 1:
        only = next(iter(produced.values()))
        return FileResponse(only, filename=os.path.basename(only))

    bundle = os.path.join(tmp, "pdftoall.zip")
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in produced.values():
            zf.write(path, arcname=os.path.basename(path))
    return FileResponse(bundle, filename="pdftoall.zip", media_type="application/zip")


def _safe_name(name: str | None) -> str:
    base = os.path.basename(name or "input.pdf")
    return base if base.lower().endswith(".pdf") else f"{base}.pdf"
