"""Tests for student_management pipeline (social auth)."""
import pytest
from django.contrib.auth.models import User
from model_bakery import baker
from student_management.pipeline import create_student_profile
from student_management.models import Student, ManageCreditPoint
from teachersManagement.models import TeacherProfile


@pytest.mark.django_db
class TestCreateStudentProfile:
    """Test create_student_profile pipeline function."""
    
    def test_create_student_profile_new_user(self):
        """Test creating student profile for new user."""
        user = baker.make(
            User,
            username="newstudent",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        
        details = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }
        
        # Call pipeline function
        result = create_student_profile(strategy=None, details=details, user=user)
        
        # Should create student profile
        assert Student.objects.filter(user=user).exists()
        student = Student.objects.get(user=user)
        assert student.first_name == "John"
        assert student.last_name == "Doe"
        assert student.email == "john@example.com"
        assert student.status == "active"
        
        # Should create credit record
        assert ManageCreditPoint.objects.filter(student=student).exists()
    
    def test_create_student_profile_existing_student(self):
        """Test with existing student profile (no duplicate)."""
        user = baker.make(User, username="existing")
        student = baker.make(Student, user=user, enrollment_number=5001)
        
        details = {"first_name": "Test", "last_name": "User", "email": "test@example.com"}
        
        # Call pipeline function
        create_student_profile(strategy=None, details=details, user=user)
        
        # Should not create duplicate
        assert Student.objects.filter(user=user).count() == 1
    
    def test_create_student_profile_teacher_user(self):
        """Test that teachers don't get student profiles."""
        teacher_user = baker.make(User, username="teacher")
        teacher_profile = baker.make(TeacherProfile, user=teacher_user)
        
        details = {"first_name": "Teacher", "last_name": "User", "email": "teacher@example.com"}
        
        # Call pipeline function
        create_student_profile(strategy=None, details=details, user=teacher_user)
        
        # Should NOT create student profile for teacher
        assert not Student.objects.filter(user=teacher_user).exists()
    
    def test_create_student_profile_no_user(self):
        """Test with no user (early return)."""
        details = {"first_name": "Test", "last_name": "User"}
        
        # Call with user=None
        result = create_student_profile(strategy=None, details=details, user=None)
        
        # Should return early without error
        assert result is None
    
    def test_create_student_profile_missing_details(self):
        """Test with missing details (uses defaults)."""
        user = baker.make(
            User,
            username="minimal",
            first_name="",
            last_name="",
            email="",
        )
        
        details = {}  # Empty details
        
        # Call pipeline function
        create_student_profile(strategy=None, details=details, user=user)
        
        # Should create student with defaults
        student = Student.objects.get(user=user)
        assert student.date_of_birth.year == 2000  # Default

