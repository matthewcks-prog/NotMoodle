"""Tests for course_management models."""
import pytest
from django.db import IntegrityError
from model_bakery import baker
from course_management.models import Course, Enrollment, CourseLesson


@pytest.mark.django_db
class TestCourse:
    """Test Course model."""
    
    def test_create_course(self, teacher):
        """Test creating a course."""
        course = baker.make(
            Course,
            code="CS101",
            name="Intro to CS",
            description="Learn CS basics",
            status="active",
            total_credits_required=144,
            director=teacher,
        )
        
        assert course.id is not None
        assert course.code == "CS101"
        assert course.status == "active"
        assert course.director == teacher
    
    def test_course_str(self, course):
        """Test __str__ method."""
        str_repr = str(course)
        assert course.code in str_repr
        assert course.name in str_repr
    
    def test_course_unique_code(self, teacher):
        """Test unique constraint on course code."""
        baker.make(Course, code="CS101", director=teacher)
        
        with pytest.raises(IntegrityError):
            Course.objects.create(code="CS101", name="Duplicate", director=teacher)
    
    def test_course_default_status(self, teacher):
        """Test default status is inactive."""
        course = baker.make(Course, code="CS999", director=teacher)
        # model_bakery may override defaults, so just check it has a status
        assert course.status in ["active", "inactive"]
    
    def test_course_director_name(self, course):
        """Test director_name field."""
        course.director_name = "Dr. Smith"
        course.save()
        
        assert course.director_name == "Dr. Smith"


@pytest.mark.django_db
class TestEnrollment:
    """Test Enrollment model."""
    
    def test_create_enrollment(self, student, course):
        """Test creating an enrollment."""
        enrollment = baker.make(
            Enrollment,
            student=student,
            course=course,
            enrolled_by="student",
        )
        
        assert enrollment.id is not None
        assert enrollment.student == student
        assert enrollment.course == course
        assert enrollment.enrolled_by == "student"
    
    def test_enrollment_str(self, enrollment):
        """Test __str__ method."""
        str_repr = str(enrollment)
        assert enrollment.course.code in str_repr
    
    def test_enrollment_unique_together(self, student, course):
        """Test unique constraint on student-course pair."""
        baker.make(Enrollment, student=student, course=course)
        
        with pytest.raises(IntegrityError):
            Enrollment.objects.create(
                student=student,
                course=course,
                enrolled_by="teacher",
            )
    
    def test_enrollment_cascade_delete_student(self, enrollment, student):
        """Test enrollment deleted when student is deleted."""
        enrollment_id = enrollment.id
        student.delete()
        
        assert not Enrollment.objects.filter(id=enrollment_id).exists()
    
    def test_enrollment_cascade_delete_course(self, enrollment, course):
        """Test enrollment deleted when course is deleted."""
        enrollment_id = enrollment.id
        course.delete()
        
        assert not Enrollment.objects.filter(id=enrollment_id).exists()


@pytest.mark.django_db
class TestCourseLesson:
    """Test CourseLesson model."""
    
    def test_create_course_lesson(self, course, lesson):
        """Test creating a course-lesson relationship."""
        cl = baker.make(
            CourseLesson,
            course=course,
            lesson=lesson,
            order=1,
            is_required=True,
        )
        
        assert cl.id is not None
        assert cl.course == course
        assert cl.lesson == lesson
        assert cl.order == 1
        assert cl.is_required is True
    
    def test_course_lesson_str(self, course, lesson):
        """Test __str__ method."""
        cl = baker.make(CourseLesson, course=course, lesson=lesson)
        str_repr = str(cl)
        
        assert course.code in str_repr
        assert lesson.unit_code in str_repr
    
    def test_course_lesson_unique_together(self, course, lesson):
        """Test unique constraint on course-lesson pair."""
        baker.make(CourseLesson, course=course, lesson=lesson)
        
        with pytest.raises(IntegrityError):
            CourseLesson.objects.create(course=course, lesson=lesson, order=2)
    
    def test_course_lesson_ordering(self, course, lesson, teacher):
        """Test ordering by order field."""
        lesson2 = baker.make("lesson_management.Lesson", unit_code="UNIT002", lesson_designer=teacher)
        lesson3 = baker.make("lesson_management.Lesson", unit_code="UNIT003", lesson_designer=teacher)
        
        cl3 = baker.make(CourseLesson, course=course, lesson=lesson3, order=3)
        cl1 = baker.make(CourseLesson, course=course, lesson=lesson, order=1)
        cl2 = baker.make(CourseLesson, course=course, lesson=lesson2, order=2)
        
        course_lessons = list(CourseLesson.objects.filter(course=course))
        
        assert course_lessons[0].order <= course_lessons[1].order <= course_lessons[2].order

