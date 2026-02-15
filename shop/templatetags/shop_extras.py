from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def numbered_list(value):
    """Format content as numbered list: split by newlines, trim, remove empty, number."""
    if not value:
        return ''
    lines = [s.strip() for s in str(value).splitlines() if s.strip()]
    return '\n'.join(f'{i}. {line}' for i, line in enumerate(lines, 1))


@register.filter
def first_three_preview(value):
    """2 lines, number points. Max 4 items so no incomplete point at line end."""
    if not value:
        return '-'
    import re
    lines = [s.strip() for s in str(value).splitlines() if s.strip()]
    if not lines:
        return '-'
    def strip_number(txt):
        return re.sub(r'^[\d\u09E6-\u09EF\u0966-\u096F]+\s*[\.\)]\s*', '', txt, count=1).strip() or txt
    items = [strip_number(line) for line in lines]
    # Show max 3 items so 2-line clamp never cuts an incomplete number
    take = items[:3]
    numbered = [f'{i}. {item}' for i, item in enumerate(take, 1)]
    if len(numbered) == 1:
        return numbered[0]
    if len(numbered) == 2:
        return numbered[0] + ' • ' + numbered[1]
    line1 = numbered[0] + ' • ' + numbered[1]
    line2 = ' • '.join(numbered[2:])
    return line1 + '\n' + line2


@register.filter
def date_ampm(value):
    """Format datetime as dd/mm/yyyy h:mm AM/PM (always English AM/PM, no locale)."""
    if value is None:
        return ''
    try:
        if hasattr(value, 'strftime'):
            # Convert to local time if timezone-aware
            try:
                value = timezone.localtime(value)
            except Exception:
                # If conversion fails (e.g. date object), just use original value
                pass
            hour = getattr(value, 'hour', 0)
            minute = getattr(value, 'minute', 0)
            ampm = 'AM' if hour < 12 else 'PM'
            h = hour % 12
            if h == 0:
                h = 12
            return value.strftime('%d/%m/%Y') + f' {h}:{minute:02d} {ampm}'
        return str(value)
    except (ValueError, TypeError, AttributeError):
        return ''


@register.filter
def date_card(value):
    """Format datetime for bazar list cards: 10Feb 2026 (11:56 PM)."""
    if value is None:
        return ''
    try:
        if hasattr(value, 'strftime'):
            # Convert to local time if timezone-aware
            try:
                value = timezone.localtime(value)
            except Exception:
                # If conversion fails (e.g. date object), just use original value
                pass
            hour = getattr(value, 'hour', 0)
            minute = getattr(value, 'minute', 0)
            ampm = 'AM' if hour < 12 else 'PM'
            h = hour % 12
            if h == 0:
                h = 12
            return value.strftime('%d%b %Y') + f' ({h}:{minute:02d} {ampm})'
        return str(value)
    except (ValueError, TypeError, AttributeError):
        return ''
