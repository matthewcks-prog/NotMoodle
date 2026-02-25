from typing import Tuple
from django.contrib import messages
from django.shortcuts import get_object_or_404
from .models import Course, Enrollment, Student


def enrol_student_in_course(request, student: Student, course_id: int) -> Tuple[Enrollment, bool]:
    """Enroll a student in a course, if not already. Returns (enrollment, created)."""
    course = get_object_or_404(Course, pk=course_id, status="active")

    # Try to fetch existing enrollment
    existing = Enrollment.objects.filter(student=student, course=course).first()
    if existing:
        # Don't spam the "already enrolled" message, just return silently
        return existing, False

    # Otherwise create a new enrollment
    enrollment = Enrollment.objects.create(
        student=student,
        course=course,
        enrolled_by="student",
    )
    messages.success(request, f"You enrolled in {course.name}.")
    return enrollment, True
