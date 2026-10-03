"""PDF output for the manual Resume Builder (ReportLab — already a dependency).

The layout follows CareerBuddy's reference resume: a classic single-column,
serif, black-and-white document — centred upper-case name, title and contact
line, upper-case section headings over a full-width rule, justified body text,
"Title | Company" experience headers with a dates line, a two-column skills
table, numbered projects with an italic "Technologies:" line, and an optional
declaration with place, date and name. It is drawn from the same document dict
as the on-page preview (``resume_document.build_document``) as real text, so
it stays selectable, searchable and readable by applicant-tracking systems,
links stay clickable, and long resumes flow onto further pages.

Fonts: a Unicode TrueType serif is registered so names and text with accents,
₹, en dashes and curly quotes print correctly — Liberation Serif / DejaVu
Serif (Linux) or Times New Roman (Windows). If no serif is installed, a sans
family (DejaVu / Noto / Liberation Sans / Arial, then the Vera family bundled
with ReportLab) is used, so a font is always available. Set
``RESUME_PDF_FONT_FILES`` in settings to (regular, bold, italic, bold-italic)
paths to choose another.
"""
import io
import os
import re
import unicodedata
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

FONT = 'CBResume'
INK = colors.HexColor('#111111')
LINK = '#1155cc'

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 16 * mm
MARGIN_BOTTOM = 16 * mm
FRAME_W = PAGE_W - 2 * MARGIN_X
# SimpleDocTemplate's frame keeps 6pt of padding on each side; anything wider
# than this does not fit the frame and gets pushed onto a new page.
CONTENT_W = FRAME_W - 12
SKILL_LABEL_W = 128

_REPORTLAB_FONTS = os.path.join(os.path.dirname(pdfmetrics.__file__), '..', 'fonts')
_WIN_FONTS = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
_LIB = '/usr/share/fonts/truetype/liberation/'
_DJV = '/usr/share/fonts/truetype/dejavu/'
SERIF_FONTS = [
    # The reference resume uses Liberation Serif.
    tuple(_LIB + f for f in ('LiberationSerif-Regular.ttf', 'LiberationSerif-Bold.ttf',
                             'LiberationSerif-Italic.ttf', 'LiberationSerif-BoldItalic.ttf')),
    tuple('/usr/share/fonts/liberation-serif/' + f for f in ('LiberationSerif-Regular.ttf', 'LiberationSerif-Bold.ttf',
                                                             'LiberationSerif-Italic.ttf', 'LiberationSerif-BoldItalic.ttf')),
    tuple(_DJV + f for f in ('DejaVuSerif.ttf', 'DejaVuSerif-Bold.ttf', 'DejaVuSerif-Italic.ttf', 'DejaVuSerif-BoldItalic.ttf')),
    tuple(os.path.join(_WIN_FONTS, f) for f in ('times.ttf', 'timesbd.ttf', 'timesi.ttf', 'timesbi.ttf')),
]
SANS_FONTS = [
    tuple(_DJV + f for f in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSans-Oblique.ttf', 'DejaVuSans-BoldOblique.ttf')),
    ('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf', '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
     '/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf', '/usr/share/fonts/truetype/noto/NotoSans-BoldItalic.ttf'),
    tuple(_LIB + f for f in ('LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf',
                             'LiberationSans-Italic.ttf', 'LiberationSans-BoldItalic.ttf')),
    tuple(os.path.join(_WIN_FONTS, f) for f in ('arial.ttf', 'arialbd.ttf', 'ariali.ttf', 'arialbi.ttf')),
    tuple(os.path.join(_REPORTLAB_FONTS, f) for f in ('Vera.ttf', 'VeraBd.ttf', 'VeraIt.ttf', 'VeraBI.ttf')),
]
# Serif first; the sans families are the fallback so a font is always available.
_FONT_CANDIDATES = SERIF_FONTS + SANS_FONTS

# Typographic characters some fonts lack, mapped to plain equivalents so the
# text never prints as an empty box.
_FALLBACK_CHARS = {
    '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-',
    '\u2022': '-', '\u2026': '...', '\u20b9': 'Rs.', '\u00a0': ' ', '\u2192': '->',
}
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')

_font_state = {}


def _register_fonts():
    if _font_state:
        return _font_state['glyphs']
    candidates = list(_FONT_CANDIDATES)
    custom = getattr(settings, 'RESUME_PDF_FONT_FILES', None)
    if custom and len(custom) == 4:
        candidates.insert(0, tuple(custom))
    for files in candidates:
        if not all(os.path.isfile(f) for f in files):
            continue
        try:
            faces = [TTFont(f'{FONT}{suffix}', path)
                     for suffix, path in zip(('', '-Bold', '-Italic', '-BoldItalic'), files)]
        except Exception:
            continue
        for face in faces:
            pdfmetrics.registerFont(face)
        pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=f'{FONT}-Bold',
                                      italic=f'{FONT}-Italic', boldItalic=f'{FONT}-BoldItalic')
        _font_state['glyphs'] = set(faces[0].face.charToGlyph.keys())
        _font_state['file'] = files[0]
        return _font_state['glyphs']
    raise RuntimeError('No TrueType font available for resume PDFs.')


def _safe(text):
    """Keep every character the font can draw; map the rest to the nearest plain text."""
    glyphs = _register_fonts()
    out = []
    for ch in str(text or ''):
        if ch in '\n\t' or ord(ch) in glyphs:
            out.append(ch)
        elif ch in _FALLBACK_CHARS:
            out.append(_FALLBACK_CHARS[ch])
        else:
            plain = unicodedata.normalize('NFKD', ch).encode('ascii', 'ignore').decode()
            out.append(plain or '?')
    return ''.join(out)


def _t(text):
    """Escape candidate text for ReportLab's paragraph markup."""
    return escape(_safe(text))


def _rich(text):
    """Escaped text where the candidate's own **double-asterisk** words are bold."""
    return _BOLD_RE.sub(r'<b>\1</b>', _t(text))


def _ch(char, fallback):
    return char if ord(char) in _register_fonts() else fallback


def _styles():
    body = dict(fontName=FONT, fontSize=10, leading=13.2, textColor=INK)
    return {
        'name': ParagraphStyle('name', fontName=f'{FONT}-Bold', fontSize=20, leading=24, textColor=INK, alignment=TA_CENTER),
        'title': ParagraphStyle('title', fontName=FONT, fontSize=11, leading=15, textColor=INK, alignment=TA_CENTER, spaceBefore=2),
        'contact': ParagraphStyle('contact', fontName=FONT, fontSize=9.5, leading=12.5, textColor=INK, alignment=TA_CENTER, spaceBefore=3),
        'heading': ParagraphStyle('heading', fontName=f'{FONT}-Bold', fontSize=11, leading=14, textColor=INK, spaceBefore=12),
        'body': ParagraphStyle('body', alignment=TA_JUSTIFY, **body),
        'left': ParagraphStyle('left', alignment=TA_LEFT, **body),
        'entry': ParagraphStyle('entry', fontName=f'{FONT}-Bold', fontSize=10.5, leading=14, textColor=INK, spaceBefore=2),
        'meta': ParagraphStyle('meta', fontName=FONT, fontSize=10.5, leading=14, textColor=INK, spaceAfter=3),
        'bullet': ParagraphStyle('bullet', alignment=TA_JUSTIFY, leftIndent=16, bulletIndent=6,
                                 bulletFontName=FONT, bulletFontSize=10, spaceBefore=2, **body),
        'tech': ParagraphStyle('tech', fontName=f'{FONT}-Italic', fontSize=10, leading=13.2, textColor=INK,
                               alignment=TA_JUSTIFY, spaceBefore=6, spaceAfter=4),
        'skill_label': ParagraphStyle('skill_label', fontName=f'{FONT}-Bold', fontSize=10, leading=13.2, textColor=INK),
        'right': ParagraphStyle('right', fontName=f'{FONT}-Bold', fontSize=10, leading=13.2, textColor=INK, alignment=TA_RIGHT),
    }


def _contact_line(contact):
    parts = []
    for item in contact:
        # Non-breaking spaces keep each item ("Passport No : Y1234567") on one line.
        text = _t(item.get('text')).replace(' ', '&nbsp;')
        href = item.get('href') or ''
        if href and not href.startswith('tel:'):
            parts.append(f'<a href="{escape(href, {chr(34): "&quot;"})}" color="{LINK}"><u>{text}</u></a>')
        else:
            parts.append(text)
    return ' | '.join(parts)


def _plain_table(rows, widths):
    table = Table(rows, colWidths=widths)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return table


def _bullets(items, st):
    bullet = _ch('\u2022', '-')
    return [Paragraph(_rich(b), st['bullet'], bulletText=bullet) for b in items or []]


def _job_blocks(section, st):
    """'Title | Company' in bold, then 'Location | dates (duration)', then bullets."""
    sep = '&nbsp;&nbsp;|&nbsp;&nbsp;'
    blocks = []
    for item in section['items']:
        head = f"<b>{_t(item['title'])}</b>" + (f"{sep}<b>{_t(item['subtitle'])}</b>" if item.get('subtitle') else '')
        lead = [Paragraph(head, st['entry'])]
        dates = item.get('dates') or ''
        if dates and item.get('duration'):
            dates += f" ({item['duration']})"
        meta = ' | '.join(_t(x) for x in (item.get('location'), dates) if x)
        if meta:
            lead.append(Paragraph(meta, st['meta']))
        bullets = _bullets(item.get('bullets'), st)
        blocks.append((lead + bullets[:2], bullets[2:] + [Spacer(1, 6)]))
    return blocks


def _project_blocks(section, st):
    """Numbered, bold project names; bullets; then an italic 'Technologies:' line."""
    blocks = []
    for n, item in enumerate(section['items'], start=1):
        lead = [Paragraph(f"<b>{n}. {_t(item['title'])}</b>", st['entry'])]
        meta = ' | '.join(_t(x) for x in (item.get('subtitle'), item.get('dates')) if x)
        if meta:
            lead.append(Paragraph(meta, st['left']))
        bullets = _bullets(item.get('bullets'), st)
        rest = bullets[2:]
        if item.get('tech'):
            rest.append(Paragraph(f"Technologies: {_t(item['tech'])}", st['tech']))
        rest.append(Spacer(1, 3))
        blocks.append((lead + bullets[:2], rest))
    return blocks


def _education_blocks(section, st):
    blocks = []
    for item in section['items']:
        keep = [Paragraph(f"<b>{_t(item['title'])}</b>", st['entry'])]
        if item.get('meta'):
            keep.append(Paragraph(_t(item['meta']), st['left']))
        blocks.append((keep, [Spacer(1, 4)]))
    return blocks


def _skill_blocks(section, st):
    rows = [[Paragraph(_t(g['label']), st['skill_label']), Paragraph(_t(', '.join(g['items'])), st['left'])]
            for g in section['groups']]
    # One row per flowable, so a long skills list can still break across pages.
    return [([_plain_table([row], [SKILL_LABEL_W, CONTENT_W - SKILL_LABEL_W])], []) for row in rows]


def _declaration_blocks(section, st):
    keep = [Paragraph(_t(section['text']), st['body']), Spacer(1, 8)]
    if section.get('place'):
        keep.append(Paragraph(f"<b>PLACE :</b> {_t(section['place'])}", st['left']))
    date = f"<b>DATE :</b> {_t(section['date'])}" if section.get('date') else ''
    keep.append(_plain_table([[Paragraph(date, st['left']), Paragraph(_t(section.get('name', '')).upper(), st['right'])]],
                             [CONTENT_W * 0.5, CONTENT_W * 0.5]))
    return [(keep, [])]


def _section_flowables(section, st):
    heading = [Paragraph(_t(section['heading']).upper(), st['heading']),
               HRFlowable(width='100%', thickness=0.75, color=INK, spaceBefore=2, spaceAfter=6)]
    kind = section['kind']
    # [(keep_together, rest)]. KeepTogether is never nested: its wrap() reports
    # a huge height, which makes an enclosing KeepTogether break the page.
    if kind == 'text':
        blocks = [([Paragraph(_rich(line), st['body'])], []) for line in section['text'].split('\n') if line.strip()]
    elif kind == 'skills':
        blocks = _skill_blocks(section, st)
    elif kind == 'bullets':
        blocks = [([p], []) for p in _bullets(section['items'], st)]
    elif kind == 'compact':
        dash = _ch('\u2013', '-')
        blocks = []
        for i in section['items']:
            text = _t(i['title'])
            if i.get('subtitle'):
                text += f" - {_t(i['subtitle'])}"
            if i.get('dates'):
                text += f" {dash} {_t(i['dates'])}" if not i.get('subtitle') else f", {_t(i['dates'])}"
            blocks.append(([Paragraph(text, st['bullet'], bulletText=_ch('\u2022', '-'))], []))
    elif kind == 'jobs':
        blocks = _job_blocks(section, st)
    elif kind == 'projects':
        blocks = _project_blocks(section, st)
    elif kind == 'education':
        blocks = _education_blocks(section, st)
    elif kind == 'declaration':
        blocks = _declaration_blocks(section, st)
    else:
        blocks = []
    if not blocks:
        return []
    flow = []
    for index, (keep, rest) in enumerate(blocks):
        if index == 0:
            keep = heading + keep   # a heading always travels with the start of its section
        flow.append(KeepTogether(keep) if len(keep) > 1 else keep[0])
        flow.extend(rest)
    return flow


def render_pdf(document):
    """Resume document dict → PDF bytes."""
    _register_fonts()
    st = _styles()
    buf = io.BytesIO()
    name = document.get('name') or 'Resume'
    title = document.get('title') or ''
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X, topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
        title=_safe(f'{name} – {title} Resume' if title else f'{name} Resume'),
        author=_safe(name), subject=_safe(f'{title} resume' if title else 'Resume'),
        creator='CareerBuddy Resume Builder',
    )
    story = [Paragraph(_t(name).upper(), st['name'])]
    if title:
        story.append(Paragraph(_t(title), st['title']))
    if document.get('contact'):
        story.append(Paragraph(_contact_line(document['contact']), st['contact']))
    for section in document.get('sections') or []:
        story.extend(_section_flowables(section, st))
    doc.build(story)
    return buf.getvalue()


def render_page_images(pdf_bytes, scale=1.35, max_pages=6):
    """PDF bytes → list of PNG bytes, one per page (for the 'Preview Pages' view).

    Uses pypdfium2, which ships with the existing pdfplumber dependency. Returns
    (images, total_pages).
    """
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        total = len(pdf)
        images = []
        for index in range(min(total, max_pages)):
            page = pdf[index]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            out = io.BytesIO()
            image.save(out, format='PNG', optimize=True)
            images.append(out.getvalue())
            page.close()
        return images, total
    finally:
        pdf.close()
