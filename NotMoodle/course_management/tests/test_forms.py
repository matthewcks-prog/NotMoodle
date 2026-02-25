# course_management/tests/test_forms.py
"""
Tests for course_management forms
"""
import pytest
from course_management.forms import CourseForm
from course_management.models import Course


@pytest.mark.django_db
class TestCourseForm:
    """Test CourseForm validation"""
    
    def test_valid_course_form(self):
        """Test that valid data creates a valid form"""
        form_data = {
            'code': 'TEST001',
            'name': 'Test Course',
            'description': 'Test Description',
            'total_credits_required': 30,
            'status': 'published'
        }
        form = CourseForm(data=form_data)
        assert form.is_valid()
    
    def test_course_form_requires_code(self):
        """Test that course code is required"""
        form_data = {
            'name': 'Test Course',
            'total_credits_required': 30,
        }
        form = CourseForm(data=form_data)
        assert not form.is_valid()
        assert 'code' in form.errors
    
    def test_course_form_requires_name(self):
        """Test that course name is required"""
        form_data = {
            'code': 'TEST001',
            'total_credits_required': 30,
        }
        form = CourseForm(data=form_data)
        assert not form.is_valid()
        assert 'name' in form.errors
    
    def test_course_form_positive_credits(self):
        """Test that credits must be positive"""
        form_data = {
            'code': 'TEST001',
            'name': 'Test Course',
            'total_credits_required': -10,
        }
        form = CourseForm(data=form_data)
        assert not form.is_valid()
        assert 'total_credits_required' in form.errors
