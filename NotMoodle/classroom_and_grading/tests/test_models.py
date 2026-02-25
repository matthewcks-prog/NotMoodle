"""
Tests for classroom_and_grading app models.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from model_bakery import baker
from classroom_and_grading.models import Classroom, ClassroomStudent, AssignmentGrade
from lesson_management.models import Assignment


@pytest.mark.django_db
class TestClassroom:
    """Test Classroom model."""
    
    def test_create_classroom(self, course, lesson, teacher):
        """Test creating a classroom."""
        start = timezone.now()
        end = start + timedelta(days=30)
        
        classroom = baker.make(
            Classroom,
            course=course,
            lesson=lesson,
            teacher=teacher,
            start_date=start,
            end_date=end,
        )
        
        assert classroom.id is not None
        assert classroom.course == course
        assert classroom.lesson == lesson
        assert classroom.teacher == teacher
        assert classroom.start_date == start
        assert classroom.end_date == end
    
    def test_classroom_str(self, classroom):
        """Test __str__ method."""
        str_repr = str(classroom)
        
        assert str(classroom.course) in str_repr
        assert str(classroom.lesson) in str_repr
    
    def test_classroom_duration_property(self):
        """Test duration property calculation."""
        start = timezone.now()
        end = start + timedelta(days=7)
        
        classroom = baker.make(
            Classroom,
            start_date=start,
            end_date=end,
        )
        
        duration = classroom.duration
        assert duration == timedelta(days=7)
    
    def test_classroom_duration_none(self):
        """Test duration when dates are missing."""
        classroom = baker.make(
            Classroom,
            start_date=None,
            end_date=None,
        )
        
        assert classroom.duration is None
    
    def test_classroom_unique_constraint(self, course, lesson, teacher):
        """Test unique constraint per teacher."""
        start = timezone.now()
        end = start + timedelta(days=30)
        
        # Create first classroom
        classroom1 = baker.make(
            Classroom,
            course=course,
            lesson=lesson,
            teacher=teacher,
            start_date=start,
            end_date=end,
        )
        
        # Try to create duplicate
        with pytest.raises(IntegrityError):
            Classroom.objects.create(
                course=course,
                lesson=lesson,
                teacher=teacher,
                start_date=start,
                end_date=end,
            )
    
    def test_classroom_ordering(self, course, lesson, teacher):
        """Test default ordering by start_date descending."""
        from freezegun import freeze_time
        
        with freeze_time("2025-01-01"):
            c1 = baker.make(Classroom, course=course, lesson=lesson, teacher=teacher, start_date=timezone.now())
        
        with freeze_time("2025-01-15"):
            c2 = baker.make(Classroom, course=course, lesson=lesson, teacher=teacher, start_date=timezone.now())
        
        classrooms = list(Classroom.objects.all()[:2])
        
        # Newest first
        assert classrooms[0] == c2
        assert classrooms[1] == c1


@pytest.mark.django_db
class TestClassroomStudent:
    """Test ClassroomStudent model."""
    
    def test_create_classroom_student(self, classroom, student):
        """Test adding student to classroom roster."""
        cs = baker.make(
            ClassroomStudent,
            classroom=classroom,
            student=student,
        )
        
        assert cs.id is not None
        assert cs.classroom == classroom
        assert cs.student == student
        assert cs.added_at is not None
    
    def test_classroom_student_str(self, classroom, student):
        """Test __str__ method."""
        cs = baker.make(
            ClassroomStudent,
            classroom=classroom,
            student=student,
        )
        
        str_repr = str(cs)
        assert str(cs.classroom_id) in str_repr
        assert str(cs.student_id) in str_repr
    
    def test_classroom_student_unique_together(self, classroom, student):
        """Test unique constraint for classroom-student pair."""
        # Create first enrollment
        baker.make(ClassroomStudent, classroom=classroom, student=student)
        
        # Try to create duplicate
        with pytest.raises(IntegrityError):
            ClassroomStudent.objects.create(
                classroom=classroom,
                student=student,
            )
    
    def test_classroom_student_cascade_delete(self, classroom, student):
        """Test cascade delete when classroom is deleted."""
        cs = baker.make(ClassroomStudent, classroom=classroom, student=student)
        cs_id = cs.id
        
        classroom.delete()
        
        assert not ClassroomStudent.objects.filter(id=cs_id).exists()


@pytest.mark.django_db
class TestAssignmentGrade:
    """Test AssignmentGrade model."""
    
    def test_create_assignment_grade(self, assignment, student, teacher):
        """Test creating an assignment grade."""
        grade = baker.make(
            AssignmentGrade,
            assignment=assignment,
            student=student,
            marks_awarded=Decimal("85.50"),
            feedback="Good work!",
            graded_by=teacher,
        )
        
        assert grade.id is not None
        assert grade.assignment == assignment
        assert grade.student == student
        assert grade.marks_awarded == Decimal("85.50")
        assert grade.feedback == "Good work!"
        assert grade.graded_by == teacher
    
    def test_assignment_grade_nullable_fields(self, assignment, student):
        """Test that marks and feedback can be null."""
        grade = baker.make(
            AssignmentGrade,
            assignment=assignment,
            student=student,
            marks_awarded=None,
            feedback="",
            graded_by=None,
        )
        
        assert grade.marks_awarded is None
        assert grade.feedback == ""
        assert grade.graded_by is None
    
    def test_assignment_grade_str(self, assignment, student, teacher):
        """Test __str__ method."""
        grade = baker.make(
            AssignmentGrade,
            assignment=assignment,
            student=student,
            marks_awarded=Decimal("90.00"),
            graded_by=teacher,
        )
        
        str_repr = str(grade)
        assert assignment.title in str_repr
        assert str(student.id) in str_repr
        assert "90.00" in str_repr
    
    def test_assignment_grade_unique_together(self, assignment, student):
        """Test unique constraint for assignment-student pair."""
        baker.make(
            AssignmentGrade,
            assignment=assignment,
            student=student,
            marks_awarded=Decimal("80.00"),
        )
        
        # Try to create duplicate
        with pytest.raises(IntegrityError):
            AssignmentGrade.objects.create(
                assignment=assignment,
                student=student,
                marks_awarded=Decimal("85.00"),
            )
    
    def test_assignment_grade_validation_negative(self, assignment, student):
        """Test that negative marks are not allowed."""
        with pytest.raises(ValidationError):
            grade = AssignmentGrade(
                assignment=assignment,
                student=student,
                marks_awarded=Decimal("-10.00"),
            )
            grade.full_clean()
    
    def test_assignment_grade_zero_marks(self, assignment, student):
        """Test that zero marks are allowed."""
        grade = baker.make(
            AssignmentGrade,
            assignment=assignment,
            student=student,
            marks_awarded=Decimal("0.00"),
        )
        
        assert grade.marks_awarded == Decimal("0.00")
    
    def test_assignment_grade_cascade_delete_assignment(self, assignment, student):
        """Test cascade delete when assignment is deleted."""
        grade = baker.make(
            AssignmentGrade,
            assignment=assignment,
            student=student,
            marks_awarded=Decimal("80.00"),
        )
        grade_id = grade.id
        
        assignment.delete()
        
        assert not AssignmentGrade.objects.filter(id=grade_id).exists()
    
    def test_assignment_grade_cascade_delete_student(self, assignment, student):
        """Test cascade delete when student is deleted."""
        grade = baker.make(
            AssignmentGrade,
            assignment=assignment,
            student=student,
            marks_awarded=Decimal("80.00"),
        )
        grade_id = grade.id
        
        student.delete()
        
        assert not AssignmentGrade.objects.filter(id=grade_id).exists()
    
    def test_assignment_grade_ordering(self, assignment, student):
        """Test default ordering by student_id."""
        from student_management.models import Student
        
        student1 = baker.make(Student, enrollment_number=1001)
        student2 = baker.make(Student, enrollment_number=1002)
        student3 = baker.make(Student, enrollment_number=1003)
        
        grade3 = baker.make(AssignmentGrade, assignment=assignment, student=student3)
        grade1 = baker.make(AssignmentGrade, assignment=assignment, student=student1)
        grade2 = baker.make(AssignmentGrade, assignment=assignment, student=student2)
        
        grades = list(AssignmentGrade.objects.filter(assignment=assignment))
        
        assert grades[0].student == student1
        assert grades[1].student == student2
        assert grades[2].student == student3

