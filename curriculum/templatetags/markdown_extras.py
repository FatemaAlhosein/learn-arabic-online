"""
curriculum/templatetags/markdown_extras.py
-------------------------------------------
Custom template filter that converts Markdown text to safe HTML.

Usage in templates:
    {% load markdown_extras %}
    {{ lesson.body_markdown|markdownify }}
"""

import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Extensions that make the output much richer:
#   - tables        → | col | col | style markdown tables
#   - fenced_code   → ``` code blocks ```
#   - attr_list     → add CSS classes/ids to any element {.class #id}
#   - nl2br         → bare newlines become <br> (friendlier for non-devs)
#   - toc           → auto-generates anchor IDs on headings (nice for long lessons)
#   - md_in_html    → render markdown inside HTML blocks (needed for colour spans)
_MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "attr_list",
    "nl2br",
    "toc",
    "md_in_html",
]


@register.filter(name="markdownify", is_safe=True)
def markdownify(value):
    """Convert a Markdown string to HTML (safe to render in templates)."""
    if not value:
        return ""
    html = markdown.markdown(str(value), extensions=_MD_EXTENSIONS)
    return mark_safe(html)
