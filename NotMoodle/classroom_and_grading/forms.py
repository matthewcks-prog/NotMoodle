# classrooms/forms.py
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Classroom, ClassroomStudent, Assignment
from student_management.models import Student
from lesson_management.forms import AssignmentForm, AttachmentForm

class DateInput(forms.DateInput):
    input_type = "date"

class ClassroomCreateForm(forms.ModelForm):
    # Force pure date pickers even though model has DateTimeField
    start_date = forms.DateField(widget=DateInput)
    end_date   = forms.DateField(widget=DateInput)

    class Meta:
        model = Classroom
        fields = ["course", "lesson", "start_date", "end_date"]
        widgets = {
            "course": forms.Select(attrs={"class": "form-control"}),
            "lesson": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before start date.'
                })
        
        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)

        # Convert dates to timezone-aware datetimes at 00:00
        sd = self.cleaned_data["start_date"]
        ed = self.cleaned_data["end_date"]
        obj.start_date = timezone.make_aware(timezone.datetime(sd.year, sd.month, sd.day, 0, 0, 0))
        obj.end_date   = timezone.make_aware(timezone.datetime(ed.year, ed.month, ed.day, 0, 0, 0))

        if commit:
            obj.save()
        return obj


class ClassroomAddStudentsForm(forms.Form):
    """Used on the detail page to add students to the roster."""
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),  # set in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"size": 10, "class": "form-control"})
    )

    def __init__(self, classroom, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classroom = classroom
        # Policy: A student can be in at most ONE classroom for a given lesson.
        # So exclude students who are already rostered in ANY classroom for this lesson.
        from .models import ClassroomStudent
        lesson_rostered_ids = (
            ClassroomStudent.objects
            .filter(classroom__lesson_id=classroom.lesson_id)
            .values_list("student_id", flat=True)
        )
        self.fields["students"].queryset = (
            Student.objects
            .exclude(id__in=lesson_rostered_ids)
            .order_by("last_name", "first_name")
        )

    def save(self):
        """Add selected students to this classroom respecting the one-classroom-per-lesson rule.

        Returns a dict: {"added": int, "skipped": int, "skipped_ids": [int, ...]}
        """
        from .models import AssignmentGrade, ClassroomStudent
        from lesson_management.models import LessonEnrollment, Assignment

        selected = list(self.cleaned_data.get("students", []))
        if not selected:
            return {"added": 0, "skipped": 0, "skipped_ids": []}

        # Guard on the server too: skip any student already rostered in ANY classroom for this lesson
        already_in_lesson_ids = set(
            ClassroomStudent.objects
            .filter(classroom__lesson_id=self.classroom.lesson_id)
            .values_list("student_id", flat=True)
        )
        allowed_students = [s for s in selected if s.id not in already_in_lesson_ids]
        skipped_ids = [s.id for s in selected if s.id in already_in_lesson_ids]

        # Create roster rows for allowed students
        roster_rows = [
            ClassroomStudent(classroom=self.classroom, student=s)
            for s in allowed_students
        ]
        ClassroomStudent.objects.bulk_create(roster_rows, ignore_conflicts=True)

        # Ensure they are enrolled in the lesson (unique per (student, lesson))
        if self.classroom.lesson_id and allowed_students:
            enroll_rows = [
                LessonEnrollment(student=s, lesson_id=self.classroom.lesson_id)
                for s in allowed_students
            ]
            LessonEnrollment.objects.bulk_create(enroll_rows, ignore_conflicts=True)

            # Create AssignmentGrade placeholders for all existing assignments in the lesson
            assignments = list(Assignment.objects.filter(lesson_id=self.classroom.lesson_id))
            if assignments:
                grade_placeholders = [
                    AssignmentGrade(assignment=assignment, student=student)
                    for assignment in assignments
                    for student in allowed_students
                ]
                AssignmentGrade.objects.bulk_create(grade_placeholders, ignore_conflicts=True)

        return {"added": len(roster_rows), "skipped": len(skipped_ids), "skipped_ids": skipped_ids}

class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"
    def format_value(self, value):
        if not value:
            return None
        # Render as "YYYY-MM-DDTHH:MM"
        return value.strftime("%Y-%m-%dT%H:%M")

