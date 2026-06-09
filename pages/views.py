"""
pages/views.py

Cross-cutting public pages (home, about, etc.).
"""

from django.views.generic import TemplateView

from curriculum.models import Course


class HomeView(TemplateView):
    """Public homepage. Passes featured courses + stats to the template."""
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Featured = the 6 most recently published courses
        ctx["featured_courses"] = (
            Course.objects
            .filter(is_published=True)
            .select_related("level", "category", "teacher")
            .order_by("-created_at")[:6]
        )

        # Site-wide stats for the stats strip
        from django.db.models import Count
        from accounts.models import User
        from curriculum.models import Enrollment, Level

        ctx["stats"] = {
            "students":  User.objects.filter(role="student").count(),
            "courses":   Course.objects.filter(is_published=True).count(),
            "levels":    Level.objects.count(),
            "enrolled":  Enrollment.objects.filter(status="active").count(),
        }
        return ctx


class ReadingPracticeView(TemplateView):
    """
    Standalone printable reading-practice worksheets for young learners.
    The template is self-contained (does NOT extend base.html) so it
    prints cleanly without the site navbar/footer.
    Accessible to any logged-in user; linked from the student dashboard.
    """
    template_name = "pages/reading_practice.html"
