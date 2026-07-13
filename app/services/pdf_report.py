from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass(frozen=True)
class GeneratedPdf:
    content: bytes
    filename: str


def _safe_text(value: Any, limit: int = 10000) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _filename(title: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in title)
    safe = "-".join(part for part in safe.split("-") if part)
    return f"{(safe or 'relatorio-domnai')[:90]}.pdf"


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DomnTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            spaceAfter=8 * mm,
            textColor=colors.HexColor("#171717"),
        ),
        "subtitle": ParagraphStyle(
            "DomnSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
            spaceAfter=8 * mm,
        ),
        "heading": ParagraphStyle(
            "DomnHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
            textColor=colors.HexColor("#171717"),
        ),
        "body": ParagraphStyle(
            "DomnBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            alignment=TA_LEFT,
            spaceAfter=3 * mm,
            textColor=colors.HexColor("#262626"),
        ),
        "small": ParagraphStyle(
            "DomnSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#666666"),
        ),
    }


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#D9D9D9"))
    canvas.line(18 * mm, 16 * mm, width - 18 * mm, 16 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(18 * mm, 10 * mm, "DomnAI - Transforme escolhas em resultados com inteligência.")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _metric_table(metrics: list[dict[str, Any]], styles: dict) -> Table | None:
    rows = []
    for item in metrics[:24]:
        label = _safe_text(item.get("label"), 120)
        value = _safe_text(item.get("value"), 180)
        if label and value:
            rows.append([Paragraph(label, styles["small"]), Paragraph(value, styles["body"])])
    if not rows:
        return None
    table = Table(rows, colWidths=[58 * mm, 112 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F3F3")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5D5D5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _data_table(payload: dict[str, Any], styles: dict) -> Table | None:
    headers = [_safe_text(item, 100) for item in payload.get("headers", [])[:10]]
    raw_rows = payload.get("rows", [])[:100]
    if not headers or not isinstance(raw_rows, list):
        return None
    data = [[Paragraph(header, styles["small"]) for header in headers]]
    for raw_row in raw_rows:
        if not isinstance(raw_row, list):
            continue
        cells = [_safe_text(item, 500) for item in raw_row[: len(headers)]]
        cells += [""] * (len(headers) - len(cells))
        data.append([Paragraph(cell, styles["small"]) for cell in cells])
    if len(data) == 1:
        return None
    width = 170 * mm / len(headers)
    table = Table(data, colWidths=[width] * len(headers), repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CFCFCF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _bar_chart(payload: dict[str, Any]) -> Drawing | None:
    labels = [_safe_text(item, 25) for item in payload.get("labels", [])[:12]]
    values = payload.get("values", [])[:12]
    numeric: list[float] = []
    for value in values:
        try:
            numeric.append(float(value))
        except (TypeError, ValueError):
            return None
    if not labels or len(labels) != len(numeric) or not any(numeric):
        return None
    drawing = Drawing(480, 230)
    chart = VerticalBarChart()
    chart.x = 45
    chart.y = 45
    chart.height = 150
    chart.width = 400
    chart.data = [numeric]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 25
    chart.categoryAxis.labels.dy = -12
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = min(0, min(numeric))
    chart.bars[0].fillColor = colors.HexColor("#3A3A3A")
    chart.bars[0].strokeColor = colors.HexColor("#3A3A3A")
    drawing.add(chart)
    return drawing


def generate_pdf_report(payload: dict[str, Any]) -> GeneratedPdf:
    title = _safe_text(payload.get("title"), 180) or "Relatório DomnAI"
    operation = _safe_text(payload.get("operation"), 180)
    summary = _safe_text(payload.get("summary"), 20000)
    sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), list) else []
    tables = payload.get("tables") if isinstance(payload.get("tables"), list) else []
    charts = payload.get("charts") if isinstance(payload.get("charts"), list) else []

    if not summary and not sections and not metrics and not tables:
        raise ValueError("O relatório não possui conteúdo suficiente para gerar o PDF.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=23 * mm,
        title=title,
        author="DomnAI",
        subject=operation or "Relatório de apoio à decisão",
    )
    styles = _styles()
    story = [
        Paragraph(title, styles["title"]),
        Paragraph(operation or "Relatório personalizado de apoio à decisão", styles["subtitle"]),
    ]

    if summary:
        story.extend([
            Paragraph("Resumo", styles["heading"]),
            Paragraph(summary.replace("\n", "<br/>"), styles["body"]),
        ])

    metric_table = _metric_table(metrics, styles)
    if metric_table is not None:
        story.extend([Paragraph("Indicadores", styles["heading"]), metric_table, Spacer(1, 3 * mm)])

    for section in sections[:30]:
        if not isinstance(section, dict):
            continue
        heading = _safe_text(section.get("title"), 180)
        body = _safe_text(section.get("content"), 30000)
        if not heading and not body:
            continue
        block = []
        if heading:
            block.append(Paragraph(heading, styles["heading"]))
        if body:
            block.append(Paragraph(body.replace("\n", "<br/>"), styles["body"]))
        story.append(KeepTogether(block) if len(body) < 1800 else block[0] if len(block) == 1 else block[0])
        if len(body) >= 1800 and body:
            story.append(Paragraph(body.replace("\n", "<br/>"), styles["body"]))

    for table_payload in tables[:12]:
        if not isinstance(table_payload, dict):
            continue
        table = _data_table(table_payload, styles)
        if table is None:
            continue
        label = _safe_text(table_payload.get("title"), 180)
        if label:
            story.append(Paragraph(label, styles["heading"]))
        story.append(table)
        story.append(Spacer(1, 4 * mm))

    valid_charts = []
    for chart_payload in charts[:6]:
        if not isinstance(chart_payload, dict):
            continue
        chart = _bar_chart(chart_payload)
        if chart is not None:
            valid_charts.append((chart_payload, chart))
    if valid_charts:
        story.append(PageBreak())
        story.append(Paragraph("Visualizações", styles["heading"]))
        for chart_payload, chart in valid_charts:
            label = _safe_text(chart_payload.get("title"), 180)
            if label:
                story.append(Paragraph(label, styles["body"]))
            story.append(chart)
            story.append(Spacer(1, 5 * mm))

    story.extend([
        Spacer(1, 6 * mm),
        Paragraph(
            "Este relatório organiza as informações fornecidas e não substitui avaliação profissional quando o tema exigir análise jurídica, contábil, médica, financeira ou técnica especializada.",
            styles["small"],
        ),
    ])

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return GeneratedPdf(content=buffer.getvalue(), filename=_filename(title))
