"""Tests for student_management models."""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from model_bakery import baker
from student_management.models import Student, ManageCreditPoint, EnrollmentSequence


@pytest.mark.django_db
class TestStudent:
    """Test Student model."""
    
    def test_create_student(self, user):
        """Test creating a student."""
        from datetime import date
        
        student = baker.make(
            Student,
            user=user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth=date(2000, 1, 1),
            enrollment_number=1001,
            status="active",
        )
        
        assert student.id is not None
        assert student.first_name == "John"
        assert student.last_name == "Doe"
        assert student.status == "active"
    
    def test_student_full_name(self, student):
        """Test full_name method."""
        full_name = student.full_name()
        
        assert student.first_name in full_name
        assert student.last_name in full_name
    
    def test_student_str(self, student):
        """Test __str__ method."""
        str_repr = str(student)
        
        assert str(student.enrollment_number) in str_repr
        assert student.first_name in str_repr
        assert student.last_name in str_repr
    
    def test_student_unique_email(self):
        """Test unique constraint on email."""
        baker.make(Student, email="test@example.com", enrollment_number=2001)
        
        with pytest.raises(IntegrityError):
            Student.objects.create(
                first_name="Jane",
                last_name="Doe",
                email="test@example.com",
                date_of_birth="2000-01-01",
                enrollment_number=2002,
            )
    
    def test_student_enrollment_number_generation(self):
        """Test automatic enrollment number generation."""
        from datetime import date
        
        student = Student.objects.create(
            first_name="Test",
            last_name="Student",
            email="auto@example.com",
            date_of_birth=date(2000, 1, 1),
        )
        
        assert student.enrollment_number is not None
        assert student.enrollment_number > 0
    
    def test_student_gpa_validation(self):
        """Test GPA validation (0.0 to 4.0)."""
        student = Student(
            first_name="Test",
            last_name="Student",
            email="gpa@example.com",
            date_of_birth="2000-01-01",
            enrollment_number=3001,
            gpa=Decimal("5.0"),  # Invalid
        )
        
        with pytest.raises(ValidationError):
            student.full_clean()
    
    def test_student_status_choices(self, student):
        """Test status choices."""
        assert student.status in ["active", "reactive", "dropout"]


@pytest.mark.django_db
class TestManageCreditPoint:
    """Test ManageCreditPoint model."""
    
    def test_create_credit_point(self, student):
        """Test creating a credit point record."""
        credit = ManageCreditPoint.objects.get_or_create(student=student)[0]
        
        assert credit.id is not None
        assert credit.student == student
        assert credit.credits >= 0
    
    def test_credit_str(self, student):
        """Test __str__ method."""
        credit = ManageCreditPoint.objects.get_or_create(student=student)[0]
        credit.credits = 12
        credit.save()
        
        str_repr = str(credit)
        assert str(student.enrollment_number) in str_repr
        assert "12" in str_repr
    
    def test_credit_increase(self, student):
        """Test increase method (atomic)."""
        credit = ManageCreditPoint.objects.get_or_create(student=student)[0]
        credit.credits = 0
        credit.save()
        
        credit.increase(6)
        
        assert credit.credits == 6
        
        credit.increase(6)
        
        assert credit.credits == 12
    
    def test_credit_decrease(self, student):
        """Test decrease method (atomic)."""
        credit = ManageCreditPoint.objects.get_or_create(student=student)[0]
        credit.credits = 12
        credit.save()
        
        credit.decrease(6)
        
        assert credit.credits == 6
    
    def test_credit_decrease_clamp_at_zero(self, student):
        """Test decrease clamps at 0 (no negatives)."""
        credit = ManageCreditPoint.objects.get_or_create(student=student)[0]
        credit.credits = 3
        credit.save()
        
        credit.decrease(10)  # Try to go negative
        
        assert credit.credits == 0
    
    def test_credit_one_to_one_constraint(self, student):
        """Test one-to-one relationship with student."""
        credit1 = ManageCreditPoint.objects.get_or_create(student=student)[0]
        
        with pytest.raises(IntegrityError):
            ManageCreditPoint.objects.create(student=student, credits=100)


@pytest.mark.django_db
class TestEnrollmentSequence:
    """Test EnrollmentSequence model."""
    
    def test_create_sequence(self):
        """Test creating a sequence entry."""
        seq = EnrollmentSequence.objects.create()
        
        assert seq.id is not None
        assert seq.id > 0
    
    def test_sequence_increment(self):
        """Test sequence increments."""
        seq1 = EnrollmentSequence.objects.create()
        seq2 = EnrollmentSequence.objects.create()
        seq3 = EnrollmentSequence.objects.create()
        
        assert seq2.id > seq1.id
        assert seq3.id > seq2.id

