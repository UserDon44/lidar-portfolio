#!/usr/bin/env python3
"""
One-page PDF summary of the QC memo -- output/reports/qc_summary_1page.pdf.

Distinct from build_report.py: that assembles the full memo section by
section; this is a hand-curated single page meant to be pasted into an
email or handed to someone who won't open the full report. Content is
duplicated deliberately (not parsed from qc_memo.md) because a one-pager
needs editorial curation -- which three findings, which three figures --
not a mechanical excerpt.

Figures chosen for standalone legibility (title/legend/colorbar baked
into each PNG, no prior section needed to read them): the deliverable
surface itself, the vendor-accuracy comparison, and the density/QL2
coverage map. The flight-line-offset and roof/pad findings are covered
in the text bullets instead of a second/third near-duplicate diff map --
three visually distinct figures read better on one dense page than three
similar-looking ones.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_report import make_image, inline_markdown  # noqa: E402

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

# Project root, resolved from this file's own location so these scripts
# run from any checkout rather than one hardcoded directory.
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "reports" / "qc_summary_1page.pdf"
PAGE_W, PAGE_H = letter

FIGURES = [
    ("fig06_hillshade_w120.png",
     "The deliverable: bare-earth hillshade, SMRF-classified from raw returns"),
    ("fig01_vendor_diff.png",
     "Accuracy: 0.162 ft RMSE vs. vendor's own classification (clears QL2)"),
    ("fig03_density_ql2.png",
     "Coverage: meets QL2 on average, 19.4% of cells locally short"),
]

ss = getSampleStyleSheet()
title_style = ParagraphStyle("title", parent=ss["Title"], fontSize=16, spaceAfter=2)
sub_style = ParagraphStyle("sub", parent=ss["BodyText"], fontSize=9, leading=12,
                            textColor=colors.HexColor("#555555"), spaceAfter=8)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, spaceBefore=6, spaceAfter=4,
                     textColor=colors.HexColor("#1a1a1a"))
body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.3, leading=12.8, spaceAfter=4)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=13, firstLineIndent=-13, spaceAfter=5)
caption = ParagraphStyle("caption", parent=ss["BodyText"], fontSize=7.6, leading=9.5,
                          alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceBefore=3)
footer = ParagraphStyle("footer", parent=ss["BodyText"], fontSize=7.8, leading=10,
                         textColor=colors.HexColor("#666666"), spaceBefore=8)

story = []

story.append(Paragraph("LiDAR Bare-Earth DEM — QC Summary", title_style))
story.append(Paragraph(
    "San Xavier District, Pima County, AZ &nbsp;·&nbsp; USGS 3DEP, QL2, Feb 2015 "
    "&nbsp;·&nbsp; 574 acres &nbsp;·&nbsp; EPSG:6405 (International Feet)",
    sub_style))
story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#888888")))
story.append(Spacer(1, 6))

story.append(Paragraph(
    "Bare-earth DEM built from raw LiDAR returns — not the vendor's delivered "
    "classification — and independently QC'd against the vendor product, "
    "flight-line geometry, and the source collection's own signed accuracy "
    "assessment. <b>Method:</b> ELM + statistical outlier removal + SMRF ground "
    "classification (window 120 ft, slope 0.15, threshold 1.6 ft) → 3 ft IDW "
    "bare-earth surface.", body))

story.append(Paragraph("Key Findings", h2))
findings = [
    "<b>Accuracy — 0.162 ft RMSE</b> vs. the vendor's own delivered ground "
    "surface, clearing the ASPRS QL2 non-vegetated threshold (≤0.328 ft) with margin.",
    "<b>Flight-line offset — ~0.12 ft systematic</b> vertical offset between two "
    "overlapping flight lines in the source collection: a real calibration "
    "artifact in the data, not a processing error.",
    "<b>Coverage — 19.4% of cells locally below QL2 minimum</b> despite a "
    "passing tile-wide average (3.70 pts/m²) — local density needs its own check.",
    "<b>Roof vs. pad — resolved.</b> Crisp rectangular features in the "
    "residential block are graded concrete pads (+2.85 ft), not unremoved "
    "roof returns (would show 8–15 ft); corroborated against current orthoimagery.",
]
for f in findings:
    story.append(Paragraph(f"•&nbsp;&nbsp;{f}", bullet))

story.append(Spacer(1, 4))

cell_w = (PAGE_W - 1.2 * inch - 0.3 * inch) / 3
img_cells, cap_cells = [], []
for fname, cap in FIGURES:
    img_cells.append(make_image(fname, max_w=cell_w, max_h=2.5 * inch))
    cap_cells.append(Paragraph(cap, caption))
fig_table = Table([img_cells, cap_cells], colWidths=[cell_w + 0.15 * inch] * 3)
fig_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("TOPPADDING", (0, 1), (-1, 1), 2),
]))
story.append(fig_table)

story.append(Paragraph(
    "Full 18-page report: output/reports/qc_report.pdf &nbsp;·&nbsp; "
    "Source memo: output/reports/qc_memo.md &nbsp;·&nbsp; "
    "Data: USGS_LPC_Eastern_Pima_County_Lidar_980398.laz", footer))

doc = SimpleDocTemplate(
    str(OUT), pagesize=letter,
    leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    topMargin=0.55 * inch, bottomMargin=0.5 * inch,
    title="LiDAR Bare-Earth DEM — QC Summary",
    author="LiDAR Processing Portfolio",
)
doc.build(story)
print(f"Wrote {OUT}")
print(f"Page count: {doc.page}")
