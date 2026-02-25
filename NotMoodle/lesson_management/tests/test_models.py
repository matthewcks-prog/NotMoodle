"""Tests for lesson_management models."""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from model_bakery import baker
from lesson_management.models import (
    Lesson, ReadingList, Assignment, AssignmentAttachment,
    LessonEnrollment, ReadingListProgress, VideoProgress, AssignmentSubmission
)


@pytest.mark.django_db
class TestLesson:
    """Test Lesson model."""
    
    def test_create_lesson(self, teacher):
        """Test creating a lesson."""
        lesson = baker.make(
            Lesson,
            unit_code="CS101",
            title="Python Basics",
            description="Learn Python",
            objectives="Understand Python syntax",
            estimated_effort=5,
            lesson_designer=teacher,
            lesson_credits=6,
            status="published",
        )
        
        assert lesson.id is not None
        assert lesson.unit_code == "CS101"
        assert lesson.status == "published"
    
    def test_lesson_str(self, lesson):
        """Test __str__ method."""
        str_repr = str(lesson)
        assert lesson.unit_code in str_repr
        assert lesson.title in str_repr
    
    def test_lesson_unique_unit_code(self, teacher):
        """Test unique constraint on unit_code."""
        baker.make(Lesson, unit_code="CS101", lesson_designer=teacher)
        
        with pytest.raises(IntegrityError):
            Lesson.objects.create(
                unit_code="CS101",
                title="Duplicate",
                estimated_effort=5,
                lesson_designer=teacher,
            )
    
    def test_lesson_clean_self_prerequisite(self, lesson):
        """Test that lesson cannot be its own prerequisite."""
        lesson.prerequisites.add(lesson)
        
        with pytest.raises(ValidationError):
            lesson.clean()
    
    def test_lesson_youtube_video_id(self, lesson):
        """Test YouTube video ID extraction."""
        lesson.youtube_link = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = lesson.get_youtube_video_id()
        
        assert video_id == "dQw4w9WgXcQ"
    
    def test_lesson_youtube_thumbnail(self, lesson):
        """Test YouTube thumbnail generation."""
        lesson.youtube_link = "https://www.youtube.com/watch?v=test123"
        thumbnail = lesson.get_youtube_thumbnail()
        
        assert "test123" in thumbnail
        assert "img.youtube.com" in thumbnail
    
    def test_lesson_youtube_embed_url(self, lesson):
        """Test YouTube embed URL generation."""
        lesson.youtube_link = "https://www.youtube.com/watch?v=embed123"
        embed_url = lesson.get_youtube_embed_url()
        
        assert "embed123" in embed_url
        assert "embed" in embed_url
    
    def test_lesson_student_passed_no_assignments(self, lesson, student):
        """Test student_passed with no assignments."""
        passed, percentage, details = lesson.student_passed(student)
        
        assert passed is False
        assert percentage == Decimal('0')
        assert details['has_grades'] is False
    
    def test_lesson_student_passed_with_grades(self, lesson, student, teacher):
        """Test student_passed calculation with grades."""
        # Create assignments
        assignment1 = baker.make(
            Assignment,
            lesson=lesson,
            marks=Decimal('100'),
            weightage=Decimal('50'),
            release_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
        )
        assignment2 = baker.make(
            Assignment,
            lesson=lesson,
            marks=Decimal('100'),
            weightage=Decimal('50'),
            release_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
        )
        
        # Create grades
        from classroom_and_grading.models import AssignmentGrade
        baker.make(
            AssignmentGrade,
            assignment=assignment1,
            student=student,
            marks_awarded=Decimal('80'),  # 80% * 50% weight = 40%
        )
        baker.make(
            AssignmentGrade,
            assignment=assignment2,
            student=student,
            marks_awarded=Decimal('90'),  # 90% * 50% weight = 45%
        )
        
        passed, percentage, details = lesson.student_passed(student)
        
        assert passed is True  # 40% + 45% = 85% >= 50%
        assert percentage == Decimal('85')
        assert details['has_grades'] is True
        assert details['graded_assignments'] == 2


@pytest.mark.django_db
class TestAssignment:
    """Test Assignment model."""
    
    def test_create_assignment(self, lesson):
        """Test creating an assignment."""
        assignment = baker.make(
            Assignment,
            title="Homework 1",
            lesson=lesson,
            release_date=timezone.now(),
            due_date=timezone.now() + timedelta(days=7),
            marks=Decimal('100'),
            weightage=Decimal('50'),
        )
        
        assert assignment.id is not None
        assert assignment.title == "Homework 1"
    
    def test_assignment_str(self, assignment):
        """Test __str__ method."""
        str_repr = str(assignment)
        assert assignment.title in str_repr
    
    def test_assignment_clean_due_before_release(self, lesson):
        """Test validation: due date before release date."""
        now = timezone.now()
        assignment = Assignment(
            title="Test",
            lesson=lesson,
            release_date=now,
            due_date=now - timedelta(days=1),  # Before release
            marks=Decimal('100'),
            weightage=Decimal('50'),
        )
        
        with pytest.raises(ValidationError):
            assignment.clean()
    
    def test_assignment_unique_together(self, lesson):
        """Test unique constraint on lesson-title pair."""
        baker.make(Assignment, lesson=lesson, title="Assignment 1")
        
        with pytest.raises(IntegrityError):
            Assignment.objects.create(
                lesson=lesson,
                title="Assignment 1",
                release_date=timezone.now(),
                due_date=timezone.now() + timedelta(days=7),
                marks=Decimal('100'),
                weightage=Decimal('50'),
            )


@pytest.mark.django_db
class TestLessonEnrollment:
    """Test LessonEnrollment model."""
    
    def test_create_lesson_enrollment(self, student, lesson):
        """Test creating a lesson enrollment."""
        enrollment = baker.make(
            LessonEnrollment,
            student=student,
            lesson=lesson,
        )
        
        assert enrollment.id is not None
        assert enrollment.student == student
        assert enrollment.lesson == lesson
    
    def test_lesson_enrollment_str(self, lesson_enrollment):
        """Test __str__ method."""
        str_repr = str(lesson_enrollment)
        assert lesson_enrollment.lesson.unit_code in str_repr
    
    def test_lesson_enrollment_unique_together(self, student, lesson):
        """Test unique constraint on student-lesson pair."""
        baker.make(LessonEnrollment, student=student, lesson=lesson)
        
        with pytest.raises(IntegrityError):
            LessonEnrollment.objects.create(student=student, lesson=lesson)


@pytest.mark.django_db
class TestVideoProgress:
    """Test VideoProgress model."""
    
    def test_create_video_progress(self, student, lesson):
        """Test creating video progress."""
        progress = baker.make(
            VideoProgress,
            student=student,
            lesson=lesson,
            watched=True,
        )
        
        assert progress.id is not None
        assert progress.watched is True
    
    def test_video_progress_str(self, student, lesson):
        """Test __str__ method."""
        progress = baker.make(VideoProgress, student=student, lesson=lesson, watched=True)
        str_repr = str(progress)
        
        assert "watched" in str_repr.lower()


@pytest.mark.django_db
class TestReadingListProgress:
    """Test ReadingListProgress model."""
    
    def test_create_reading_progress(self, student, lesson):
        """Test creating reading progress."""
        reading = baker.make("lesson_management.ReadingList", lesson=lesson)
        progress = baker.make(
            ReadingListProgress,
            student=student,
            reading=reading,
            done=True,
        )
        
        assert progress.id is not None
        assert progress.done is True

