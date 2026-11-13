# Disk / memory footprint

Measured 2026-11-13 on a clean Linux box with Python 3.14 (wheels resolved fresh).

## Configurations

| Setup | Disk | RAM floor | Note |
|---|---|---|---|
| repo (code, tests, sample PDF) | < 5 MB | — | 13 files of Python, ~1.4 kLOC |
| native runtime (`pip install -e .`) | 172 MB (venv) | ~120 MB | pdfplumber + 3 renderers + FastAPI |
| + LibreOffice bridge | +186 MB download / +765 MB installed | ~250 MB per soffice process | `libreoffice-{writer,impress,calc}-nogui` |
| + docling | +~2 GB | ~2–4 GB | torch 539 MB wheel + 530 MB models |
| + marker | +~3–4 GB | ~4 GB | surya layout 250 MB + recognition weights + torch |
| + OCR (PaddleOCR PP-Structure) | +~1 GB | ~1.5 GB | CPU inference is slow but works |
| PDF-Extract-Kit (all models) | +15.1 GB | ~6 GB | not bundled; server-side only |
| Tauri build toolchain (Rust + node_modules + target/) | +~2.5 GB | — | build machine only, not shipped |

## What a released installer looks like

| Distribution | Size |
|---|---|
| native-only (no models, no LO) | ~120–180 MB |
| + LibreOffice bridge | ~1.4–1.8 GB |
| + docling models bundled | ~2.5–3 GB |
| + OCR models | ~3.5–4 GB |

Recommendation: ship **native + LibreOffice** in the base installer and download the neural engine on
first use of a scanned document (~600 MB, one-time), which keeps the download under 2 GB while still
working offline after setup.

## Runtime cost of the native engine

~50 ms/page on one core, ~120 MB RSS for a 100-page document — because pdfplumber is pure Python and
no model is loaded. That is why the native path stays the default on desktop.
