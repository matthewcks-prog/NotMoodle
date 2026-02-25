"""
Comprehensive admin interface tests for all NotMoodle apps.
"""
import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from model_bakery import baker


@pytest.mark.django_db
class TestAdminRegistration:
    """Test that all models are registered in admin."""
    
    def test_assist_models_registered(self):
        """Test assist app models are registered."""
        from assist.models import DocumentChunk, StudentQuestion
        
        assert DocumentChunk in admin.site._registry
        assert StudentQuestion in admin.site._registry
    
    def test_classroom_models_registered(self):
        """Test classroom_and_grading models are registered."""
        from classroom_and_grading.models import Classroom, ClassroomStudent, AssignmentGrade
        
        assert Classroom in admin.site._registry
        assert ClassroomStudent in admin.site._registry
        assert AssignmentGrade in admin.site._registry
    
    def test_course_models_registered(self):
        """Test course_management models are registered."""
        from course_management.models import Course, Enrollment, CourseLesson
        
        assert Course in admin.site._registry
        assert Enrollment in admin.site._registry
        assert CourseLesson in admin.site._registry
    
    def test_lesson_models_registered(self):
        """Test lesson_management models are registered."""
        from lesson_management.models import (
            Lesson, ReadingList, Assignment, AssignmentAttachment,
            LessonEnrollment, ReadingListProgress, VideoProgress, AssignmentSubmission
        )
        
        assert Lesson in admin.site._registry
        assert ReadingList in admin.site._registry
        assert Assignment in admin.site._registry
        assert LessonEnrollment in admin.site._registry
    
    def test_student_models_registered(self):
        """Test student_management models are registered."""
        from student_management.models import Student, ManageCreditPoint
        
        assert Student in admin.site._registry
        assert ManageCreditPoint in admin.site._registry
    
    def test_teacher_models_registered(self):
        """Test teachersManagement models are registered."""
        from teachersManagement.models import TeacherProfile
        
        assert TeacherProfile in admin.site._registry
    
    def test_welcome_models_registered(self):
        """Test welcome_page models are registered."""
        from welcome_page.models import ContactMessage
        
        assert ContactMessage in admin.site._registry


@pytest.mark.django_db
class TestAdminViews:
    """Test admin views are accessible."""
    
    def test_admin_login_page(self, client):
        """Test admin login page loads."""
        response = client.get("/admin/")
        assert response.status_code == 302  # Redirect to login
    
    def test_admin_index_authenticated(self, client, superuser):
        """Test admin index with authenticated superuser."""
        client.force_login(superuser)
        response = client.get("/admin/")
        assert response.status_code == 200
    
    def test_admin_course_list(self, client, superuser):
        """Test course admin list view."""
        client.force_login(superuser)
        response = client.get("/admin/course_management/course/")
        assert response.status_code == 200
    
    def test_admin_student_list(self, client, superuser):
        """Test student admin list view."""
        client.force_login(superuser)
        response = client.get("/admin/student_management/student/")
        assert response.status_code == 200
    
    def test_admin_lesson_list(self, client, superuser):
        """Test lesson admin list view."""
        client.force_login(superuser)
        response = client.get("/admin/lesson_management/lesson/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminActions:
    """Test admin CRUD operations."""
    
    def test_admin_create_course(self, client, superuser, teacher):
        """Test creating a course via admin."""
        client.force_login(superuser)
        
        data = {
            "code": "TEST101",
            "name": "Test Course",
            "description": "Test description",
            "status": "active",
            "total_credits_required": 144,
            "director": teacher.id,
        }
        
        response = client.post("/admin/course_management/course/add/", data=data)
        
        # Check redirect or success
        assert response.status_code in [200, 302]
    
    def test_admin_edit_student(self, client, superuser, student):
        """Test editing a student via admin."""
        client.force_login(superuser)
        
        response = client.get(f"/admin/student_management/student/{student.id}/change/")
        assert response.status_code == 200
    
    def test_admin_search_courses(self, client, superuser, course):
        """Test searching courses in admin."""
        client.force_login(superuser)
        
        response = client.get("/admin/course_management/course/?q=CS")
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminPermissions:
    """Test admin permissions."""
    
    def test_admin_requires_staff(self, client, user):
        """Test that regular users can't access admin."""
        client.force_login(user)
        response = client.get("/admin/")
        assert response.status_code == 302  # Redirect
    
    def test_admin_requires_superuser_for_users(self, client, staff_user):
        """Test that staff (non-superuser) can't manage users."""
        client.force_login(staff_user)
        response = client.get("/admin/auth/user/")
        # May be 403 or redirect depending on permissions
        assert response.status_code in [302, 403]

