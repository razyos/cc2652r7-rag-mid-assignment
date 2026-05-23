from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "report.md"
OUTPUT = ROOT / "report.pdf"


def inline_markdown(text: str) -> str:
    text = escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(
        r"`([^`]+)`",
        r'<font name="Courier">\1</font>',
        text,
    )
    return text


def parse_table(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    return rows


def column_widths(rows: list[list[str]], total_width: float) -> list[float]:
    cols = max(len(row) for row in rows)
    if cols == 3:
        weights = [0.54, 0.30, 0.16]
    elif cols == 4:
        first = rows[0][0].lower()
        if first == "metric":
            weights = [0.22, 0.13, 0.13, 0.52]
        else:
            weights = [0.36, 0.12, 0.22, 0.30]
    elif cols == 5:
        weights = [0.17, 0.32, 0.10, 0.16, 0.25]
    else:
        weights = [1 / cols] * cols
    return [total_width * w for w in weights]


def make_table(rows: list[list[str]], styles: dict[str, ParagraphStyle], width: float) -> Table:
    max_cols = max(len(row) for row in rows)
    normalized = [row + [""] * (max_cols - len(row)) for row in rows]
    table_style = styles["table"]
    data = [[Paragraph(inline_markdown(cell), table_style) for cell in row] for row in normalized]
    table = Table(data, colWidths=column_widths(normalized, width), repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]
        )
    )
    return table


def build_story(markdown: str, available_width: float):
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            alignment=TA_CENTER,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.35,
            leading=9.75,
            alignment=TA_LEFT,
            spaceAfter=3.2,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=11.5,
            spaceBefore=5,
            spaceAfter=2.2,
            keepWithNext=True,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.2,
            leading=8.2,
            leftIndent=5,
            rightIndent=5,
            spaceBefore=2,
            spaceAfter=4,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.15,
            leading=7.1,
            spaceAfter=0,
        ),
    }

    story = []
    para: list[str] = []
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_para() -> None:
        if para:
            text = " ".join(line.strip() for line in para)
            story.append(Paragraph(inline_markdown(text), styles["body"]))
            para.clear()

    def flush_table() -> None:
        if table_lines:
            table = make_table(parse_table(table_lines), styles, available_width)
            story.append(table)
            story.append(Spacer(1, 3))
            table_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            flush_para()
            flush_table()
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"]))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if line.startswith("|"):
            flush_para()
            table_lines.append(line)
            continue
        flush_table()

        if not line.strip():
            flush_para()
            continue

        if line.startswith("# "):
            flush_para()
            story.append(Paragraph(inline_markdown(line[2:].strip()), styles["title"]))
            continue

        if line.startswith("## "):
            flush_para()
            story.append(Paragraph(inline_markdown(line[3:].strip()), styles["h2"]))
            continue

        para.append(line)

    flush_para()
    flush_table()
    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["code"]))

    return story


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#4B5563"))
    canvas.drawRightString(A4[0] - 12 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def main() -> None:
    margin_x = 12 * mm
    margin_top = 11 * mm
    margin_bottom = 13 * mm
    available_width = A4[0] - (2 * margin_x)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=margin_x,
        leftMargin=margin_x,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
        title="CC2652R7 RAG Report",
        author="",
    )
    story = build_story(SOURCE.read_text(encoding="utf-8"), available_width)
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)


if __name__ == "__main__":
    main()
