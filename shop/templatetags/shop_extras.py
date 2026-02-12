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
