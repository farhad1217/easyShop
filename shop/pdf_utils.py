"""
PDF generation utilities with Bengali/Unicode font support.
Uses Noto Sans Bengali for clear, readable Bangla in PDFs.
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
    """Find and register a Bengali-supporting font. Prefers Noto Sans Bengali."""
    global _BANGLA_FONT_REGISTERED, _BANGLA_FONT_NAME
    if _BANGLA_FONT_REGISTERED:
        return _BANGLA_FONT_NAME

    try:
        import reportlab.rl_config
        reportlab.rl_config.warnOnMissingFontGlyphs = 0
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return None

    base = str(settings.BASE_DIR)
    windir = os.environ.get('WINDIR') or os.environ.get('SYSTEMROOT') or 'C:\\Windows'
    font_paths = [
        os.path.join(base, 'shop', 'static', 'fonts', 'NotoSansBengali-Regular.ttf'),
        os.path.join(base, 'shop', 'fonts', 'NotoSansBengali-Regular.ttf'),
        os.path.join(windir, 'Fonts', 'Nirmala.ttf'),
        os.path.join(windir, 'Fonts', 'Vrinda.ttf'),
        '/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf',
    ]

    for path in font_paths:
        if path and os.path.isfile(path):
            try:
                name = 'BanglaFont'
                pdfmetrics.registerFont(TTFont(name, path))
                pdfmetrics.registerFontFamily(
                    name,
                    normal=name,
                    bold=name,
                    italic=name,
                    boldItalic=name,
                )
                _BANGLA_FONT_REGISTERED = True
                _BANGLA_FONT_NAME = name
                return name
            except Exception:
                continue
    return None


def get_pdf_styles(font_name=None):
    """Get ParagraphStyles with Bengali font support."""
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    font = font_name or _find_bengali_font()
    if not font:
        font = 'Helvetica'
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name='BanglaTitle',
        parent=base['Title'],
        fontName=font,
        fontSize=18,
        spaceAfter=16,
        textColor='#0f172a',
        alignment=1,
    )
    heading_style = ParagraphStyle(
        name='BanglaHeading',
        parent=base['Heading2'],
        fontName=font,
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor='#1e40af',
    )
    body_style = ParagraphStyle(
        name='BanglaBody',
        parent=base['Normal'],
        fontName=font,
        fontSize=11,
        spaceAfter=6,
        textColor='#334155',
    )
    return {'title': title_style, 'heading': heading_style, 'body': body_style, 'font': font}


def safe_paragraph(style, text):
    """Create a ReportLab Paragraph with escaped text. Preserves line breaks."""
    from reportlab.platypus import Paragraph
    if text is None:
        text = ''
    escaped = _escape_for_paragraph(str(text))
    escaped = escaped.replace('\n', '<br/>')
    return Paragraph(escaped, style)


def safe_paragraph_bold(style, text):
    """Create a bold Paragraph with escaped text."""
    from reportlab.platypus import Paragraph
    escaped = _escape_for_paragraph(text)
    return Paragraph(f'<b>{escaped}</b>', style)


def _get_bengali_font_path():
    """Return path to a Bengali+Latin supporting TTF font. Nirmala has both on Windows."""
    base = str(settings.BASE_DIR)
    windir = os.environ.get('WINDIR') or os.environ.get('SYSTEMROOT') or 'C:\\Windows'
    paths = [
        os.path.join(windir, 'Fonts', 'Nirmala.ttf'),
        os.path.join(windir, 'Fonts', 'Vrinda.ttf'),
        os.path.join(base, 'shop', 'static', 'fonts', 'NotoSansBengali-Regular.ttf'),
        os.path.join(base, 'shop', 'fonts', 'NotoSansBengali-Regular.ttf'),
        '/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf',
    ]
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None


def generate_list_entry_pdf_fpdf2(lists):
    """Generate list entry PDF using fpdf2 (better Bengali support). Returns bytes or None."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    font_path = _get_bengali_font_path()
    if not font_path:
        return None
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(True, margin=18)
        pdf.add_page()
        pdf.set_margins(18, 18, 18)
        pdf.add_font('Bangla', '', font_path, uni=True)
        pdf.add_font('Bangla', 'B', font_path, uni=True)
    except Exception:
        return None
    w = pdf.epw
    pdf.set_font('Bangla', '', 11)
    pdf.ln(5)
    pdf.set_font('Bangla', 'B', 16)
    pdf.multi_cell(w, 8, 'লিস্ট এন্ট্রি - সব লিস্ট (পিডিএফ)', align='C')
    pdf.ln(8)
    if not lists:
        pdf.set_font('Bangla', '', 10)
        pdf.multi_cell(w, 5, 'কোনো লিস্ট নেই।')
        return pdf.output(dest='S')
    for idx, lst in enumerate(lists, 1):
        name = getattr(lst, 'user_display_name', lst.family.username)
        pdf.set_font('Bangla', 'B', 11)
        pdf.multi_cell(w, 6, f'সিরিয়াল: {idx} | লিস্ট: {lst.list_id} | ব্যবহারকারী: {name}')
        pdf.set_font('Bangla', '', 10)
        dt = lst.created_at.strftime('%d/%m/%Y %H:%M') if lst.created_at else '-'
        pdf.multi_cell(w, 5, f'তারিখ: {dt}')
        pdf.set_font('Bangla', 'B', 10)
        pdf.multi_cell(w, 5, 'মূল লিস্ট:')
        pdf.set_font('Bangla', '', 10)
        content = (lst.content or '—').replace('\r\n', '\n').replace('\r', '\n')
        pdf.multi_cell(w, 5, content)
        if lst.ai_content:
            pdf.set_font('Bangla', 'B', 10)
            pdf.multi_cell(w, 5, 'AI লিস্ট:')
            pdf.set_font('Bangla', '', 10)
            pdf.multi_cell(w, 5, lst.ai_content.replace('\r\n', '\n').replace('\r', '\n'))
        pdf.ln(6)
    return pdf.output(dest='S')


def generate_consolidated_pdf_fpdf2(all_lines, dt, title='সম্মিলিত বাজার পয়েন্ট', pre_numbered=False):
    """Consolidated list PDF with fpdf2. pre_numbered=True if lines already have '১. ' etc."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    font_path = _get_bengali_font_path()
    if not font_path:
        return None
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    try:
        pdf.add_font('Bangla', '', font_path, uni=True)
        pdf.add_font('Bangla', 'B', font_path, uni=True)
    except Exception:
        return None
    w = pdf.epw
    pdf.set_font('Bangla', 'B', 16)
    pdf.multi_cell(w, 8, title + ' - ' + dt.strftime('%d/%m/%Y'), align='C')
    pdf.ln(8)
    pdf.set_font('Bangla', '', 10)
    if not all_lines:
        pdf.multi_cell(w, 5, 'কোনো আইটেম নেই।')
    else:
        for i, line in enumerate(all_lines, 1):
            txt = line if pre_numbered else f'{i}. {line}'
            pdf.multi_cell(w, 5, txt)
    return pdf.output(dest='S')
