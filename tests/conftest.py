"""Builds a realistic sample PDF (headings, paragraphs, bullets, table) with reportlab."""

from __future__ import annotations

import pytest
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

TITLE = "Quarterly Operations Review"
KPI_ROWS = [
    ["Region", "Q1", "Q2", "Q3", "Q4"],
    ["EMEA", "12 400", "13 100", "14 050", "15 200"],
    ["APAC", "9 800", "10 450", "11 900", "12 750"],
    ["Americas", "21 300", "22 100", "23 400", "24 050"],
]


def build_sample_pdf(path: str) -> str:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, leading=14)
    h1 = ParagraphStyle("H1x", parent=styles["Heading1"], fontSize=20, leading=24, spaceAfter=10)
    h2 = ParagraphStyle("H2x", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=10, spaceAfter=6)

    doc = SimpleDocTemplate(path, pagesize=A4, title=TITLE, author="PdfToAll tests",
                            leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    story = [
        Paragraph(TITLE, h1),
        Paragraph("Prepared by the operations team. Figures are gross and unaudited.", body),
        Spacer(1, 10),
        Paragraph("1. Highlights", h2),
        Paragraph(
            "Throughput grew in every region for the fourth consecutive quarter. The EMEA pipeline "
            "converted at 31 percent, while APAC benefited from the new fulfilment partner. "
            "No material incidents were recorded in the period under review.",
            body,
        ),
        Paragraph("2. Key findings", h2),
        ListFlowable(
            [
                ListItem(Paragraph("Order volume up 18 percent year over year.", body)),
                ListItem(Paragraph("Average handling time down to 2.4 days.", body)),
                ListItem(Paragraph("Returns stayed flat at 3.1 percent of shipped units.", body)),
            ],
            bulletType="bullet",
            start="circle",
        ),
        Spacer(1, 12),
        Paragraph("3. Volume by region", h2),
        Spacer(1, 6),
        Table(
            KPI_ROWS,
            colWidths=[40 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ]
            ),
        ),
        PageBreak(),
        Paragraph("4. Outlook", h2),
        Paragraph(
            "Capacity planning assumes a further 12 percent increase in the first half of next year. "
            "Two contracts are pending signature and are excluded from the forecast below.",
            body,
        ),
        Spacer(1, 10),
        Table(
            [["Scenario", "Units", "Revenue"], ["Base", "58 000", "4.1M"], ["Upside", "64 500", "4.6M"]],
            colWidths=[40 * mm, 30 * mm, 30 * mm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
        PageBreak(),
        Paragraph("5. Appendix", h2),
        Paragraph("Notes, methodology and glossary of terms used in this document.", body),
    ]
    doc.build(story)
    return path


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("fixtures") / "sample.pdf"
    return build_sample_pdf(str(path))


@pytest.fixture(scope="session")
def out_dir(tmp_path_factory) -> str:
    return str(tmp_path_factory.mktemp("out"))
