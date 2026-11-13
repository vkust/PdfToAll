# Licensing — what we may and may not vendor

Rule of thumb: anything AGPL/GPL stays **behind a process boundary** (separate binary, container, or
user-installed dependency), never imported into `pdftoall` itself. Our own code stays MIT.

## Used directly (safe to ship in a closed-source product)

| Component | License | Role |
|---|---|---|
| pdfplumber / pdfminer.six | MIT | native PDF ingest |
| python-docx | MIT | DOCX render |
| python-pptx | MIT | PPTX render |
| openpyxl | MIT | XLSX render |
| pypdf | BSD-3 | page count, metadata, PDF merge/split later |
| FastAPI / Starlette | MIT / BSD-3 | local API |
| reportlab | BSD | test fixtures only |

## Optional engines

| Component | License | Constraint |
|---|---|---|
| docling (code) | MIT | models carry their own licenses (layout/TableFormer) — check before redistribution |
| marker (code) | Apache-2.0 | ✅ commercial use |
| marker (weights) | OpenRAIL-M | free for research, personal use and startups under a revenue threshold; larger companies need a commercial license from Datalab |
| MinerU | Apache-2.0 + additional terms | read §1 of LICENSE.md: commercial licensing terms apply above a usage threshold |
| MinerU2PPT | **none stated** | all rights reserved by default — ideas only, do not copy code |
| PaddleOCR | Apache-2.0 | ✅ |
| surya | Apache-2.0 code, OpenRAIL-M weights | same caveat as marker |

## Process-boundary only

| Component | License | How to use |
|---|---|---|
| LibreOffice | MPL-2.0 (+ LGPL parts) | spawn `soffice --headless` as a separate process; do not link into our binary |
| pandoc | GPL-2.0 | invoke as an external binary if we ever add Markdown→Office |
| PDF-Extract-Kit | AGPL-3.0 | separate service/container only |
| PyMuPDF | **AGPL-3.0** | avoid; if its speed becomes essential, buy the Artifex commercial license |

## Trademarks

`PdfToAll` is a descriptive name; do not use "Adobe", "Microsoft Word", "PowerPoint" or "Excel" as
product-name components. Say "converts to DOCX/PPTX/XLSX" in marketing copy.
