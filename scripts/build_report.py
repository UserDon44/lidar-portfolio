#!/usr/bin/env python3
"""
Assemble output/reports/qc_memo.md + output/figures/*.png into a single
PDF deliverable: output/reports/qc_report.pdf.

qc_memo.md stays the single source of truth for text -- this script parses
its markdown subset (headers, **bold**, `code`, tables, numbered/bulleted
lists) into reportlab flowables rather than duplicating the memo's content
here. Figures are inserted at the end of whichever section first mentions
them by name (FIGURE_MAP below), in reading order.
"""
import re
from pathlib import Path
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, HRFlowable, KeepTogether, CondPageBreak,
)

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
MEMO = ROOT / "output" / "reports" / "qc_memo.md"
FIG_DIR = ROOT / "output" / "figures"
OUT = ROOT / "output" / "reports" / "qc_report.pdf"

PAGE_W, PAGE_H = letter
MAX_IMG_W = PAGE_W - 1.6 * inch
DPI_SOURCE = 300  # matches DPI in scripts/render_figures.py

# section heading (as it appears after "## " or "### ", stripped) -> figures
# to place at the end of that section, each (filename, caption).
FIGURE_MAP = {
    "2. Processing Method": [
        ("fig06_hillshade_w120.png",
         "Figure 1. Bare-earth hillshade, project SMRF result "
         "(window=120 ft, slope=0.15, threshold=1.6 ft) — the primary "
         "deliverable surface."),
    ],
    "3.1 Vendor comparison": [
        ("fig01_vendor_diff.png",
         "Figure 2. Vendor vs. project DEM difference. RMSE = 0.162 ft, "
         "clears the ASPRS QL2 non-vegetated threshold (\u2264 0.328 ft)."),
    ],
    "3.3 Flight-line (swath) consistency": [
        ("fig02_swath_offset.png",
         "Figure 3. Flight-line overlap offset (line 600 \u2212 line 519). "
         "Mean = +0.124 ft, a systematic offset in the source collection."),
    ],
    "3.5 Point density and coverage": [
        ("fig03_density_ql2.png",
         "Figure 4. First-return point density vs. the QL2 minimum. "
         "Tile-wide mean meets spec; 19.4% of cells locally fall short."),
    ],
    "3.6 DSM/CHM tall-point check": [
        ("fig04_chm.png",
         "Figure 5. Canopy/structure height model (DSM \u2212 DEM). Dark "
         "outlines confirm genuine roofs; the 72.87 ft max is a utility "
         "pole, off-scale."),
    ],
    "5.1 Depression handling": [
        ("fig10_fill_impact.png",
         "Figure 6. Breach/fill impact classified by region. Real terrain "
         "is breach-dominated; fill volume concentrates at the tile edge."),
    ],
    "5.2 Flow routing and stream network": [
        ("fig09_threshold_3panel.png",
         "Figure 7. Stream-extraction threshold comparison \u2014 no single "
         "value clears the wheel-track artifact without losing real "
         "tributaries."),
    ],
    "5.3 Watershed delineation": [
        ("fig08_hydrology_overlay.png",
         "Figure 8. Derived stream network and main-wash watershed "
         "(258.4 ac, stated as a lower bound)."),
    ],
}

APPENDIX_FIGURES = [
    ("fig05_hillshade_vendor.png",
     "Figure A1. Hillshade, vendor delivered classification (baseline)."),
    ("fig07_hillshade_w60.png",
     "Figure A2. Hillshade, SMRF window=60 ft (first attempt) \u2014 "
     "near-identical to the 120 ft result, supporting the roof/pad "
     "finding in \u00a74."),
]


def _code_span(m):
    # slightly smaller than body text -- Courier glyphs run wide, and at
    # body size a long file path (e.g. output/contours/contours_2ft_
    # w120_s0.15_t1.6.gpkg) didn't fit a table column, so reportlab
    # force-split it at an arbitrary character instead of a path
    # boundary. (Tried inserting a U+200B zero-width space after each
    # "/" as a legal break point -- reportlab's base-14 Courier has no
    # glyph for it and rendered a visible tofu box, worse than the
    # original bug. Reverted; the smaller font alone gives enough margin
    # for every path in this memo to fit on one line, checked directly.)
    content = m.group(1)
    return f'<font face="Courier" size="7.6">{content}</font>'


def inline_markdown(text):
    text = text.replace("&", "&amp;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", _code_span, text)
    return text


CACHE_DIR = FIG_DIR / "_pdf_cache"
CACHE_DIR.mkdir(exist_ok=True)
TARGET_DPI = 170  # print-quality on the page, but source PNGs are rendered
                   # at 300 DPI for full-resolution portfolio use elsewhere --
                   # re-encoding down to this cuts the PDF from ~95MB to a
                   # shareable size without visibly softening line art/text


def make_image(fname, max_w=MAX_IMG_W, max_h=8.8 * inch):
    path = FIG_DIR / fname
    cached = CACHE_DIR / fname
    with PILImage.open(path) as im:
        w, h = im.size
        display_w_in = min(max_w / inch, w / DPI_SOURCE)
        target_w_px = int(display_w_in * TARGET_DPI)
        if target_w_px < w:
            im = im.resize((target_w_px, int(h * target_w_px / w)), PILImage.LANCZOS)
            im.save(cached, optimize=True)
            w, h = im.size
        else:
            cached = path
    scale = min(max_w / w, max_h / h)
    return Image(str(cached), width=w * scale, height=h * scale, hAlign="CENTER")


def build_styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("MemoTitle", parent=ss["Title"], fontSize=18, spaceAfter=10))
    ss.add(ParagraphStyle("H1", parent=ss["Heading1"], fontSize=15, spaceBefore=4, spaceAfter=8,
                           textColor=colors.HexColor("#1a1a1a")))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=6,
                           textColor=colors.HexColor("#2a2a2a")))
    ss.add(ParagraphStyle("Body", parent=ss["BodyText"], fontSize=9.7, leading=13.5, spaceAfter=6,
                           alignment=4))  # justified
    ss.add(ParagraphStyle("ListItem", parent=ss["BodyText"], fontSize=9.7, leading=13.5,
                           spaceAfter=4, leftIndent=14, firstLineIndent=-14))
    ss.add(ParagraphStyle("Meta", parent=ss["BodyText"], fontSize=9.3, leading=13, spaceAfter=3))
    ss.add(ParagraphStyle("Caption", parent=ss["BodyText"], fontSize=8.5, leading=11,
                           alignment=TA_CENTER, textColor=colors.HexColor("#333333"),
                           spaceBefore=4, spaceAfter=14))
    return ss


PIPE_PLACEHOLDER = "\x00PIPE\x00"


def split_row(r):
    protected = r.strip().replace("\\|", PIPE_PLACEHOLDER).strip("|")
    return [c.strip().replace(PIPE_PLACEHOLDER, "|") for c in protected.split("|")]


def parse_table(rows):
    data = [split_row(r) for r in rows]
    header, _, *body = data
    data = [header] + body
    ncols = len(header)
    col_w = (PAGE_W - 1.6 * inch) / ncols
    ss = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=ss["BodyText"], fontSize=8.7, leading=11)
    hdr_style = ParagraphStyle("cellhdr", parent=cell_style, fontName="Helvetica-Bold")
    tbl_data = [[Paragraph(inline_markdown(c), hdr_style) for c in header]]
    for row in body:
        tbl_data.append([Paragraph(inline_markdown(c), cell_style) for c in row])
    t = Table(tbl_data, colWidths=[col_w] * ncols, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def flush_section(story, sec_key, buf):
    story.extend(buf)
    for fname, caption in FIGURE_MAP.get(sec_key, []):
        story.append(Spacer(1, 6))
        story.append(make_image(fname))
        story.append(Paragraph(caption, styles["Caption"]))


def title_page(story, meta_lines, exec_summary_text=None):
    story.append(Spacer(1, 1.1 * inch))
    story.append(Paragraph("LiDAR Bare-Earth DEM", styles["MemoTitle"]))
    story.append(Paragraph("Quality Control Memorandum", styles["MemoTitle"]))
    story.append(Spacer(1, 0.35 * inch))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#888888")))
    story.append(Spacer(1, 0.22 * inch))
    for line in meta_lines:
        story.append(Paragraph(inline_markdown(line), styles["Meta"]))
    if exec_summary_text:
        # lives on page 1, after the header block and before §1 -- someone
        # spending 90 seconds with this needs the verdict without flipping
        # pages, so this is real title-page content, not just the next
        # section in the normal flowing pipeline
        story.append(Spacer(1, 0.3 * inch))
        story.append(HRFlowable(width="100%", color=colors.HexColor("#888888")))
        story.append(Spacer(1, 0.18 * inch))
        story.append(Paragraph("EXECUTIVE SUMMARY", styles["H2"]))
        story.append(Paragraph(inline_markdown(exec_summary_text), styles["Body"]))
    story.append(Spacer(1, 0.45 * inch))
    story.append(Paragraph(
        "Portfolio deliverable — processed from raw returns, independently "
        "QC'd against vendor classification, flight-line geometry, and "
        "the project's own signed accuracy assessment.",
        ParagraphStyle("sub", parent=styles["Body"], alignment=TA_CENTER,
                        textColor=colors.HexColor("#555555"))))
    story.append(PageBreak())


styles = build_styles()


NUMBERED_RE = re.compile(r"^\d+\.\s+")
META_LABEL_RE = re.compile(r"^\*\*[^*]+:\*\*")


def split_blocks(lines):
    """Group lines into blank-line-separated blocks, each a list of
    stripped, non-empty physical lines (markdown soft-wraps within a
    block and must be rejoined by the caller, not treated as separate
    paragraphs/list items)."""
    blocks, cur = [], []
    for line in lines:
        s = line.strip()
        if not s:
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(s)
    if cur:
        blocks.append(cur)
    return blocks


def split_items(block_lines, marker_re, strip_marker=None):
    """Split a list/meta block into items, where a line matching
    marker_re starts a new item and any other line is a continuation of
    the previous item (joined with a space) -- this is what correctly
    handles markdown's soft-wrapped list items and bold-label metadata
    lines."""
    items = []
    for line in block_lines:
        if marker_re.match(line):
            text = marker_re.sub("", line, count=1) if strip_marker else line
            items.append(text)
        elif items:
            items[-1] = items[-1] + " " + line
        else:
            items.append(line)
    return items


def extract_front_matter_section(blocks, heading_text):
    """Pull a '## <heading_text>' section (its heading block + the body
    block immediately after it) out of the block list entirely, returning
    the joined body text and the blocks list with those two blocks
    removed. Used for the executive summary, which belongs on the title
    page (page 1) rendered directly by title_page(), not in the normal
    flowing section pipeline where it would land on page 2 regardless of
    how much room page 1 has left."""
    for i, b in enumerate(blocks):
        if b[0].strip() == f"## {heading_text}":
            body = blocks[i + 1] if i + 1 < len(blocks) else []
            return " ".join(body), blocks[:i] + blocks[i + 2:]
    return None, blocks


def main():
    lines = MEMO.read_text(encoding="utf-8").splitlines()
    blocks = split_blocks(lines)
    exec_summary_text, blocks = extract_front_matter_section(blocks, "Executive Summary")

    story = []
    meta_lines = []
    buf = []
    cur_key = None
    started = False
    in_meta = True
    pending_heading = None  # [heading Paragraph] waiting to be glued via
                             # KeepTogether to whatever content follows it,
                             # so a heading can never render alone at the
                             # bottom of a page -- a CondPageBreak alone
                             # only reserves room for the heading itself,
                             # not for the text that has to follow it, so
                             # the heading and the next few lines could
                             # still land on opposite pages

    def push(flowables):
        # append content to buf, gluing it to a just-emitted heading (if
        # any) so heading + first content block move together as one unit
        nonlocal pending_heading
        if pending_heading is not None:
            buf.append(KeepTogether(pending_heading + flowables))
            pending_heading = None
        else:
            buf.extend(flowables)

    def end_heading_block(new_top_level):
        # flush whatever section/subsection is currently open, including
        # its mapped figures, before starting the next heading. Sections
        # flow continuously (no forced page break per heading -- that
        # wasted half-empty pages); a rule + generous spacing marks each
        # new top-level section instead, and reportlab breaks naturally
        # wherever content actually runs out of room.
        nonlocal buf, cur_key, started, pending_heading
        if pending_heading is not None:
            # previous heading had no body content at all (edge case) --
            # emit it alone rather than lose it
            buf.append(KeepTogether(pending_heading))
            pending_heading = None
        if cur_key is None:
            if not started:
                title_page(story, meta_lines, exec_summary_text)
                started = True
            return
        flush_section(story, cur_key, buf)
        if new_top_level:
            story.append(Spacer(1, 10))
            story.append(HRFlowable(width="100%", thickness=0.6,
                                     color=colors.HexColor("#bbbbbb")))
        buf = []

    for block in blocks:
        first = block[0]

        if first.startswith("|"):
            # the table's own Spacer+Table+Spacer must stay one atomic
            # KeepTogether unit regardless of whether push() also glues
            # it to a preceding heading -- otherwise (the common case,
            # no heading immediately above) push() just extends buf with
            # three loose flowables and reportlab is free to split the
            # table across a page boundary again, header stranded from
            # its data despite repeatRows=1 fixing only the *reprinted*
            # header, not the split itself
            push([KeepTogether([Spacer(1, 4), parse_table(block), Spacer(1, 6)])])
            continue

        if first == "---":
            continue

        if first.startswith("# "):
            in_meta = True
            continue

        if first.startswith("## "):
            end_heading_block(new_top_level=True)
            cur_key = first[3:].strip()
            pending_heading = [CondPageBreak(1.3 * inch),
                                Paragraph(inline_markdown(cur_key), styles["H1"])]
            in_meta = False
            # remainder of this block (rare: text on the same block as
            # the heading) falls through as a paragraph below
            block = block[1:]
            if not block:
                continue
            first = block[0]

        elif first.startswith("### "):
            end_heading_block(new_top_level=False)
            cur_key = first[4:].strip()
            pending_heading = [CondPageBreak(1.0 * inch),
                                Paragraph(inline_markdown(cur_key), styles["H2"])]
            block = block[1:]
            if not block:
                continue
            first = block[0]

        if NUMBERED_RE.match(first):
            items = split_items(block, NUMBERED_RE, strip_marker=True)
            push([Paragraph(f"{n}.&nbsp;&nbsp;{inline_markdown(t)}", styles["ListItem"])
                  for n, t in enumerate(items, start=1)])
            continue

        if first.startswith("- "):
            items = split_items(block, re.compile(r"^-\s+"), strip_marker=True)
            push([Paragraph(f"•&nbsp;&nbsp;{inline_markdown(t)}", styles["ListItem"])
                  for t in items])
            continue

        if in_meta:
            items = split_items(block, META_LABEL_RE)
            meta_lines.extend(items)
            continue

        # plain paragraph: rejoin soft-wrapped lines into one string
        push([Paragraph(inline_markdown(" ".join(block)), styles["Body"])])

    if pending_heading is not None:  # heading with no body at all (edge case)
        buf.append(KeepTogether(pending_heading))
    if cur_key is not None:
        flush_section(story, cur_key, buf)

    # Appendix
    story.append(PageBreak())
    story.append(Paragraph("Appendix: Hillshade Comparison", styles["H1"]))
    story.append(Paragraph(
        "Supporting hillshades referenced in \u00a74 (roof vs. pad "
        "investigation): the vendor-delivered classification baseline "
        "and the first SMRF parameter attempt (window=60 ft) \u2014 the one "
        "tested window value that produced a genuinely distinct result "
        "(see \u00a74 for the full four-value comparison and why 120, 180, "
        "and 240 ft converge to an identical output).", styles["Body"]))
    # Side by side, not one full page each -- these are corroborating
    # evidence for a point already made in §4, not primary figures,
    # so they don't need primary-figure-sized real estate.
    half_w = (MAX_IMG_W - 0.3 * inch) / 2
    col1, col2 = [], []
    for fname, caption in APPENDIX_FIGURES:
        col1.append(make_image(fname, max_w=half_w, max_h=6.5 * inch))
        col2.append(Paragraph(caption, styles["Caption"]))
    row = Table([[col1[0], col1[1]]], colWidths=[half_w + 0.15 * inch] * 2)
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    cap_row = Table([[col2[0], col2[1]]], colWidths=[half_w + 0.15 * inch] * 2)
    story.append(Spacer(1, 6))
    story.append(row)
    story.append(cap_row)

    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title="LiDAR Bare-Earth DEM — QC Memorandum",
        author="LiDAR Processing Portfolio",
    )
    doc.build(story)
    print(f"Wrote {OUT}")
    print(f"Page count: {doc.page}")


if __name__ == "__main__":
    main()
