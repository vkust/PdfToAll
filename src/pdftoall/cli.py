"""PdfToAll CLI: `pdftoall` / `python -m pdftoall`."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .convert import convert, convert_with_libreoffice, detect
from .engines import EngineError, available_engines


def _build() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pdftoall", description="PDF -> DOCX / XLSX / PPTX, locally.")
    p.add_argument("--version", action="version", version=f"pdftoall {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="convert a PDF into Office formats")
    c.add_argument("src")
    c.add_argument("-o", "--out-dir", default=None)
    c.add_argument("-f", "--formats", default="docx,pptx,xlsx")
    c.add_argument("-e", "--engine", default="native", help="native | docling | marker")
    c.add_argument("--libreoffice", action="store_true", help="use the LibreOffice layout-preserving path")
    c.add_argument("--json", action="store_true", help="machine-readable output")

    d = sub.add_parser("info", help="inspect a PDF before converting")
    d.add_argument("src")

    sub.add_parser("engines", help="list engines and availability")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build().parse_args(argv)

    if args.cmd == "engines":
        avail = available_engines()
        for name, ok in avail.items():
            print(f"{name:<10}{'available' if ok else 'not installed'}")
        return 0

    if args.cmd == "info":
        print(json.dumps(detect(args.src), indent=2))
        return 0

    formats = tuple(f.strip() for f in args.formats.split(",") if f.strip())
    try:
        if args.libreoffice:
            from .convert import UNO_INPUT_FILTERS

            usable = tuple(f for f in formats if f in UNO_INPUT_FILTERS)
            skipped = [f for f in formats if f not in UNO_INPUT_FILTERS]
            if skipped:
                print(f"note: LibreOffice path cannot produce {', '.join(skipped)}; skipped", file=sys.stderr)
            if not usable:
                raise ValueError(f"LibreOffice path supports {', '.join(UNO_INPUT_FILTERS)}")
            out = {f: convert_with_libreoffice(args.src, f, args.out_dir) for f in usable}
        else:
            out = convert(args.src, args.out_dir, formats, engine=args.engine)
    except (EngineError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for fmt, path in out.items():
            print(f"{fmt:<6}{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
