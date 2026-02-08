"""
PDF generation utilities with Bengali/Unicode font support.
"""
import os
from django.conf import settings
from xml.sax.saxutils import escape

_BANGLA_FONT_REGISTERED = False
_BANGLA_FONT_NAME = 'Helvetica'  # fallback


def _escape_for_paragraph(text):
    """Escape text for ReportLab Paragraph (handles & < > to avoid XML errors)."""
    if not text:
        return ''
    return escape(str(text))


def _find_bengali_font():
    """Find and register a Bengali-supporting font. Returns font name or None."""
    global _BANGLA_FONT_REGISTERED, _BANGLA_FONT_NAME
    if _BANGLA_FONT_REGISTERED:
        return _BANGLA_FONT_NAME

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return None

    windir = os.environ.get('WINDIR') or os.environ.get('SYSTEMROOT') or 'C:\\Windows'
    font_paths = [
        # Windows Bengali fonts (Nirmala supports Bengali)
        os.path.join(windir, 'Fonts', 'Nirmala.ttf'),
        os.path.join(windir, 'Fonts', 'NirmalaB.ttf'),
        os.path.join(windir, 'Fonts', 'Vrinda.ttf'),
        os.path.join(windir, 'Fonts', 'Shonar.ttf'),
        # Project fonts
        os.path.join(settings.BASE_DIR, 'shop', 'static', 'fonts', 'NotoSansBengali-Regular.ttf'),
        os.path.join(settings.BASE_DIR, 'shop', 'fonts', 'NotoSansBengali-Regular.ttf'),
        os.path.join(settings.BASE_DIR, 'shop', 'static', 'fonts', 'Siyamrupali_1_01.ttf'),
        os.path.join(settings.BASE_DIR, 'shop', 'fonts', 'Siyamrupali_1_01.ttf'),
        # Linux
        '/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf',
    ]

    for path in font_paths:
        if path and os.path.isfile(path):
            try:
                name = 'BanglaFont'
                pdfmetrics.registerFont(TTFont(name, path))
                _BANGLA_FONT_REGISTERED = True
                _BANGLA_FONT_NAME = name
                return name
            except Exception:
                continue
    return None


def get_pdf_styles(font_name=None):
    """Get ParagraphStyles with Bengali font support."""
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    font = font_name or _find_bengali_font() or 'Helvetica'
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name='BanglaTitle',
        parent=styles['Heading1'],
        fontName=font,
        fontSize=16,
        spaceAfter=14,
        textColor='#1e3a5f',
        alignment=1,  # CENTER
    )
    heading_style = ParagraphStyle(
        name='BanglaHeading',
        parent=styles['Heading2'],
        fontName=font,
        fontSize=11,
        spaceAfter=6,
        spaceBefore=10,
        textColor='#1e40af',
        leftIndent=0,
    )
    body_style = ParagraphStyle(
        name='BanglaBody',
        parent=styles['Normal'],
        fontName=font,
        fontSize=10,
        spaceAfter=6,
        textColor='#374151',
        leftIndent=10,
    )
    return {'title': title_style, 'heading': heading_style, 'body': body_style, 'font': font}


def safe_paragraph(style, text):
    """Create a ReportLab Paragraph with escaped text."""
    from reportlab.platypus import Paragraph
    escaped = _escape_for_paragraph(text)
    return Paragraph(escaped, style)


def safe_paragraph_bold(style, text):
    """Create a bold Paragraph with escaped text."""
    from reportlab.platypus import Paragraph
    escaped = _escape_for_paragraph(text)
    return Paragraph(f'<b>{escaped}</b>', style)
