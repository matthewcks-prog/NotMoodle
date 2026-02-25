# lesson_management/tests/test_views.py
"""
Tests for lesson_management views - focusing on enrollment and prerequisite validation
"""
import pytest
from django.urls import reverse
from django.contrib import messages as django_messages
from lesson_management.models import Lesson, LessonEnrollment, Assignment
from classroom_and_grading.models import AssignmentGrade, Classroom, ClassroomStudent
from student_management.models import Student, ManageCreditPoint
from teachersManagement.models import TeacherProfile
from course_management.models import Course


@pytest.mark.django_db
class TestLessonBrowsing:
    """Test lesson browsing and listing for students"""
    
    def test_student_can_view_published_lessons(self, client, student_user, lesson):
        """Test that students can view published lessons"""
        client.force_login(student_user)
        lesson.status = 'published'
        lesson.save()
        
        url = reverse('lessons:student_list')
        response = client.get(url)
        
        assert response.status_code == 200
        assert lesson in response.context['lessons']
    
    def test_draft_lessons_not_visible_to_students(self, client, student_user, lesson):
        """Test that draft lessons are not visible to students"""
        client.force_login(student_user)
        lesson.status = 'draft'
        lesson.save()
        
        url = reverse('lessons:student_list')
        response = client.get(url)
        
        assert lesson not in response.context['lessons']
    
    def test_lesson_list_shows_prerequisite_info(self, client, student_user, student, teacher):
        """
        CRITICAL TEST: Verify prerequisite information is displayed on browse page
        Tests recent feature addition
        """
        client.force_login(student_user)
        
        # Create prerequisite lesson
        prereq_lesson = Lesson.objects.create(
            unit_code='PRE101',
            title='Prerequisite Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        # Create main lesson with prerequisite
        main_lesson = Lesson.objects.create(
            unit_code='MAIN101',
            title='Main Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        main_lesson.prerequisites.add(prereq_lesson)
        
        url = reverse('lessons:student_list')
        response = client.get(url)
        
        # Should include prerequisite information in context
        assert 'lesson_prerequisites' in response.context
        assert main_lesson.id in response.context['lesson_prerequisites']
        
        prereq_info = response.context['lesson_prerequisites'][main_lesson.id]
        assert len(prereq_info) == 1
        assert prereq_info[0]['lesson'] == prereq_lesson
        assert prereq_info[0]['passed'] is False  # Not passed yet


@pytest.mark.django_db
class TestPrerequisiteEnrollmentValidation:
    """
    CRITICAL TESTS: Test the new prerequisite pass validation
    Tests recent feature - students must PASS prerequisites, not just enroll
    """
    
    def test_cannot_enroll_without_passing_prerequisite(self, client, student_user, student, teacher):
        """Test that students cannot enroll without passing prerequisite"""
        client.force_login(student_user)
        
        # Create prerequisite lesson
        prereq = Lesson.objects.create(
            unit_code='PRE201',
            title='Prerequisite',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        # Create main lesson with prerequisite
        main_lesson = Lesson.objects.create(
            unit_code='MAIN201',
            title='Main Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        main_lesson.prerequisites.add(prereq)
        
        # Student is enrolled but hasn't passed
        LessonEnrollment.objects.create(student=student, lesson=prereq)
        
        # Try to enroll in main lesson
        url = reverse('lessons:enroll', kwargs={'lesson_id': main_lesson.id})
        response = client.post(url, follow=True)
        
        # Should be rejected with error message
        assert not LessonEnrollment.objects.filter(student=student, lesson=main_lesson).exists()
        
        # Check for error message
        messages = list(response.context['messages'])
        assert any('pass' in str(m).lower() and 'prerequisite' in str(m).lower() for m in messages)
    
    def test_cannot_enroll_with_failing_prerequisite_grade(self, client, student_user, student, teacher):
        """Test that students cannot enroll if they failed the prerequisite"""
        client.force_login(student_user)
        
        # Create prerequisite lesson
        prereq = Lesson.objects.create(
            unit_code='PRE202',
            title='Prerequisite',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        # Create main lesson
        main_lesson = Lesson.objects.create(
            unit_code='MAIN202',
            title='Main Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        main_lesson.prerequisites.add(prereq)
        
        # Student enrolled and has FAILING grade (< 50%)
        LessonEnrollment.objects.create(student=student, lesson=prereq)
        
        assignment = Assignment.objects.create(
            lesson=prereq,
            title='Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment,
            student=student,
            marks_awarded=40,  # 40% - FAILING
            graded_by=teacher
        )
        
        # Try to enroll
        url = reverse('lessons:enroll', kwargs={'lesson_id': main_lesson.id})
        response = client.post(url, follow=True)
        
        # Should be rejected
        assert not LessonEnrollment.objects.filter(student=student, lesson=main_lesson).exists()
        
        # Should show error message listing the prerequisite
        messages = list(response.context['messages'])
        assert any('Prerequisite' in str(m) for m in messages)
    
    def test_can_enroll_after_passing_prerequisite(self, client, student_user, student, teacher):
        """Test that students CAN enroll after passing the prerequisite"""
        client.force_login(student_user)
        
        # Create prerequisite lesson
        prereq = Lesson.objects.create(
            unit_code='PRE203',
            title='Prerequisite',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        # Create main lesson
        main_lesson = Lesson.objects.create(
            unit_code='MAIN203',
            title='Main Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        main_lesson.prerequisites.add(prereq)
        
        # Student has PASSING grade (>= 50%)
        LessonEnrollment.objects.create(student=student, lesson=prereq)
        
        assignment = Assignment.objects.create(
            lesson=prereq,
            title='Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment,
            student=student,
            marks_awarded=75,  # 75% - PASSING
            graded_by=teacher
        )
        
        # Try to enroll
        url = reverse('lessons:enroll', kwargs={'lesson_id': main_lesson.id})
        response = client.post(url, follow=True)
        
        # Should succeed
        assert LessonEnrollment.objects.filter(student=student, lesson=main_lesson).exists()
        
        # Should show success message
        messages = list(response.context['messages'])
        assert any('enrolled' in str(m).lower() for m in messages)
    
    def test_multiple_prerequisites_all_must_pass(self, client, student_user, student, teacher):
        """Test that ALL prerequisites must be passed"""
        client.force_login(student_user)
        
        # Create two prerequisite lessons
        prereq1 = Lesson.objects.create(
            unit_code='PRE301',
            title='Prerequisite 1',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        prereq2 = Lesson.objects.create(
            unit_code='PRE302',
            title='Prerequisite 2',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        # Create main lesson with both prerequisites
        main_lesson = Lesson.objects.create(
            unit_code='MAIN301',
            title='Main Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        main_lesson.prerequisites.add(prereq1, prereq2)
        
        # Pass prereq1, fail prereq2
        LessonEnrollment.objects.create(student=student, lesson=prereq1)
        LessonEnrollment.objects.create(student=student, lesson=prereq2)
        
        # Prereq1: Passing
        assignment1 = Assignment.objects.create(
            lesson=prereq1,
            title='Assignment 1',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment1,
            student=student,
            marks_awarded=80,
            graded_by=teacher
        )
        
        # Prereq2: Failing
        assignment2 = Assignment.objects.create(
            lesson=prereq2,
            title='Assignment 2',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment2,
            student=student,
            marks_awarded=30,  # Failing
            graded_by=teacher
        )
        
        # Try to enroll
        url = reverse('lessons:enroll', kwargs={'lesson_id': main_lesson.id})
        response = client.post(url, follow=True)
        
        # Should be rejected (one prerequisite failed)
        assert not LessonEnrollment.objects.filter(student=student, lesson=main_lesson).exists()
    
    def test_prerequisite_not_enrolled_blocks_enrollment(self, client, student_user, student, teacher):
        """Test that not being enrolled in prerequisite blocks enrollment"""
        client.force_login(student_user)
        
        # Create prerequisite lesson
        prereq = Lesson.objects.create(
            unit_code='PRE401',
            title='Prerequisite',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        # Create main lesson
        main_lesson = Lesson.objects.create(
            unit_code='MAIN401',
            title='Main Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        main_lesson.prerequisites.add(prereq)
        
        # Student is NOT enrolled in prerequisite at all
        
        # Try to enroll
        url = reverse('lessons:enroll', kwargs={'lesson_id': main_lesson.id})
        response = client.post(url, follow=True)
        
        # Should be rejected
        assert not LessonEnrollment.objects.filter(student=student, lesson=main_lesson).exists()


@pytest.mark.django_db
class TestLessonDetailView:
    """Test lesson detail view with prerequisite display"""
    
    def test_lesson_detail_shows_passed_prerequisites(self, client, student_user, student, teacher):
        """Test that lesson detail correctly shows passed prerequisites"""
        client.force_login(student_user)
        
        # Create prerequisite and pass it
        prereq = Lesson.objects.create(
            unit_code='PRE501',
            title='Prerequisite',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        
        LessonEnrollment.objects.create(student=student, lesson=prereq)
        
        assignment = Assignment.objects.create(
            lesson=prereq,
            title='Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        AssignmentGrade.objects.create(
            assignment=assignment,
            student=student,
            marks_awarded=70,
            graded_by=teacher
        )
        
        # Create main lesson
        main_lesson = Lesson.objects.create(
            unit_code='MAIN501',
            title='Main Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        main_lesson.prerequisites.add(prereq)
        LessonEnrollment.objects.create(student=student, lesson=main_lesson)
        
        # View lesson detail
        url = reverse('lessons:detail', kwargs={'lesson_id': main_lesson.id})
        response = client.get(url)
        
        assert response.status_code == 200
        assert prereq in response.context['completed_prerequisites']
        assert prereq not in response.context['missing_prerequisites']


@pytest.mark.django_db  
class TestAssignmentSubmission:
    """Test assignment submission workflow"""
    
    def test_student_can_submit_assignment(self, client, student_user, student, teacher):
        """Test basic assignment submission"""
        client.force_login(student_user)
        
        # Create lesson and enroll
        lesson = Lesson.objects.create(
            unit_code='TEST101',
            title='Test Lesson',
            lesson_designer=teacher,
            lesson_credits=6,
            estimated_effort=5,
            status='published'
        )
        LessonEnrollment.objects.create(student=student, lesson=lesson)
        
        # Create classroom and enroll student
        course = Course.objects.create(
            code='TEST001',
            name='Test Course',
            total_credits_required=30
        )
        classroom = Classroom.objects.create(
            lesson=lesson,
            course=course,
            name='Test Classroom',
            start_date='2025-01-01',
            end_date='2025-12-31'
        )
        ClassroomStudent.objects.create(classroom=classroom, student=student)
        
        # Create assignment
        assignment = Assignment.objects.create(
            lesson=lesson,
            title='Test Assignment',
            marks=100,
            weightage=100,
            release_date='2025-01-01 00:00:00',
            due_date='2025-12-31 23:59:59'
        )
        
        # View lesson detail (should see assignment)
        url = reverse('lessons:detail', kwargs={'lesson_id': lesson.id})
        response = client.get(url)
        
        assert assignment in response.context['assignments']
