"""End-to-end conversion tests: the assertions read the produced Office files back."""

from __future__ import annotations

import os

import pytest
from docx import Document as Docx
from openpyxl import load_workbook
from pptx import Presentation

from pdftoall import convert, detect, parse
from pdftoall.cli import main
from pdftoall.engines import EngineError, available_engines, unoconvert_path


def test_parse_model(sample_pdf):
    doc = parse(sample_pdf, engine="native")
    assert doc.page_count >= 3
    assert doc.char_count > 800
    assert doc.scanned is False
    assert any(b.kind == "heading" for p in doc.pages for b in p.blocks)
    assert len(doc.tables) >= 2, "both tables on the sample PDF must be detected"


def test_detect_recommends_native(sample_pdf):
    info = detect(sample_pdf)
    assert info["scanned"] is False
    assert info["recommended_engine"] == "native"
    assert info["tables"] >= 2


def test_docx_output(sample_pdf, out_dir):
    out = convert(sample_pdf, out_dir, ("docx",))["docx"]
    assert os.path.getsize(out) > 5000
    d = Docx(out)
    text = "\n".join(p.text for p in d.paragraphs)
    assert "Quarterly Operations Review" in text
    assert "Order volume up 18 percent" in text
    styles = {p.style.name for p in d.paragraphs}
    assert any(s.startswith("Heading") for s in styles), styles
    assert "List Bullet" in styles, styles
    assert len(d.tables) >= 2
    assert d.tables[0].cell(0, 0).text.strip() == "Region"


def test_pptx_output(sample_pdf, out_dir):
    out = convert(sample_pdf, out_dir, ("pptx",))["pptx"]
    prs = Presentation(out)
    assert len(prs.slides) >= 3
    tables = [sh for s in prs.slides for sh in s.shapes if sh.has_table]
    assert tables, "tables must be native PowerPoint tables, not images"
    assert tables[0].table.cell(0, 0).text == "Region"
    all_text = " ".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    assert "Outlook" in all_text


def test_xlsx_output(sample_pdf, out_dir):
    out = convert(sample_pdf, out_dir, ("xlsx",))["xlsx"]
    wb = load_workbook(out)
    assert "Index" in wb.sheetnames
    table_sheets = [s for s in wb.sheetnames if s.startswith("P")]
    assert table_sheets, wb.sheetnames
    ws = wb[table_sheets[0]]
    assert ws["A1"].value == "Region"
    assert ws.max_column == 5
    # numbers must survive as numbers, not strings
    assert isinstance(ws.cell(row=2, column=2).value, (int, float))
    assert not isinstance(ws.cell(row=2, column=2).value, str)


def test_cli_convert_all(sample_pdf, out_dir, capsys):
    code = main(["convert", sample_pdf, "-o", out_dir, "-f", "docx,pptx,xlsx", "--json"])
    assert code == 0
    printed = capsys.readouterr().out
    assert "docx" in printed and "pptx" in printed and "xlsx" in printed


def test_cli_engines(capsys):
    assert main(["engines"]) == 0
    out = capsys.readouterr().out
    assert "native" in out
    assert available_engines()["native"] is True


def test_unsupported_target(sample_pdf, out_dir):
    with pytest.raises(ValueError):
        convert(sample_pdf, out_dir, ("pdf",))


@pytest.mark.skipif(unoconvert_path() is None, reason="unoconvert (unoserver) not installed")
def test_libreoffice_fallback(sample_pdf, out_dir):
    """Needs a LibreOffice whose PDF import filter works (see docs/libreoffice.md).

    Many minimal builds ship a broken PDF import; on a dev machine we skip with the
    diagnosis, in CI (PDFTOALL_LO_STRICT=1) the failure must surface.
    """
    from pdftoall import convert_with_libreoffice

    try:
        out = convert_with_libreoffice(sample_pdf, "docx", out_dir)
    except EngineError as exc:
        if os.environ.get("PDFTOALL_LO_STRICT") == "1":
            raise
        pytest.skip(f"LibreOffice PDF import unusable here: {exc}")
    assert os.path.getsize(out) > 5000


def test_libreoffice_missing_is_explicit(monkeypatch, sample_pdf, out_dir):
    import importlib

    conv_mod = importlib.import_module("pdftoall.convert")
    monkeypatch.setattr(conv_mod, "unoconvert_path", lambda: None)
    with pytest.raises(EngineError, match="unoconvert not found"):
        conv_mod.convert_with_libreoffice(sample_pdf, "docx", out_dir)


def test_libreoffice_marker_survives_xml_escaping(tmp_path):
    """LibreOffice writes the apostrophe as &apos;; detection must not depend on it."""
    import importlib
    import zipfile

    conv_mod = importlib.import_module("pdftoall.convert")
    broken = tmp_path / "escaped.docx"
    with zipfile.ZipFile(broken, "w") as zf:
        zf.writestr(
            "word/document.xml",
            "<w:document><w:body><w:p><w:r><w:t>This PDF file is encrypted and can&apos;t "
            "be opened.</w:t></w:r></w:p></w:body></w:document>",
        )
        zf.writestr("padding.bin", "x" * 400)
    with pytest.raises(EngineError, match="PDF import is not working"):
        conv_mod.validate_libreoffice_output(str(broken))


def test_libreoffice_error_document_is_rejected(tmp_path):
    """A broken PDF import yields an error document; we must never ship it."""
    import importlib

    from docx import Document as Docx

    conv_mod = importlib.import_module("pdftoall.convert")
    fake = tmp_path / "broken.docx"
    d = Docx()
    d.add_paragraph("This PDF file is encrypted and can't be opened.")
    d.save(fake)
    with pytest.raises(EngineError, match="PDF import is not working"):
        conv_mod.validate_libreoffice_output(str(fake))
