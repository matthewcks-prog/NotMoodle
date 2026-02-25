from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from teachersManagement.models import TeacherProfile
from django.db.models.signals import post_save
from django.dispatch import receiver
from student_management.models import Student, ManageCreditPoint


# ---------------------------
# Lesson Model
# ---------------------------
class Lesson(models.Model):
    unit_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    objectives = models.TextField(blank=True)
    estimated_effort = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        help_text="Estimated effort (hours per week)."
    )
    youtube_link = models.URLField(blank=True, help_text="YouTube video URL for this lesson")
    youtube_thumbnail = models.URLField(blank=True, help_text="Auto-generated from YouTube link")

    prerequisites = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="unlocks"
    )
    lesson_designer = models.ForeignKey(
        TeacherProfile, on_delete=models.CASCADE, related_name="lessons"
    )
    date_of_creation = models.DateTimeField(auto_now_add=True)
    date_of_update = models.DateTimeField(auto_now=True)
    # Default each lesson to 6 credits unless explicitly set otherwise
    lesson_credits = models.PositiveSmallIntegerField(default=6)
    status = models.CharField(
        max_length=10,
        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
        default="draft"
    )

    class Meta:
        ordering = ["unit_code"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["unit_code"]),
        ]

    def __str__(self):
        return f"{self.unit_code} - {self.title}"

    def clean(self):
        super().clean()
        if self.pk and self.prerequisites.filter(pk=self.pk).exists():
            raise ValidationError("A lesson cannot list itself as a prerequisite.")

    # --- YouTube helpers ---
    def get_youtube_video_id(self):
        """Extract video ID from supported YouTube URL formats."""
        if not self.youtube_link:
            return None

        import re
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)',
            r'youtu\.be/([a-zA-Z0-9_-]+)',
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.youtube_link)
            if match:
                return match.group(1)
        return None

    def get_youtube_thumbnail(self):
        """Auto-generate YouTube thumbnail URL."""
        video_id = self.get_youtube_video_id()
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        return None

    def get_youtube_embed_url(self):
        """Return embeddable YouTube video URL."""
        video_id = self.get_youtube_video_id()
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return None

    def save(self, *args, **kwargs):
        if self.youtube_link and not self.youtube_thumbnail:
            self.youtube_thumbnail = self.get_youtube_thumbnail()
        super().save(*args, **kwargs)
    
    def student_passed(self, student):
        """
        Calculate if a student has passed this lesson (50%+ overall).
        Returns a tuple: (passed: bool, percentage: Decimal, details: dict)
        """
        from classroom_and_grading.models import AssignmentGrade
        from decimal import Decimal
        
        assignments = self.assignments.all()
        if not assignments.exists():
            return (False, Decimal('0'), {
                'message': 'No assignments in this lesson',
                'has_grades': False,
                'total_assignments': 0,
                'graded_assignments': 0
            })
        
        total_weightage = sum(a.weightage for a in assignments)
        if total_weightage == 0:
            return (False, Decimal('0'), {
                'message': 'Total weightage is 0',
                'has_grades': False,
                'total_assignments': assignments.count(),
                'graded_assignments': 0
            })
        
        # Calculate weighted score
        weighted_score = Decimal('0')
        graded_assignments = 0
        
        for assignment in assignments:
            try:
                grade = AssignmentGrade.objects.get(assignment=assignment, student=student)
                # Check if marks_awarded is not None (nullable field)
                if grade.marks_awarded is not None and assignment.marks > 0:
                    # Contribution is the achieved fraction times the assignment weightage (in %)
                    # e.g. 100% on a 50%-weight assignment contributes 50 to overall
                    weighted_contribution = (grade.marks_awarded / assignment.marks) * assignment.weightage
                    weighted_score += weighted_contribution
                    graded_assignments += 1
            except AssignmentGrade.DoesNotExist:
                # Student hasn't been graded for this assignment
                continue
        
        if graded_assignments == 0:
            return (False, Decimal('0'), {
                'message': 'No grades found for this student',
                'has_grades': False,
                'total_weightage': total_weightage,
                'graded_assignments': 0,
                'total_assignments': assignments.count()
            })
        
        # Final percentage is the sum of weighted contributions.
        # Cap at 100 in case of misconfigured weightage totals > 100.
        final_percentage = weighted_score if weighted_score <= 100 else Decimal('100')
        passed = final_percentage >= Decimal('50')
        
        return (passed, final_percentage, {
            'total_weightage': total_weightage,
            'graded_assignments': graded_assignments,
            'total_assignments': assignments.count(),
            'has_grades': True
        })


# ---------------------------
# Reading List
# ---------------------------
class ReadingList(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="reading_list")
    title = models.CharField(max_length=200)
    url = models.URLField(blank=True, help_text="Optional URL for the reading material")
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    class Meta:
        ordering = ["order", "title"]
        unique_together = ("lesson", "title")

    def __str__(self):
        return f"{self.lesson.unit_code} - {self.title}"


# ---------------------------
# Assignment and Attachments
# ---------------------------
def assignment_pdf_path(instance, filename):
    return f"lesson_files/lesson-{instance.lesson_id}/assignments/{filename}"

class Assignment(models.Model):
    title = models.CharField(max_length=200)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="assignments")
    release_date = models.DateTimeField()
    due_date = models.DateTimeField()
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    weightage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weightage percentage (0-100). Total weightage of all assignments in a lesson should be 100."
    )
    description = models.TextField(blank=True)
    pdf = models.FileField(
        upload_to=assignment_pdf_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        help_text="Assignment PDF file (optional)"
    )

    class Meta:
        ordering = ["due_date"]
        unique_together = ("lesson", "title")
        indexes = [models.Index(fields=["due_date"])]

    def __str__(self):
        return f"{self.title} ({self.lesson.title})"

    def clean(self):
        if self.due_date and self.release_date and self.due_date < self.release_date:
            raise ValidationError("Due date cannot be earlier than release date.")
    
    @property
    def pdf_filename(self):
        if self.pdf:
            return self.pdf.name.rsplit("/", 1)[-1]
        return None


def assignment_attachment_path(instance, filename):
    return f"lesson_files/lesson-{instance.assignment.lesson_id}/assignment-{instance.assignment_id}/{filename}"


class AssignmentAttachment(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=assignment_attachment_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def filename(self):
        return self.file.name.rsplit("/", 1)[-1]

    def __str__(self):
        return self.filename()


# ---------------------------
# Signals
# ---------------------------
@receiver(post_save, sender=Lesson)
def drop_self_when_archived(sender, instance: Lesson, **kwargs):
    if instance.status == "archived":
        for l in Lesson.objects.filter(prerequisites=instance):
            l.prerequisites.remove(instance)


# ---------------------------
# Enrollments and Progress Tracking
# ---------------------------
class LessonEnrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="lesson_enrollments")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "lesson")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.full_name()} → {self.lesson.unit_code}"


class ReadingListProgress(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="reading_progress")
    reading = models.ForeignKey("ReadingList", on_delete=models.CASCADE, related_name="progress")
    done = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "reading")
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["reading"]),
        ]

    def __str__(self):
        return f"{self.student.full_name()} • {self.reading.title} → {'done' if self.done else 'todo'}"


class VideoProgress(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="video_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="video_progress")
    watched = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "lesson")
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["lesson"]),
        ]

    def __str__(self):
        return f"{self.student.full_name()} • {self.lesson.unit_code} video → {'watched' if self.watched else 'not watched'}"

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(
        "lesson_management.Assignment",
        on_delete=models.CASCADE,
        related_name="submissions"
    )
    student = models.ForeignKey(
        "student_management.Student",
        on_delete=models.CASCADE,
        related_name="assignment_submissions"
    )
    pdf = models.FileField(upload_to="submissions/%Y/%m/%d/")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.assignment_id} · {self.student_id}"

    @property
    def filename(self):
        return getattr(self.pdf, "name", "").split("/")[-1]


class LessonCreditAwarded(models.Model):
    """Track which lessons have awarded credits to which students (to prevent double-awarding)."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="lesson_credits_awarded")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="credits_awarded")
    credits_amount = models.PositiveSmallIntegerField()
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "lesson")
        ordering = ["-awarded_at"]
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["lesson"]),
        ]

    def __str__(self):
        return f"{self.student.full_name()} • {self.lesson.unit_code} • {self.credits_amount} credits"