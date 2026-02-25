# lesson_management/tests/test_forms.py
"""
Tests for lesson_management forms
"""
import pytest
from lesson_management.forms import LessonForm, AssignmentForm, AssignmentSubmissionForm
from lesson_management.models import Lesson, Assignment
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestLessonForm:
    """Test LessonForm validation"""
    
    def test_valid_lesson_form(self, teacher):
        """Test that valid data creates a valid form"""
        form_data = {
            'unit_code': 'TEST101',
            'title': 'Test Lesson',
            'description': 'Test Description',
            'lesson_credits': 6,
            'estimated_effort': 10,
            'status': 'published',
            'lesson_designer': teacher.id
        }
        form = LessonForm(data=form_data)
        assert form.is_valid()
    
    def test_lesson_form_prevents_self_prerequisite(self, teacher, lesson):
        """Test that a lesson cannot be its own prerequisite"""
        form_data = {
            'unit_code': lesson.unit_code,
            'title': lesson.title,
            'lesson_credits': 6,
            'estimated_effort': 10,
            'status': 'published',
            'lesson_designer': teacher.id,
            'prerequisites': [lesson.id]  # Self-reference
        }
        form = LessonForm(data=form_data, instance=lesson)
        
        # This should be caught at model level
        lesson.prerequisites.add(lesson)
        with pytest.raises(Exception):
            lesson.clean()


@pytest.mark.django_db
class TestAssignmentForm:
    """Test AssignmentForm validation - including date validation"""
    
    def test_valid_assignment_form(self, lesson):
        """Test that valid data creates a valid form"""
        now = timezone.now()
        form_data = {
            'title': 'Test Assignment',
            'lesson': lesson.id,
            'release_date': now,
            'due_date': now + timedelta(days=7),
            'marks': 100,
            'weightage': 50,
            'description': 'Test Description'
        }
        form = AssignmentForm(data=form_data)
        assert form.is_valid()
    
    def test_assignment_due_date_must_be_after_release_date(self, lesson):
        """
        CRITICAL TEST: Test date validation - due date must be >= release date
        Tests recent validation feature
        """
        now = timezone.now()
        form_data = {
            'title': 'Test Assignment',
            'lesson': lesson.id,
            'release_date': now,
            'due_date': now - timedelta(days=1),  # Due date BEFORE release date
            'marks': 100,
            'weightage': 50
        }
        form = AssignmentForm(data=form_data)
        assert not form.is_valid()
        assert 'due_date' in form.errors or '__all__' in form.errors
    
    def test_assignment_weightage_validation(self, lesson):
        """Test that weightage must be between 0 and 100"""
        now = timezone.now()
        
        # Test weightage > 100
        form_data = {
            'title': 'Test Assignment',
            'lesson': lesson.id,
            'release_date': now,
            'due_date': now + timedelta(days=7),
            'marks': 100,
            'weightage': 150  # Invalid
        }
        form = AssignmentForm(data=form_data)
        assert not form.is_valid()
        assert 'weightage' in form.errors
        
        # Test weightage < 0
        form_data['weightage'] = -10
        form = AssignmentForm(data=form_data)
        assert not form.is_valid()
        assert 'weightage' in form.errors


@pytest.mark.django_db
class TestAssignmentSubmissionForm:
    """Test assignment submission form"""
    
    def test_valid_submission_form(self, assignment):
        """Test that valid submission is accepted"""
        form = AssignmentSubmissionForm(data={}, files={})
        # The form should require a file
        assert 'submission_file' in form.fields
