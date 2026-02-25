from typing import Any, Dict
from django.contrib.auth.models import User
from .models import Student, ManageCreditPoint


def create_student_profile(strategy, details: Dict[str, Any], user: User=None, *args, **kwargs):
    """Ensure a Student profile exists for the authenticated user.

    Called by social-auth pipeline after a User has been created/associated.
    """
    if user is None:
        return
    # If a teacher profile exists, skip creating student
    if getattr(user, "teacherprofile", None) is not None or getattr(user, "teacher_profile", None) is not None:
        return
    student, created = Student.objects.get_or_create(
        user=user,
        defaults={
            "first_name": user.first_name or (details.get("first_name") or ""),
            "last_name": user.last_name or (details.get("last_name") or ""),
            "email": user.email or details.get("email") or f"{user.username}@example.com",
            "date_of_birth": details.get("date_of_birth") or "2000-01-01",
            "status": "active",
        },
    )
    # Ensure credit record
    ManageCreditPoint.objects.get_or_create(student=student)


