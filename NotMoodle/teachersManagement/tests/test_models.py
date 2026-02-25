"""Tests for teachersManagement models."""
import pytest
from django.contrib.auth.models import User
from model_bakery import baker
from teachersManagement.models import TeacherProfile


@pytest.mark.django_db
class TestTeacherProfile:
    """Test TeacherProfile model."""
    
    def test_create_teacher_profile(self, teacher_user):
        """Test creating a teacher profile."""
        from datetime import date
        
        profile = baker.make(
            TeacherProfile,
            user=teacher_user,
            department="Computer Science",
            hire_date=date(2020, 1, 1),
            display_name="Dr. Smith",
            contact_email="smith@example.com",
        )
        
        assert profile.id is not None
        assert profile.user == teacher_user
        assert profile.department == "Computer Science"
        assert profile.display_name == "Dr. Smith"
    
    def test_teacher_profile_str_with_display_name(self, teacher):
        """Test __str__ method with display_name."""
        teacher.display_name = "Dr. John Smith"
        teacher.save()
        
        str_repr = str(teacher)
        assert str_repr == "Dr. John Smith"
    
    def test_teacher_profile_str_with_user_full_name(self, teacher_user):
        """Test __str__ method fallback to user's full name."""
        teacher_user.first_name = "John"
        teacher_user.last_name = "Smith"
        teacher_user.save()
        
        profile = baker.make(
            TeacherProfile,
            user=teacher_user,
            display_name="",  # Empty display name
        )
        
        str_repr = str(profile)
        assert "John Smith" in str_repr or teacher_user.username in str_repr
    
    def test_teacher_profile_str_fallback_username(self, teacher_user):
        """Test __str__ method fallback to username."""
        teacher_user.first_name = ""
        teacher_user.last_name = ""
        teacher_user.save()
        
        profile = baker.make(
            TeacherProfile,
            user=teacher_user,
            display_name="",
        )
        
        str_repr = str(profile)
        assert teacher_user.username in str_repr
    
    def test_teacher_get_full_name(self, teacher):
        """Test get_full_name method."""
        teacher.display_name = "Dr. Jane Doe"
        teacher.save()
        
        full_name = teacher.get_full_name()
        assert full_name == "Dr. Jane Doe"
    
    def test_teacher_get_email_contact_email(self, teacher):
        """Test get_email method with contact_email."""
        teacher.contact_email = "teacher@school.edu"
        teacher.save()
        
        email = teacher.get_email()
        assert email == "teacher@school.edu"
    
    def test_teacher_get_email_fallback(self, teacher):
        """Test get_email method fallback to user email."""
        teacher.contact_email = ""
        teacher.user.email = "fallback@example.com"
        teacher.user.save()
        teacher.save()
        
        email = teacher.get_email()
        assert email == "fallback@example.com"

