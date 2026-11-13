"""API smoke tests (needs the `api` extra: pip install -e '.[api,dev]')."""

from __future__ import annotations

import io
import zipfile

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from pdftoall.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["engines"]["native"] is True


def test_convert_single_and_zip(sample_pdf):
    data = open(sample_pdf, "rb").read()

    r = client.post("/convert", files={"file": ("sample.pdf", io.BytesIO(data), "application/pdf")},
                    data={"formats": "docx"})
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"

    r = client.post("/convert", files={"file": ("sample.pdf", io.BytesIO(data), "application/pdf")},
                    data={"formats": "docx,xlsx"})
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
    assert any(n.endswith(".docx") for n in names) and any(n.endswith(".xlsx") for n in names)


def test_convert_rejects_unknown_format(sample_pdf):
    data = open(sample_pdf, "rb").read()
    r = client.post("/convert", files={"file": ("sample.pdf", io.BytesIO(data), "application/pdf")},
                    data={"formats": "docx,exe"})
    assert r.status_code == 422
