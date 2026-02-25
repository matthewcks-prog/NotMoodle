from django.db import models
from student_management.models import Student
from lesson_management.models import Lesson
from teachersManagement.models import TeacherProfile

class Course(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    total_credits_required = models.PositiveIntegerField(default=144)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="inactive",   # safer default
    )
    # NEW: Course director field
    director = models.ForeignKey(
        TeacherProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="directed_courses",
        help_text="Teacher responsible for directing this course"
    )
    # Optional free-text director display name (used when no teacher profile is selected)
    director_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    lessons = models.ManyToManyField(
        Lesson,
        through="CourseLesson",
        related_name="courses",   # <-- this creates Lesson.courses
        blank=True,
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def check_graduation_eligibility(self, student):
        """
        Check if a student is eligible to graduate from this course.
        Returns (is_eligible, total_credits, core_lessons_completed) tuple.
        
        Credits are counted from ALL passed lessons (core, electives, and any other lessons),
        but graduation also requires completing all core lessons for the course.
        """
        from lesson_management.models import LessonEnrollment

        # Get all required lessons for this course
        core_lesson_ids = set(
            self.course_lessons.filter(is_required=True).values_list('lesson_id', flat=True)
        )

        # Get ALL lesson enrollments for this student (not just course lessons)
        # This allows electives and any other passed lessons to contribute credits
        all_lesson_enrollments = LessonEnrollment.objects.filter(
            student=student
        ).select_related('lesson')

        # Initialize sets and counters
        completed_core_lessons = set()
        total_credits = 0
        
        for enrollment in all_lesson_enrollments:
            # Check if student has passed this lesson
            passed, _, _ = enrollment.lesson.student_passed(student)
            
            if passed:
                # Add credits from ANY passed lesson (core, elective, or other)
                total_credits += enrollment.lesson.lesson_credits
                
                # Track if this is a core lesson that was passed
                if enrollment.lesson.id in core_lesson_ids:
                    completed_core_lessons.add(enrollment.lesson.id)

        # Student is eligible if they have enough credits AND completed all core lessons
        has_all_core = len(completed_core_lessons) == len(core_lesson_ids)
        has_enough_credits = total_credits >= self.total_credits_required
        
        return (
            has_enough_credits and has_all_core,  # is_eligible
            total_credits,  # total credits earned
            has_all_core  # whether all core lessons are complete
        )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["code"]),
        ]



class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_by = models.CharField(
        max_length=10,
        choices=[("student", "Student Self-Enrollment"), ("teacher", "Teacher Enrollment")]
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student.full_name()} → {self.course.code} ({self.enrolled_by})"


class CourseLesson(models.Model):
    """Many-to-many relationship between courses and lessons"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_lessons")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_courses")
    order = models.PositiveIntegerField(default=0, help_text="Order of lesson in course")
    is_required = models.BooleanField(default=True, help_text="Whether this lesson is required for course completion")
    
    class Meta:
        unique_together = ("course", "lesson")
        ordering = ["order", "lesson__unit_code"]
    
    def __str__(self):
        return f"{self.course.code} → {self.lesson.unit_code}"
