from typing import Dict
from django.db.models import QuerySet
from .models import Course, Enrollment


def get_all_courses_ordered_by_name() -> QuerySet[Course]:
    """Return all courses ordered by name for catalog/admin listings."""
    return Course.objects.all().order_by("name")


def get_enrolled_course_ids_for_student(student_id: int) -> set[int]:
    """Return a set of course ids that the given student is enrolled in."""
    return set(
        Enrollment.objects.filter(student_id=student_id).values_list("course_id", flat=True)
    )


