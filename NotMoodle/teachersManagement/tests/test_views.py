# teachersManagement/tests/test_views.py
"""
Tests for teachersManagement views
"""
import pytest
from django.urls import reverse
from teachersManagement.models import TeacherProfile
from student_management.models import Student
from course_management.models import Course, Enrollment, CourseLesson
from lesson_management.models import Lesson, Assignment, LessonEnrollment
from classroom_and_grading.models import AssignmentGrade


@pytest.mark.django_db
class TestTeacherDashboard:
    """Test teacher dashboard view"""
    
    def test_teacher_dashboard_accessible(self, client, teacher_user):
        """Test that teacher dashboard is accessible"""
        client.force_login(teacher_user)
        url = reverse('teachersManagement:teacher_home')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_teacher_dashboard_requires_authentication(self, client):
        """Test that teacher dashboard requires authentication"""
        url = reverse('teachersManagement:teacher_home')
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login
    
    def test_teacher_dashboard_shows_lessons(self, client, teacher_user, teacher, lesson):
        """Test that teacher dashboard shows their lessons"""
        client.force_login(teacher_user)
        lesson.lesson_designer = teacher
        lesson.save()
        
        url = reverse('teachersManagement:teacher_home')
        response = client.get(url)
        
        # Dashboard should show the lesson
        assert lesson.title in str(response.content)


@pytest.mark.django_db
class TestStudentReportGeneration:
    """Test PDF report generation for students"""
    
    def test_teacher_can_generate_student_report(self, client, teacher_user, student, course, teacher):
        """Test that teachers can generate PDF reports for students"""
        client.force_login(teacher_user)
        
        # Enroll student in course
        Enrollment.objects.create(student=student, course=course, enrolled_by='teacher')
        
        # Create lesson with passing grade
        lesson = Lesson.objects.create(
            unit_code='RPT101',
            title='Report Test Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        CourseLesson.objects.create(course=course, lesson=lesson, is_required=True)
        LessonEnrollment.objects.create(student=student, lesson=lesson)
        
        assignment = Assignment.objects.create(
            lesson=lesson,
            title='Test Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment,
            student=student,
            marks_awarded=75,
            graded_by=teacher_user
        )
        
        # Generate report
        url = reverse('teachersManagement:generate_student_report')
        response = client.post(url, {
            'student_id': student.id,
            'course_id': course.id,
            'total_credits_required': course.total_credits_required
        })
        
        # Should return PDF
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'


@pytest.mark.django_db
class TestTeacherLessonManagement:
    """Test teacher lesson creation and management"""
    
    def test_teacher_can_create_lesson(self, client, teacher_user):
        """Test that teachers can create lessons"""
        client.force_login(teacher_user)
        url = reverse('teachersManagement:lessons:create')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_teacher_can_view_lesson_list(self, client, teacher_user):
        """Test that teachers can view their lessons"""
        client.force_login(teacher_user)
        url = reverse('teachersManagement:lessons:list')
        response = client.get(url)
        assert response.status_code == 200
