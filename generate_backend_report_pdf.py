from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def is_table_separator(line: str) -> bool:
    stripped = line.strip().strip("|").replace(" ", "")
    return bool(stripped) and all(ch in "-:" for ch in stripped)


def parse_table(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for idx, raw in enumerate(lines):
        if not raw.strip().startswith("|"):
            continue
        if idx == 1 and is_table_separator(raw):
            continue
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        spaceAfter=10,
    )
    style_h2 = ParagraphStyle(
        "H2Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        spaceBefore=8,
        spaceAfter=6,
    )
    style_h3 = ParagraphStyle(
        "H3Custom",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=6,
        spaceAfter=4,
    )
    style_body = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )
    style_bullet = ParagraphStyle(
        "BulletCustom",
        parent=style_body,
        leftIndent=12,
        bulletIndent=0,
    )
    style_code = ParagraphStyle(
        "CodeCustom",
        parent=style_body,
        fontName="Courier",
        fontSize=8.8,
        leading=11,
        leftIndent=8,
        rightIndent=8,
    )

    story = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            story.append(Spacer(1, 2))
            i += 1
            continue

        if stripped == "---":
            story.append(Spacer(1, 6))
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            block = "\n".join(code_lines).rstrip()
            if block:
                story.append(Preformatted(block, style_code))
                story.append(Spacer(1, 4))
            continue

        if stripped.startswith("|"):
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = parse_table(table_lines)
            if rows:
                col_count = max(len(r) for r in rows)
                normalized = [r + [""] * (col_count - len(r)) for r in rows]
                usable_width = A4[0] - 36 * mm
                col_width = usable_width / max(col_count, 1)
                table = Table(
                    normalized, colWidths=[col_width] * col_count, repeatRows=1
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef7")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8.6),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfc7d5")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 4),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 6))
            continue

        if stripped.startswith("# "):
            story.append(Paragraph(escape(stripped[2:].strip()), style_title))
            i += 1
            continue

        if stripped.startswith("## "):
            story.append(Paragraph(escape(stripped[3:].strip()), style_h2))
            i += 1
            continue

        if stripped.startswith("### "):
            story.append(Paragraph(escape(stripped[4:].strip()), style_h3))
            i += 1
            continue

        if stripped.startswith("#### "):
            story.append(Paragraph(escape(stripped[5:].strip()), style_h3))
            i += 1
            continue

        if stripped.startswith("- "):
            story.append(
                Paragraph(escape(stripped[2:].strip()), style_bullet, bulletText="•")
            )
            i += 1
            continue

        story.append(Paragraph(escape(stripped), style_body))
        i += 1

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Makezy Backend Integration Report",
        author="OpenCode",
    )
    doc.build(story)


if __name__ == "__main__":
    workspace = Path(__file__).resolve().parent
    markdown = workspace / "makezy_backend_integration_report.md"
    pdf = workspace / "makezy_backend_integration_report.pdf"
    build_pdf(markdown, pdf)
