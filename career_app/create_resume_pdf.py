"""PDF output for the Create Resume module — Classic, Modern and Minimal.

All three templates print the same document (``create_resume.build_document``)
as real, selectable text in one ATS-friendly column on A4; they differ only in
typography and restrained styling:

  Classic  serif, centred upper-case name, black headings over a full rule
  Modern   sans-serif, left-aligned header, subtle blue accent on name/headings
  Minimal  sans-serif, compact spacing, small grey headings, no rules

No tables, text boxes, images or rating bars are used for content, contact
details stay in the body (not in page headers/footers), and the reading order
is the visual order, so applicant-tracking systems parse it cleanly. Fonts are
Unicode TrueType families with embedded subsets (see ``resume_pdf``).
"""
import io
import os
import re
import unicodedata
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from .resume_pdf import _FALLBACK_CHARS, SANS_FONTS, SERIF_FONTS, render_page_images  # noqa: F401

LINK = '#1155cc'
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_families = {}


def _family(kind):
    """Register (once) and return (font family name, glyph set) for 'serif' or 'sans'."""
    if kind in _families:
        return _families[kind]
    name = 'CBCreate' + kind.title()
    candidates = (SERIF_FONTS + SANS_FONTS) if kind == 'serif' else SANS_FONTS
    for files in candidates:
        if not all(os.path.isfile(f) for f in files):
            continue
        try:
            faces = [TTFont(f'{name}{s}', path) for s, path in zip(('', '-Bold', '-Italic', '-BoldItalic'), files)]
        except Exception:
            continue
        for face in faces:
            pdfmetrics.registerFont(face)
        pdfmetrics.registerFontFamily(name, normal=name, bold=f'{name}-Bold', italic=f'{name}-Italic',
                                      boldItalic=f'{name}-BoldItalic')
        _families[kind] = (name, set(faces[0].face.charToGlyph.keys()))
        return _families[kind]
    raise RuntimeError('No TrueType font available for resume PDFs.')


TEMPLATES = {
    'classic': dict(font='serif', ink='#111111', accent='#111111', muted='#111111', rule='#111111', rule_w=0.75,
                    align_header=TA_CENTER, upper_name=True, name=20, title=11, contact=9.5, heading=11,
                    body=10, leading=13.2, entry=10.5, meta=10, head_before=12, justify=True),
    'modern': dict(font='sans', ink='#1f2937', accent='#1d4ed8', muted='#4b5563', rule='#93c5fd', rule_w=0.9,
                   align_header=TA_LEFT, upper_name=False, name=22, title=11.5, contact=9, heading=10.5,
                   body=9.6, leading=13, entry=10, meta=9.2, head_before=12, justify=False),
    'minimal': dict(font='sans', ink='#111827', accent='#111827', muted='#6b7280', rule=None, rule_w=0,
                    align_header=TA_LEFT, upper_name=False, name=18, title=10.5, contact=8.8, heading=9.2,
                    body=9.4, leading=12.4, entry=9.8, meta=9, head_before=10, justify=False),
}

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
MARGIN_Y = 16 * mm


class _Renderer:
    def __init__(self, template):
        self.cfg = TEMPLATES.get(template, TEMPLATES['classic'])
        self.font, self.glyphs = _family(self.cfg['font'])
        c, f = self.cfg, self.font
        ink, muted, accent = colors.HexColor(c['ink']), colors.HexColor(c['muted']), colors.HexColor(c['accent'])
        body_align = TA_JUSTIFY if c['justify'] else TA_LEFT
        self.st = {
            'name': ParagraphStyle('name', fontName=f'{f}-Bold', fontSize=c['name'], leading=c['name'] * 1.2,
                                   textColor=ink, alignment=c['align_header']),
            'title': ParagraphStyle('title', fontName=f, fontSize=c['title'], leading=c['title'] * 1.35,
                                    textColor=accent if c['accent'] != c['ink'] else (muted if c['muted'] != c['ink'] else ink),
                                    alignment=c['align_header'], spaceBefore=2),
            'contact': ParagraphStyle('contact', fontName=f, fontSize=c['contact'], leading=c['contact'] * 1.35,
                                      textColor=muted if c['muted'] != c['ink'] else ink,
                                      alignment=c['align_header'], spaceBefore=2),
            'heading': ParagraphStyle('heading', fontName=f'{f}-Bold', fontSize=c['heading'], leading=c['heading'] * 1.3,
                                      textColor=accent if c['accent'] != c['ink'] else (muted if c['rule'] is None else ink),
                                      spaceBefore=c['head_before'], spaceAfter=0 if c['rule'] else 3),
            'body': ParagraphStyle('body', fontName=f, fontSize=c['body'], leading=c['leading'], textColor=ink,
                                   alignment=body_align),
            'left': ParagraphStyle('left', fontName=f, fontSize=c['body'], leading=c['leading'], textColor=ink),
            'entry': ParagraphStyle('entry', fontName=f'{f}-Bold', fontSize=c['entry'], leading=c['entry'] * 1.3,
                                    textColor=ink, spaceBefore=3),
            'meta': ParagraphStyle('meta', fontName=f, fontSize=c['meta'], leading=c['meta'] * 1.35,
                                   textColor=muted if c['muted'] != c['ink'] else ink, spaceAfter=1),
            'bullet': ParagraphStyle('bullet', fontName=f, fontSize=c['body'], leading=c['leading'], textColor=ink,
                                     alignment=body_align, leftIndent=14, bulletIndent=4, bulletFontName=f,
                                     bulletFontSize=c['body'], spaceBefore=1.5),
            'group': ParagraphStyle('group', fontName=f'{f}-Bold', fontSize=c['body'], leading=c['leading'],
                                    textColor=ink, spaceBefore=3),
            'note': ParagraphStyle('note', fontName=f, fontSize=c['body'], leading=c['leading'], textColor=ink,
                                   alignment=body_align, spaceBefore=2),
        }

    # -- text helpers ------------------------------------------------------
    def safe(self, text):
        out = []
        for ch in str(text or ''):
            if ch in '\n\t' or ord(ch) in self.glyphs:
                out.append(ch)
            elif ch in _FALLBACK_CHARS:
                out.append(_FALLBACK_CHARS[ch])
            else:
                out.append(unicodedata.normalize('NFKD', ch).encode('ascii', 'ignore').decode() or '?')
        return ''.join(out)

    def t(self, text):
        return escape(self.safe(text))

    def rich(self, text):
        return _BOLD_RE.sub(r'<b>\1</b>', self.t(text))

    def link(self, text, href):
        href = escape(href, {'"': '&quot;'})
        return f'<a href="{href}" color="{LINK}"><u>{self.t(text)}</u></a>'

    def bullet_char(self):
        return '•' if 0x2022 in self.glyphs else '-'

    def bullets(self, items):
        return [Paragraph(self.rich(b), self.st['bullet'], bulletText=self.bullet_char()) for b in items or []]

    # -- blocks --------------------------------------------------------------
    def heading(self, text):
        out = [Paragraph(self.t(text).upper(), self.st['heading'])]
        if self.cfg['rule']:
            out.append(HRFlowable(width='100%', thickness=self.cfg['rule_w'], color=colors.HexColor(self.cfg['rule']),
                                  spaceBefore=2, spaceAfter=5))
        return out

    def entry_blocks(self, item):
        head = f"<b>{self.t(item['title'])}</b>"
        if item.get('subtitle'):
            head += f"&nbsp;&nbsp;|&nbsp;&nbsp;{self.t(item['subtitle'])}"
        lead = [Paragraph(head, self.st['entry'])]
        if item.get('meta'):
            lead.append(Paragraph(self.t(item['meta']), self.st['meta']))
        if item.get('link') and item['link'].get('href'):
            lead.append(Paragraph(self.link(item['link']['text'], item['link']['href']), self.st['meta']))
        body = [Paragraph(self.rich(x), self.st['body']) for x in item.get('paragraphs') or []]
        notes = item.get('notes') or []
        role = [n for n in notes if n['label'] == 'Role']
        body += [Paragraph(f"<b>{self.t(n['label'])}:</b> {self.t(n['text'])}", self.st['note']) for n in role]
        body += self.bullets(item.get('bullets'))
        for g in item.get('groups') or []:
            body.append(Paragraph(f"{self.t(g['label'])}:", self.st['group']))
            body += self.bullets(g['bullets'])
        body += [Paragraph(f"<i>{self.t(n['label'])}: {self.t(n['text'])}</i>", self.st['note'])
                 for n in notes if n['label'] != 'Role']
        # The entry heading travels with its first two lines so it never sits alone at a page bottom.
        return lead + body[:2], body[2:] + [Spacer(1, 5)]

    def item_blocks(self, item):
        text = f"<b>{self.t(item['title'])}</b>"
        if item.get('text'):
            text += f" – {self.t(item['text'])}"
        if item.get('link') and item['link'].get('href'):
            text += f" | {self.link(item['link']['text'], item['link']['href'])}"
        keep = [Paragraph(text, self.st['bullet'], bulletText=self.bullet_char())]
        if item.get('detail'):
            keep.append(Paragraph(self.rich(item['detail']), ParagraphStyle('d', parent=self.st['body'], leftIndent=14)))
        return keep, []

    def section(self, section):
        kind = section['kind']
        if kind == 'text':
            blocks = [([Paragraph(self.rich(x), self.st['body'])], []) for x in section['text'].split('\n') if x.strip()]
        elif kind == 'lines':
            blocks = [([Paragraph(f"<b>{self.t(i['label'])}:</b> {self.t(i['text'])}", self.st['left'])], [])
                      for i in section['items']]
        elif kind == 'entries':
            blocks = [self.entry_blocks(i) for i in section['items']]
        elif kind == 'items':
            blocks = [self.item_blocks(i) for i in section['items']]
        else:
            blocks = []
        flow = []
        for index, (keep, rest) in enumerate(blocks):
            if index == 0:
                keep = self.heading(section['heading']) + keep   # heading travels with its first entry
            flow.append(KeepTogether(keep) if len(keep) > 1 else keep[0])
            flow.extend(rest)
        return flow

    def header(self, doc):
        name = self.t(doc.get('name') or 'Your Name')
        story = [Paragraph(name.upper() if self.cfg['upper_name'] else name, self.st['name'])]
        if doc.get('title'):
            story.append(Paragraph(self.t(doc['title']), self.st['title']))
        parts = []
        for c in doc.get('contact') or []:
            text = self.t(c['text']).replace(' ', '&nbsp;')
            parts.append(f'<a href="{escape(c["href"])}" color="{LINK}"><u>{text}</u></a>' if c.get('href') else text)
        if parts:
            story.append(Paragraph(' | '.join(parts), self.st['contact']))
        links = [self.link(l['text'], l['href']) for l in doc.get('links') or []]
        if links:
            story.append(Paragraph(' | '.join(links), self.st['contact']))
        if doc.get('address'):
            story.append(Paragraph(self.t(doc['address']), self.st['contact']))
        if self.cfg['font'] == 'sans' and self.cfg['rule']:
            story.append(HRFlowable(width='100%', thickness=1.4, color=colors.HexColor(self.cfg['accent']),
                                    spaceBefore=6, spaceAfter=0))
        return story


def render_pdf(document):
    """Create Resume document dict → PDF bytes in the document's template."""
    r = _Renderer(document.get('template'))
    buf = io.BytesIO()
    name = document.get('name') or 'Resume'
    title = document.get('title') or ''
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X, topMargin=MARGIN_Y, bottomMargin=MARGIN_Y,
        title=r.safe(f'{name} – {title} Resume' if title else f'{name} Resume'), author=r.safe(name),
        subject=r.safe(f'{title} resume' if title else 'Resume'), creator='CareerBuddy Resume Builder',
    )
    story = r.header(document)
    for section in document.get('sections') or []:
        story.extend(r.section(section))
    doc.build(story)
    return buf.getvalue()
