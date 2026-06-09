"""
core/context_processors.py

Functions registered in TEMPLATES['OPTIONS']['context_processors'] run on
every template render and merge their return dict into the context.

Use sparingly — anything in here loads on every page. Right now we only
expose SITE_NAME so {{ SITE_NAME }} works in any template (navbar, title,
emails, etc.) without each view having to pass it.
"""

from django.conf import settings


def site_globals(request):
    """Inject site-wide values into every template context."""
    return {
        "SITE_NAME": settings.SITE_NAME,
    }
