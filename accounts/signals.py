"""
accounts/signals.py

When a User is created, auto-create the matching profile based on `role`:
  - role=teacher  -> TeacherProfile
  - role=student  -> StudentProfile
  - role=parent   -> ParentProfile
  - role=admin    -> no profile

Signals are registered when Django starts via accounts/apps.py:ready().
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ParentProfile, StudentProfile, TeacherProfile, User


@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    """Auto-create the matching profile the first time a User is saved."""

    # `created` is True only on the very first save (i.e. a new row).
    # Skip subsequent updates so we don't overwrite anything.
    if not created:
        return

    role = instance.role

    if role == User.Role.TEACHER:
        TeacherProfile.objects.get_or_create(user=instance)
    elif role == User.Role.STUDENT:
        StudentProfile.objects.get_or_create(user=instance)
    elif role == User.Role.PARENT:
        ParentProfile.objects.get_or_create(user=instance)
    # role=admin -> no profile (admins don't need one).
