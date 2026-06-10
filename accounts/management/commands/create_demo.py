"""
Management command: create_demo
Creates a demo student account for visitors to explore the site.

Usage:
    python manage.py create_demo
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a demo student account with A1 level"

    def handle(self, *args, **options):
        from accounts.models import User, StudentProfile
        from curriculum.models import Level

        email    = "demo@learnarabicasl.com"
        password = "Demo1234!"

        # Use C2 (highest level) so demo can access ALL courses
        try:
            a1 = Level.objects.get(code="C2")
        except Level.DoesNotExist:
            a1 = Level.objects.order_by("-order").first()

        # Create user if not exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"Demo account already exists: {email}"))
            # Make sure level is set
            user = User.objects.get(email=email)
            profile = getattr(user, "student_profile", None)
            if profile and a1 and not profile.current_level:
                profile.current_level = a1
                profile.save()
            return

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name="Demo",
            last_name="Student",
            role=User.Role.STUDENT,
        )

        # Set A1 level on the auto-created profile
        try:
            profile = user.student_profile
            profile.current_level = a1
            profile.age_track = "adult"
            profile.native_language = "English"
            profile.save()
        except StudentProfile.DoesNotExist:
            StudentProfile.objects.create(
                user=user,
                current_level=a1,
                age_track="adult",
                native_language="English",
            )

        self.stdout.write(self.style.SUCCESS(
            f"Demo account created: {email} / {password}"
        ))
