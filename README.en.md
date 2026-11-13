# PdfToAll

[![ci](https://github.com/vkust/PdfToAll/actions/workflows/ci.yml/badge.svg)](https://github.com/vkust/PdfToAll/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

PDF → **DOCX · XLSX · PPTX**, converted **on your machine**. No uploads, no accounts, no per-file limits.

*Русская версия: [README.md](README.md)*

The project exists because the PDF-to-Office space is either closed (Adobe, ABBYY, Wondershare) or
cloud-only (Smallpdf, iLovePDF, ConvertAPI) — and cloud means your contracts, medical records and
financial statements leave your laptop. Even the strongest open-source PDF app, Stirling-PDF, is a
server product: your document still travels.

**Status:** v0.1.0 — the native conversion pipeline works end to end and is covered by tests.
Neural engines (docling, marker) and the desktop shell are wired in but not yet shipped.

```bash
# text-based PDF, no models, ~50 ms/page
pip install -e .[dev]
pdftoall convert report.pdf -o out/            # -> report.docx, report.pptx, report.xlsx
pdftoall info report.pdf                       # scanned? how many tables? which engine?
pdftoall engines                               # what is installed
```

## What it actually does

| Output | What you get |
|---|---|
| DOCX | Real Word styles (`Heading 1..4`, `List Bullet`), editable paragraphs, native tables |
| PPTX | One slide per PDF page, **geometry preserved** (blocks keep their relative position), native editable tables |
| XLSX | One worksheet per detected table, header row styled, numbers stored as numbers, plus an index sheet |

Not yet: images/figure extraction, vector graphics, fonts matching, page-faithful reflow.
For "looks exactly like the PDF", there is an experimental LibreOffice bridge (`--libreoffice`) — it trades
editability for fidelity and depends on the LibreOffice build, see `docs/libreoffice.md`.

## Architecture

```
PDF ──▶ Engine ────▶ Document model ────▶ Renderers ────▶ .docx / .pptx / .xlsx
        (native |    (Page, Block,      (python-docx,
         docling |    Table; MIT-clean)   python-pptx,
         marker)                          openpyxl)
```

The model is the product's contract: any engine that produces `Document` automatically gets all three
renderers, and any new renderer works with every engine. Engines are swappable per file — a clean
born-digital PDF goes through the native path in milliseconds, a scanned contract goes through
docling/marker OCR.

```
src/pdftoall/
  model.py        Document/Page/Block/Table — the intermediate representation
  ingest.py       native engine: pdfplumber -> model (lines, blocks, headings, bullets, tables)
  engines.py      registry + docling/marker adapters + LibreOffice detection
  convert.py      one-call facade + LibreOffice fallback path
  render/         docx.py, pptx.py, xlsx.py
  api.py          local FastAPI service (127.0.0.1) — the bridge for a Tauri/Electron UI
  cli.py          `pdftoall` command
```

## Engines

| Engine | Install | License | Use when |
|---|---|---|---|
| native | included | MIT | born-digital PDFs, simple layout, speed matters |
| docling | `.[docling]` | MIT | multi-column, complex tables, needs OCR — best license/quality balance |
| marker | `.[marker]` | Apache-2.0 code / OpenRAIL-M weights | degraded scans, highest accuracy; runs on CPU |
| LibreOffice | apt + unoserver | MPL-2.0 | **experimental** (own CI job): layout-preserving path, `--libreoffice` — see `docs/libreoffice.md` |

Deliberately **not** used: PyMuPDF (AGPL-3.0) — see `docs/licensing.md` before adding it.

## API (for the desktop shell)

```bash
uvicorn pdftoall.api:app --port 8765
curl -F file=@report.pdf -F formats=docx,pptx http://127.0.0.1:8765/convert -o out.zip
```

## Disk footprint

Measured on this repo's test machine (`docs/footprint.md` has the breakdown):

- code + tests: **< 5 MB**
- `pip install -e .[dev]`: **172 MB** (venv, incl. FastAPI)
- LibreOffice bridge: **186 MB download / ~765 MB installed**
- + docling: **~2 GB** (torch 539 MB + models 530 MB)
- + marker: **~3–4 GB**
- desktop shell (Tauri + Rust toolchain): **~2.5 GB** build-only

Shipping a desktop build: budget **~1.5 GB installer** with the LibreOffice bridge, **~2.5–3 GB** with
docling bundled, **~150 MB** for the native-only build.

## Roadmap

- [x] native engine + three renderers + CLI + local API + tests
- [ ] image/figure extraction and placement
- [ ] docling engine enabled by default on complex layouts (auto-routing by `detect()`)
- [ ] conversion quality benchmark vs. LibreOffice/Stirling on a public PDF corpus
- [ ] Tauri desktop shell (drag & drop, before/after preview via pdf.js/docxjs/SheetJS, batch mode)
- [ ] OCR path for scans without a GPU
- [ ] signed installers for Windows/macOS/Linux

## License

MIT. See `docs/licensing.md` for the third-party license matrix.
