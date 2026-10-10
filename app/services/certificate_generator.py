from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.config import settings


def get_font_path():
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def register_font():
    font_path = get_font_path()
    if font_path:
        font_name = "GeneratedFont"
        existing = pdfmetrics.getRegisteredFontNames()
        if font_name not in existing:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        return font_name
    return "Helvetica"


def get_certificate_dir(job_id):
    root = Path(settings.CERTIFICATES_DIR)
    root.mkdir(parents=True, exist_ok=True)
    job_dir = root / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def build_certificate_path(job_id, certificate_id):
    job_dir = get_certificate_dir(job_id)
    return job_dir / f"{certificate_id}.pdf"


def relative_file_path(job_id, certificate_id):
    return f"{job_id}/{certificate_id}.pdf"


def fit_text_width(c, text, width, min_size=16, max_size=40, font_name="Helvetica"):
    size = max_size
    while size >= min_size:
        c.setFont(font_name, size)
        if c.stringWidth(text, font_name, size) <= width:
            return size
        size -= 2
    return min_size


def generate_certificate_pdf(job_id, cert_id, name, event_name, issuer_name, issue_date, course_or_role=None):
    output_path = build_certificate_path(job_id, cert_id)
    font_name = register_font()
    c = canvas.Canvas(str(output_path), pagesize=landscape(A4))
    width, height = landscape(A4)

    c.setStrokeColor(HexColor("#2E4057"))
    c.setFillColor(HexColor("#1F2D3D"))
    c.rect(36, 36, width - 72, height - 72, stroke=1, fill=0)
    c.rect(52, 52, width - 104, height - 104, stroke=1, fill=0)

    c.setStrokeColor(HexColor("#C4A43F"))
    c.setLineWidth(2)
    c.line(70, 70, width - 70, 70)
    c.line(70, height - 70, width - 70, height - 70)
    c.line(70, 70, 70, height - 70)
    c.line(width - 70, 70, width - 70, height - 70)

    c.setFillColor(HexColor("#1F2D3D"))
    c.setFont(font_name, 30)
    c.drawCentredString(width / 2, height - 100, "Certificate of Achievement")

    c.setFont(font_name, 19)
    c.drawCentredString(width / 2, height - 150, "This is to certify that")

    safe_name = str(name or "Recipient")
    name_font_size = fit_text_width(c, safe_name, width * 0.7, min_size=20, max_size=42, font_name=font_name)
    c.setFont(font_name, name_font_size)
    c.drawCentredString(width / 2, height / 2 + 35, safe_name)

    c.setFont(font_name, 20)
    c.drawCentredString(width / 2, height / 2 - 45, "has successfully participated in / completed")

    event_line = str(event_name or "the event")
    event_font_size = fit_text_width(c, event_line, width * 0.65, min_size=18, max_size=30, font_name=font_name)
    c.setFont(font_name, event_font_size)
    c.drawCentredString(width / 2, height / 2 - 95, event_line)

    if course_or_role:
        course_line = str(course_or_role)
        course_font_size = fit_text_width(c, course_line, width * 0.55, min_size=14, max_size=22, font_name=font_name)
        c.setFont(font_name, course_font_size)
        c.drawCentredString(width / 2, height / 2 - 140, course_line)

    issue_date_value = issue_date.isoformat() if isinstance(issue_date, date) else str(issue_date)
    c.setFont(font_name, 14)
    c.drawString(110, 115, f"Issue date: {issue_date_value}")

    c.setFont(font_name, 14)
    c.drawRightString(width - 110, 115, f"Issued by: {issuer_name}")

    c.setFont(font_name, 12)
    c.drawCentredString(width / 2, 94, f"Certificate ID: {cert_id}")
    c.showPage()
    c.save()

    return relative_file_path(job_id, cert_id)
