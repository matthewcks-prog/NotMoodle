"""
Global pytest fixtures for NotMoodle test suite.

Provides reusable fixtures for users, students, teachers, courses, etc.
"""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone
from datetime import timedelta
from model_bakery import baker


# ============================
# PYTEST CONFIGURATION
# ============================

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for test session.
    """
    # Any session-level DB setup can go here
    pass


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.
    """
    pass


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    """
    Use temporary directory for media files during tests.
    """
    settings.MEDIA_ROOT = tmpdir.strpath


# ============================
# USER FIXTURES
# ============================

@pytest.fixture
def user():
    """
    Create a basic authenticated user.
    """
    return baker.make(
        User,
        username="testuser",
        email="testuser@example.com",
        is_active=True,
        is_staff=False,
    )


@pytest.fixture
def staff_user():
    """
    Create a staff user.
    """
    return baker.make(
        User,
        username="staffuser",
        email="staff@example.com",
        is_active=True,
        is_staff=True,
    )


@pytest.fixture
def superuser():
    """
    Create a superuser.
    """
    return baker.make(
        User,
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )


# ============================
# STUDENT FIXTURES
# ============================

@pytest.fixture
def student(user):
    """
    Create a Student profile linked to a user.
    """
    from student_management.models import Student, ManageCreditPoint
    from datetime import date
    
    student = baker.make(
        Student,
        user=user,
        first_name="Test",
        last_name="Student",
        email=user.email,
        date_of_birth=date(2000, 1, 1),
        enrollment_number=1001,
        status="active",
    )
    
    # Ensure credit record exists
    baker.make(ManageCreditPoint, student=student, credits=0)
    
    return student


@pytest.fixture
def student_user(student):
    """
    Return the user associated with a student (for easy authentication).
    """
    return student.user


# ============================
# TEACHER FIXTURES
# ============================

@pytest.fixture
def teacher_user():
    """
    Create a user for a teacher.
    """
    return baker.make(
        User,
        username="teacher",
        email="teacher@example.com",
        is_active=True,
        is_staff=True,  # Teachers typically have staff access
    )


@pytest.fixture
def teacher(teacher_user):
    """
    Create a TeacherProfile.
    """
    from teachersManagement.models import TeacherProfile
    from datetime import date
    
    return baker.make(
        TeacherProfile,
        user=teacher_user,
        department="Computer Science",
        hire_date=date(2020, 1, 1),
        display_name="Dr. Test Teacher",
        contact_email="teacher@example.com",
    )


# ============================
# COURSE & LESSON FIXTURES
# ============================

@pytest.fixture
def course(teacher):
    """
    Create a Course.
    """
    from course_management.models import Course
    
    return baker.make(
        Course,
        code="CS101",
        name="Introduction to Computer Science",
        description="A foundational CS course",
        status="active",
        total_credits_required=144,
        director=teacher,
    )


@pytest.fixture
def lesson(teacher):
    """
    Create a Lesson.
    """
    from lesson_management.models import Lesson
    
    return baker.make(
        Lesson,
        unit_code="UNIT001",
        title="Introduction to Python",
        description="Learn Python basics",
        estimated_effort=5,
        lesson_designer=teacher,
        status="published",
        lesson_credits=6,
    )


@pytest.fixture
def assignment(lesson):
    """
    Create an Assignment for a lesson.
    """
    from lesson_management.models import Assignment
    from decimal import Decimal
    
    return baker.make(
        Assignment,
        title="Assignment 1",
        lesson=lesson,
        release_date=timezone.now(),
        due_date=timezone.now() + timedelta(days=7),
        marks=Decimal("100.00"),
        weightage=Decimal("50.00"),
        description="First assignment",
    )


# ============================
# ENROLLMENT FIXTURES
# ============================

@pytest.fixture
def enrollment(student, course):
    """
    Create a Course Enrollment.
    """
    from course_management.models import Enrollment
    
    return baker.make(
        Enrollment,
        student=student,
        course=course,
        enrolled_by="student",
    )


@pytest.fixture
def lesson_enrollment(student, lesson):
    """
    Create a Lesson Enrollment.
    """
    from lesson_management.models import LessonEnrollment
    
    return baker.make(
        LessonEnrollment,
        student=student,
        lesson=lesson,
    )


# ============================
# CLASSROOM FIXTURES
# ============================

@pytest.fixture
def classroom(course, lesson, teacher):
    """
    Create a Classroom.
    """
    from classroom_and_grading.models import Classroom
    
    return baker.make(
        Classroom,
        course=course,
        lesson=lesson,
        teacher=teacher,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=30),
    )


# ============================
# CLIENT FIXTURES
# ============================

@pytest.fixture
def client():
    """
    Django test client.
    """
    return Client()


@pytest.fixture
def authenticated_client(user):
    """
    Django test client with authenticated user.
    """
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def student_client(student_user):
    """
    Django test client authenticated as a student.
    """
    client = Client()
    client.force_login(student_user)
    return client


@pytest.fixture
def teacher_client(teacher_user):
    """
    Django test client authenticated as a teacher.
    """
    client = Client()
    client.force_login(teacher_user)
    return client


# ============================
# MOCK FIXTURES
# ============================

@pytest.fixture
def mock_ollama(monkeypatch):
    """
    Mock Ollama API calls for AI assistant tests.
    """
    def mock_embed_texts(texts, model=None):
        # Return dummy embeddings (768 dimensions for nomic-embed-text)
        return [[0.1] * 768 for _ in texts]
    
    def mock_chat(messages, model=None):
        return "This is a mock AI response."
    
    def mock_estimate_tokens(text):
        return len(text) // 4
    
    from assist import ollama
    monkeypatch.setattr(ollama, "embed_texts", mock_embed_texts)
    monkeypatch.setattr(ollama, "chat", mock_chat)
    monkeypatch.setattr(ollama, "estimate_tokens", mock_estimate_tokens)
    
    return {
        "embed_texts": mock_embed_texts,
        "chat": mock_chat,
        "estimate_tokens": mock_estimate_tokens,
    }


# ============================
# SETTINGS FIXTURES
# ============================

@pytest.fixture
def override_settings():
    """
    Context manager for temporarily overriding Django settings.
    """
    from django.test import override_settings as django_override
    return django_override

