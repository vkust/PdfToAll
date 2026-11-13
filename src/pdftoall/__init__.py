"""PdfToAll — PDF to DOCX / XLSX / PPTX, locally.

Public API:
    >>> from pdftoall import convert
    >>> convert("report.pdf", "out", ("docx", "pptx"), engine="native")
"""

__version__ = "0.1.0"

from .convert import convert, convert_with_libreoffice, detect, parse
from .model import Block, Document, Page, Table

__all__ = [
    "Block",
    "Document",
    "Page",
    "Table",
    "__version__",
    "convert",
    "convert_with_libreoffice",
    "detect",
    "parse",
]
