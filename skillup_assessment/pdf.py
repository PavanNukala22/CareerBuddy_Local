"""
Certificate PDF generation using reportlab (already a project dependency —
no new external binary/tool required, unlike wkhtmltopdf/weasyprint).

Visual design follows the navy/gold "Certificate of Appreciation" style:
a curved navy+gold header band, a gold medal/ribbon badge, bold serif
title, script-style recipient name, and signature/date lines at the foot.
Colors match the site's existing Black & Gold Elegance theme (see
static/css/style.css), so a downloaded certificate feels visually
consistent with the rest of Career Buddy.
"""
import io
import math

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


NAVY = colors.HexColor("#14213D")
NAVY_DARK = colors.HexColor("#0b1526")
GOLD = colors.HexColor("#FCA311")
GOLD_DARK = colors.HexColor("#c97f0a")
GRAY_TEXT = colors.HexColor("#64748b")
WHITE = colors.white


def _draw_wave_header(c, width, height):
    """Navy curved band across the top, with a gold accent wave beneath it —
    the signature shape of the reference design.
    """
    wave_base = height - 5.3 * cm

    # Navy band
    p = c.beginPath()
    p.moveTo(0, height)
    p.lineTo(0, wave_base + 1.3 * cm)
    p.curveTo(
        width * 0.28, wave_base + 2.6 * cm,
        width * 0.62, wave_base - 0.9 * cm,
        width, wave_base + 0.7 * cm,
    )
    p.lineTo(width, height)
    p.close()
    c.setFillColor(NAVY)
    c.drawPath(p, fill=1, stroke=0)

    # Gold accent wave, riding just under the navy edge
    p2 = c.beginPath()
    p2.moveTo(0, wave_base + 1.3 * cm)
    p2.curveTo(
        width * 0.28, wave_base + 2.6 * cm,
        width * 0.62, wave_base - 0.9 * cm,
        width, wave_base + 0.7 * cm,
    )
    p2.lineTo(width, wave_base + 0.7 * cm - 0.45 * cm)
    p2.curveTo(
        width * 0.62, wave_base - 0.9 * cm - 0.45 * cm,
        width * 0.28, wave_base + 2.6 * cm - 0.45 * cm,
        0, wave_base + 1.3 * cm - 0.45 * cm,
    )
    p2.close()
    c.setFillColor(GOLD)
    c.drawPath(p2, fill=1, stroke=0)

    return wave_base


def _star(c, cx, cy, r, color):
    c.setFillColor(color)
    points = []
    for i in range(5):
        outer_angle = math.pi / 2 + i * 2 * math.pi / 5
        points.append((cx + r * math.cos(outer_angle), cy + r * math.sin(outer_angle)))
        inner_angle = outer_angle + math.pi / 5
        points.append((cx + r * 0.42 * math.cos(inner_angle), cy + r * 0.42 * math.sin(inner_angle)))
    p = c.beginPath()
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def _draw_medal(c, cx, cy):
    """Gold 'BEST AWARD' medal with ribbon tails, positioned to overlap the
    header band on the left, matching the reference badge.
    """
    r_outer = 1.55 * cm
    r_inner = 1.3 * cm

    # Ribbon tails first (so the medal sits on top of them)
    tail_w = 0.55 * cm
    for dx in (-0.55 * cm, 0.55 * cm):
        p = c.beginPath()
        x0 = cx + dx - tail_w / 2
        p.moveTo(x0, cy)
        p.lineTo(x0 + tail_w, cy)
        p.lineTo(x0 + tail_w, cy - 2.6 * cm)
        p.lineTo(x0 + tail_w / 2, cy - 2.0 * cm)
        p.lineTo(x0, cy - 2.6 * cm)
        p.close()
        c.setFillColor(GOLD_DARK)
        c.drawPath(p, fill=1, stroke=0)

    # Medal disc
    c.setFillColor(GOLD)
    c.circle(cx, cy, r_outer, fill=1, stroke=0)
    c.setStrokeColor(WHITE)
    c.setLineWidth(1.2)
    c.circle(cx, cy, r_inner, fill=0, stroke=1)

    for i, angle_deg in enumerate((90, 60, 120)):
        angle = math.radians(angle_deg)
        sx = cx + (r_inner - 0.25 * cm) * math.cos(angle)
        sy = cy + 0.35 * cm + (r_inner - 0.9 * cm) * math.sin(angle) + 0.15 * cm
        _star(c, sx, sy, 0.09 * cm, WHITE)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8.2)
    c.drawCentredString(cx, cy - 0.05 * cm, "BEST")
    c.drawCentredString(cx, cy - 0.42 * cm, "AWARD")


def render_certificate_pdf(*, certificate_name, module_display, score, total, certificate_number, issued_on):
    """Return raw PDF bytes for a completed certificate."""
    buffer = io.BytesIO()
    page_size = landscape(A4)
    width, height = page_size
    c = canvas.Canvas(buffer, pagesize=page_size)

    c.setFillColor(WHITE)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    wave_base = _draw_wave_header(c, width, height)
    _draw_medal(c, 3.6 * cm, wave_base - 0.15 * cm)

    text_left = 6.6 * cm
    text_right = width - 2.2 * cm

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 30)
    title_y = wave_base - 0.55 * cm
    c.drawString(text_left, title_y, "CAREER BUDDY")

    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica", 15)
    c.drawString(text_left, title_y - 0.85 * cm, "CERTIFICATE OF ACHIEVEMENT")

    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(text_left, title_y - 1.15 * cm, text_left + 4.6 * cm, title_y - 1.15 * cm)

    center_x = width / 2

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawCentredString(center_x, title_y - 2.35 * cm, "THIS CERTIFICATE IS PROUDLY PRESENTED TO")

    c.setFillColor(GOLD_DARK)
    c.setFont("Times-Italic", 34)
    name_y = title_y - 3.75 * cm
    c.drawCentredString(center_x, name_y, certificate_name)

    name_width = c.stringWidth(certificate_name, "Times-Italic", 34)
    underline_half = max(name_width / 2 + 0.6 * cm, 3.2 * cm)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(center_x - underline_half, name_y - 0.45 * cm, center_x + underline_half, name_y - 0.45 * cm)

    c.setFillColor(GRAY_TEXT)
    c.setFont("Helvetica", 11)
    c.drawCentredString(
        center_x, name_y - 1.35 * cm,
        f"for successfully completing the Career Buddy {module_display} Skill Up Mock Test",
    )
    c.drawCentredString(
        center_x, name_y - 1.9 * cm,
        "and achieving the required score.",
    )
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(center_x, name_y - 2.55 * cm, f"Score: {score} / {total}")

    # Signature / Date / Certificate ID
    foot_y = 3.6 * cm
    line_len = 4.6 * cm

    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(1)
    c.line(text_left - 1.0 * cm, foot_y, text_left - 1.0 * cm + line_len, foot_y)
    c.setFillColor(GRAY_TEXT)
    c.setFont("Helvetica", 9)
    c.drawString(text_left - 1.0 * cm, foot_y - 0.45 * cm, "SIGNATURE")
    c.drawString(text_left - 1.0 * cm, foot_y - 0.9 * cm, "Authorized by Career Buddy")

    date_line_x = text_right - line_len
    c.line(date_line_x, foot_y, date_line_x + line_len, foot_y)
    c.drawString(date_line_x, foot_y - 0.45 * cm, "DATE")
    c.setFont("Helvetica", 9)
    c.setFillColor(NAVY)
    c.drawString(date_line_x, foot_y + 0.15 * cm, issued_on.strftime("%d %B %Y"))

    c.setFillColor(GRAY_TEXT)
    c.setFont("Helvetica", 8)
    c.drawCentredString(center_x, 1.1 * cm, f"Certificate ID: {certificate_number}")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 1.0 * cm, height - 0.9 * cm, "CAREER BUDDY")

    c.showPage()
    c.save()

    return buffer.getvalue()

