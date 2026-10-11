from __future__ import annotations

from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except ImportError:  # Allows the app to explain the optional dependency at export time.
    colors = None


def _require_reportlab() -> None:
    if colors is None:
        raise RuntimeError(
            "Falta ReportLab. Instálalo con: python -m pip install reportlab"
        )


def _build(path: str | Path, title: str, subtitle: str, headers: list[str], rows: list[list[str]]) -> Path:
    _require_reportlab()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "OpenChessTitle", parent=styles["Title"], textColor=colors.HexColor("#17324D"),
        fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=4 * mm,
    )
    subtitle_style = ParagraphStyle(
        "OpenChessSubtitle", parent=styles["Normal"], textColor=colors.HexColor("#4A6075"),
        fontSize=9, alignment=TA_CENTER, spaceAfter=6 * mm,
    )
    page_size = landscape(A4) if len(headers) >= 6 else A4
    doc = SimpleDocTemplate(
        str(path), pagesize=page_size, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=title, author="Open Chess",
    )
    story = [
        Paragraph(title, title_style),
        Paragraph(f"{subtitle} · Generado el {datetime.now():%d/%m/%Y %H:%M}", subtitle_style),
    ]
    data = [headers] + (rows or [["Sin datos"] + [""] * (len(headers) - 1)])
    available = page_size[0] - 28 * mm
    widths = [available / len(headers)] * len(headers)
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B9C5D1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F8")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([table, Spacer(1, 4 * mm)])
    doc.build(story)
    return path


def participants_pdf(path: str | Path, tournament: str, players: list) -> Path:
    rows = [[str(i), f"{p['first_name']} {p['last_name']}", p["course"] or "-", p["center"] or "-"]
            for i, p in enumerate(players, 1)]
    return _build(path, "Listado de participantes", tournament, ["Nº", "Alumno/a", "Curso", "Centro"], rows)


def pairings_pdf(path: str | Path, tournament: str, round_number: int, pairings: list) -> Path:
    rows = [[str(p["board"]), p["white_name"], p["black_name"], p["result"] or "Pendiente"] for p in pairings]
    return _build(path, f"Emparejamientos - Ronda {round_number}", tournament,
                  ["Mesa", "Blancas", "Negras", "Resultado"], rows)


def standings_pdf(path: str | Path, tournament: str, standings: list) -> Path:
    rows = [[str(i), s.name, s.course or "-", s.center or "-", _fmt(s.points), _fmt(s.buchholz), str(s.wins)]
            for i, s in enumerate(standings, 1)]
    return _build(path, "Clasificación", tournament,
                  ["Pos.", "Alumno/a", "Curso", "Centro", "Puntos", "Buchholz", "Victorias"], rows)


def _fmt(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value).replace(".", ",")
