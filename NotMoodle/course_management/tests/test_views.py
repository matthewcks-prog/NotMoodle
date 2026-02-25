# course_management/tests/test_views.py
"""
Tests for course_management views
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from course_management.models import Course, Enrollment, CourseLesson
from lesson_management.models import Lesson, Assignment, LessonEnrollment
from classroom_and_grading.models import AssignmentGrade
from student_management.models import Student, ManageCreditPoint
from teachersManagement.models import TeacherProfile


@pytest.mark.django_db
class TestCourseListView:
    """Test course listing view for students"""
    
    def test_course_list_view_accessible(self, client, student_user):
        """Test that course list view is accessible to authenticated students"""
        client.force_login(student_user)
        url = reverse('course_management:student_course_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'courses' in response.context
    
    def test_course_list_view_shows_published_courses(self, client, student_user, course):
        """Test that only published courses are shown"""
        client.force_login(student_user)
        course.status = 'published'
        course.save()
        
        url = reverse('course_management:student_course_list')
        response = client.get(url)
        
        assert course in response.context['courses']
    
    def test_course_list_view_requires_authentication(self, client):
        """Test that course list requires authentication"""
        url = reverse('course_management:student_course_list')
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
class TestCourseEnrollment:
    """Test course enrollment functionality"""
    
    def test_student_can_enroll_in_course(self, client, student_user, student, course):
        """Test that a student can enroll in a published course"""
        client.force_login(student_user)
        course.status = 'published'
        course.save()
        
        url = reverse('course_management:enroll_in_course', kwargs={'course_id': course.id})
        response = client.post(url)
        
        assert response.status_code == 302  # Redirect after enrollment
        assert Enrollment.objects.filter(student=student, course=course).exists()
    
    def test_student_cannot_enroll_twice(self, client, student_user, student, course):
        """Test that a student cannot enroll in the same course twice"""
        course.status = 'published'
        course.save()
        
        # First enrollment
        Enrollment.objects.create(student=student, course=course, enrolled_by='student')
        
        client.force_login(student_user)
        url = reverse('course_management:enroll_in_course', kwargs={'course_id': course.id})
        response = client.post(url)
        
        # Should still succeed but not create duplicate
        assert Enrollment.objects.filter(student=student, course=course).count() == 1


@pytest.mark.django_db
class TestGraduationEligibilityWithElectives:
    """
    Test the credit calculation fix - ensuring ALL passed lessons contribute credits,
    not just lessons that are part of the course
    """
    
    def test_elective_lessons_contribute_to_credits(self, student, course, teacher):
        """
        CRITICAL TEST: Verify that elective lessons (not part of course) contribute credits
        This tests the recent fix to check_graduation_eligibility()
        """
        # Enroll student in course
        Enrollment.objects.create(student=student, course=course, enrolled_by='student')
        
        # Create core lesson (part of course)
        core_lesson = Lesson.objects.create(
            unit_code='CORE101',
            title='Core Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=10,
            status='published'
        )
        CourseLesson.objects.create(course=course, lesson=core_lesson, is_required=True)
        
        # Create elective lesson (NOT part of course)
        elective_lesson = Lesson.objects.create(
            unit_code='ELEC101',
            title='Elective Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        # Note: elective_lesson is NOT added to CourseLesson
        
        # Enroll in both lessons
        LessonEnrollment.objects.create(student=student, lesson=core_lesson)
        LessonEnrollment.objects.create(student=student, lesson=elective_lesson)
        
        # Create assignments and grades for core lesson (passing)
        core_assignment = Assignment.objects.create(
            lesson=core_lesson,
            title='Core Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=core_assignment,
            student=student,
            marks_awarded=60,  # 60% - passing
            graded_by=teacher
        )
        
        # Create assignments and grades for elective lesson (passing)
        elective_assignment = Assignment.objects.create(
            lesson=elective_lesson,
            title='Elective Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=elective_assignment,
            student=student,
            marks_awarded=75,  # 75% - passing
            graded_by=teacher
        )
        
        # Check graduation eligibility
        is_eligible, total_credits, core_complete = course.check_graduation_eligibility(student)
        
        # CRITICAL ASSERTION: Total credits should include BOTH lessons
        assert total_credits == 12, f"Expected 12 credits (6 core + 6 elective), got {total_credits}"
        assert core_complete is True, "Core lesson should be marked as complete"
    
    def test_failed_elective_does_not_contribute_credits(self, student, course, teacher):
        """Test that failed elective lessons don't contribute credits"""
        Enrollment.objects.create(student=student, course=course, enrolled_by='student')
        
        # Create elective lesson (NOT part of course)
        elective_lesson = Lesson.objects.create(
            unit_code='ELEC102',
            title='Failed Elective',
            lesson_designer=teacher,
            lesson_credits=6,
            status='published'
        )
        
        LessonEnrollment.objects.create(student=student, lesson=elective_lesson)
        
        # Create assignment with failing grade
        assignment = Assignment.objects.create(
            lesson=elective_lesson,
            title='Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment,
            student=student,
            marks_awarded=40,  # 40% - failing
            graded_by=teacher
        )
        
        # Check graduation eligibility
        _, total_credits, _ = course.check_graduation_eligibility(student)
        
        # Should NOT count failed elective
        assert total_credits == 0, f"Failed elective should not contribute credits, got {total_credits}"
    
    def test_graduation_requires_core_lessons_and_enough_credits(self, student, course, teacher):
        """Test that graduation requires BOTH core completion AND enough credits"""
        course.total_credits_required = 12
        course.save()
        
        Enrollment.objects.create(student=student, course=course, enrolled_by='student')
        
        # Create core lesson
        core_lesson = Lesson.objects.create(
            unit_code='CORE201',
            title='Required Core',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        CourseLesson.objects.create(course=course, lesson=core_lesson, is_required=True)
        
        # Create elective lesson
        elective_lesson = Lesson.objects.create(
            unit_code='ELEC201',
            title='Extra Elective',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        # Pass ONLY the elective (not the core)
        LessonEnrollment.objects.create(student=student, lesson=elective_lesson)
        
        assignment = Assignment.objects.create(
            lesson=elective_lesson,
            title='Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment,
            student=student,
            marks_awarded=80,
            graded_by=teacher
        )
        
        # Check graduation eligibility
        is_eligible, total_credits, core_complete = course.check_graduation_eligibility(student)
        
        # Should have credits but not be eligible (missing core)
        assert total_credits == 6, "Should have 6 credits from elective"
        assert core_complete is False, "Core lessons not complete"
        assert is_eligible is False, "Should not be eligible without core lesson"


@pytest.mark.django_db
class TestCourseDetailView:
    """Test course detail view"""
    
    def test_course_detail_shows_lessons(self, client, student_user, course, lesson):
        """Test that course detail shows associated lessons"""
        client.force_login(student_user)
        CourseLesson.objects.create(course=course, lesson=lesson, is_required=True)
        
        url = reverse('course_management:course_detail', kwargs={'course_id': course.id})
        response = client.get(url)
        
        assert response.status_code == 200
        assert lesson in response.context['lessons']
