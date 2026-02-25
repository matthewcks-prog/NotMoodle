"""
Tests for classroom_and_grading app forms.
"""
import pytest
from django.utils import timezone
from datetime import date, timedelta
from model_bakery import baker
from classroom_and_grading.forms import ClassroomCreateForm, ClassroomAddStudentsForm
from classroom_and_grading.models import ClassroomStudent
from lesson_management.models import LessonEnrollment, Assignment
from student_management.models import Student


@pytest.mark.django_db
class TestClassroomCreateForm:
    """Test ClassroomCreateForm."""
    
    def test_form_valid_data(self, course, lesson):
        """Test form with valid data."""
        data = {
            "course": course.id,
            "lesson": lesson.id,
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        }
        
        form = ClassroomCreateForm(data=data)
        assert form.is_valid()
    
    def test_form_date_conversion(self, course, lesson):
        """Test that dates are converted to datetime."""
        data = {
            "course": course.id,
            "lesson": lesson.id,
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        }
        
        form = ClassroomCreateForm(data=data)
        assert form.is_valid()
        
        # Don't commit yet
        obj = form.save(commit=False)
        
        # Should have datetime objects
        assert obj.start_date.year == 2025
        assert obj.start_date.month == 1
        assert obj.start_date.day == 1
        assert obj.end_date.year == 2025
        assert obj.end_date.month == 1
        assert obj.end_date.day == 31
    
    def test_form_missing_fields(self):
        """Test form with missing required fields."""
        form = ClassroomCreateForm(data={})
        assert not form.is_valid()
        assert "course" in form.errors
        assert "lesson" in form.errors
        assert "start_date" in form.errors
        assert "end_date" in form.errors


@pytest.mark.django_db
class TestClassroomAddStudentsForm:
    """Test ClassroomAddStudentsForm."""
    
    def test_form_initialization(self, classroom):
        """Test form initializes with correct queryset."""
        form = ClassroomAddStudentsForm(classroom)
        
        # Should exclude students already in ANY classroom for this lesson
        assert form.fields["students"].queryset is not None
    
    def test_form_excludes_rostered_students(self, classroom, lesson):
        """Test form excludes students already in lesson classrooms."""
        # Create another classroom for same lesson
        other_classroom = baker.make(
            "classroom_and_grading.Classroom",
            lesson=lesson,
        )
        
        # Add student to other classroom
        student = baker.make(Student, enrollment_number=2001)
        baker.make(ClassroomStudent, classroom=other_classroom, student=student)
        
        # Form should exclude this student
        form = ClassroomAddStudentsForm(classroom)
        student_ids = list(form.fields["students"].queryset.values_list("id", flat=True))
        
        assert student.id not in student_ids
    
    def test_form_save_adds_students(self, classroom):
        """Test that save() adds students to classroom."""
        student1 = baker.make(Student, enrollment_number=3001)
        student2 = baker.make(Student, enrollment_number=3002)
        
        form = ClassroomAddStudentsForm(
            classroom,
            data={"students": [student1.id, student2.id]}
        )
        
        assert form.is_valid()
        result = form.save()
        
        assert result["added"] == 2
        assert result["skipped"] == 0
        assert ClassroomStudent.objects.filter(classroom=classroom, student=student1).exists()
        assert ClassroomStudent.objects.filter(classroom=classroom, student=student2).exists()
    
    def test_form_save_creates_lesson_enrollments(self, classroom):
        """Test that save() creates lesson enrollments."""
        student = baker.make(Student, enrollment_number=4001)
        
        form = ClassroomAddStudentsForm(
            classroom,
            data={"students": [student.id]}
        )
        
        assert form.is_valid()
        form.save()
        
        # Should create lesson enrollment
        assert LessonEnrollment.objects.filter(
            student=student,
            lesson=classroom.lesson
        ).exists()
    
    def test_form_save_creates_grade_placeholders(self, classroom, assignment):
        """Test that save() creates grade placeholders for existing assignments."""
        assignment.lesson = classroom.lesson
        assignment.save()
        
        student = baker.make(Student, enrollment_number=5001)
        
        form = ClassroomAddStudentsForm(
            classroom,
            data={"students": [student.id]}
        )
        
        assert form.is_valid()
        form.save()
        
        # Should create AssignmentGrade placeholder
        from classroom_and_grading.models import AssignmentGrade
        assert AssignmentGrade.objects.filter(
            assignment=assignment,
            student=student
        ).exists()
    
    def test_form_save_skips_already_rostered(self, classroom):
        """Test that save() skips students already rostered in ANY classroom for lesson."""
        # Create another classroom for same lesson
        other_classroom = baker.make(
            "classroom_and_grading.Classroom",
            lesson=classroom.lesson,
        )
        
        student1 = baker.make(Student, enrollment_number=6001)
        student2 = baker.make(Student, enrollment_number=6002)
        
        # Add student1 to other classroom first
        baker.make(ClassroomStudent, classroom=other_classroom, student=student1)
        
        # Try to add both to this classroom
        # Need to manually construct form data since queryset will exclude student1
        form = ClassroomAddStudentsForm(classroom)
        form.cleaned_data = {"students": [student1, student2]}
        
        result = form.save()
        
        # student1 should be skipped, student2 should be added
        assert result["added"] == 1
        assert result["skipped"] == 1
        assert student1.id in result["skipped_ids"]
        assert ClassroomStudent.objects.filter(classroom=classroom, student=student2).exists()
        assert not ClassroomStudent.objects.filter(classroom=classroom, student=student1).exists()
    
    def test_form_save_empty_selection(self, classroom):
        """Test save with no students selected."""
        form = ClassroomAddStudentsForm(classroom, data={"students": []})
        
        assert form.is_valid()
        result = form.save()
        
        assert result["added"] == 0
        assert result["skipped"] == 0

