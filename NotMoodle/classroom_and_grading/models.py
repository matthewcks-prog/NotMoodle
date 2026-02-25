from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

from student_management.models import Student
from course_management.models import Course
from lesson_management.models import Lesson, Assignment
from teachersManagement.models import TeacherProfile


class Classroom(models.Model):
    # Cascade classroom lifecycle when the owning course/lesson/teacher is removed.
    # This ensures admin-deletes of users (which cascade to TeacherProfile/Student)
    # will not be blocked by PROTECT and will remove associated classrooms.
    course = models.ForeignKey('course_management.Course', on_delete=models.CASCADE, related_name='classrooms')
    lesson = models.ForeignKey('lesson_management.Lesson', on_delete=models.CASCADE, related_name='classrooms')
    teacher = models.ForeignKey('teachersManagement.TeacherProfile', on_delete=models.CASCADE, related_name='classrooms')

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'lesson', 'teacher', 'start_date'],
                name='uniq_classroom_slot_per_teacher'
            )
        ]

    def __str__(self):
        return f"{self.course} • {self.lesson} • {self.start_date:%Y-%m-%d}"
    
    def clean(self):
        super().clean()
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before start date.'
                })

    # Optional: keep a computed duration helper (different name!)
    @property
    def duration(self):
        if self.start_date and self.end_date:
            return self.end_date - self.start_date
        return None


class ClassroomStudent(models.Model):
    classroom = models.ForeignKey("Classroom", on_delete=models.CASCADE, related_name="roster")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="classroom_rosters")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("classroom", "student")
        ordering = ["student_id"]

    def __str__(self):
        return f"{self.classroom_id} → {self.student_id}"

class AssignmentGrade(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="grades")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="assignment_grades")
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    feedback = models.TextField(blank=True)
    # If a teacher is deleted, cascade removal of grades they authored so
    # admin-delete of the underlying user cleans up related grade records.
    graded_by = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="given_grades", null=True, blank=True)
    graded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["student_id"]

    def __str__(self):
        return f"{self.assignment.title} · {self.student_id} · {self.marks_awarded}"


# ---------------------------
# Signal: Award credits when student passes a lesson
# ---------------------------
@receiver(post_save, sender=AssignmentGrade)
def award_credits_on_pass(sender, instance, created, **kwargs):
    """
    Award credits to student when they pass a lesson (>50% total marks).
    Credits are awarded only once per lesson, for both core and elective units.
    """
    from student_management.models import ManageCreditPoint
    from lesson_management.models import LessonCreditAwarded
    
    # Only process if marks_awarded is set (not None)
    if instance.marks_awarded is None:
        return
    
    # Get the lesson for this assignment
    lesson = instance.assignment.lesson
    student = instance.student
    
    # Check if student has already been awarded credits for this lesson
    if LessonCreditAwarded.objects.filter(student=student, lesson=lesson).exists():
        return  # Already awarded, don't double-award
    
    # Check if student has passed the lesson (>50%)
    passed, percentage, details = lesson.student_passed(student)
    
    if passed:
        # Award credits for this lesson (both core and elective units count)
        credit, _ = ManageCreditPoint.objects.get_or_create(student=student)
        credits_amount = max(1, int(lesson.lesson_credits or 0))
        credit.increase(amount=credits_amount)
        
        # Record that credits have been awarded for this lesson
        LessonCreditAwarded.objects.create(
            student=student,
            lesson=lesson,
            credits_amount=credits_amount
        )