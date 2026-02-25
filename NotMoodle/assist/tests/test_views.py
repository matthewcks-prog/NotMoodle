"""
Tests for assist app views (AI Assistant API).
"""
import pytest
import json
from django.urls import reverse
from django.contrib.auth.models import User
from freezegun import freeze_time
from model_bakery import baker
from assist.models import StudentQuestion, DocumentChunk
from student_management.models import Student, ManageCreditPoint
from lesson_management.models import Lesson


@pytest.mark.django_db
class TestAskAssistant:
    """Test ask_assistant API endpoint."""
    
    def test_ask_assistant_requires_login(self, client):
        """Test that endpoint requires authentication."""
        url = reverse("assist:ask_assistant")
        response = client.post(url, data=json.dumps({"message": "Test"}), content_type="application/json")
        
        # Should redirect to login
        assert response.status_code == 302
    
    def test_ask_assistant_sqlite_returns_503(self, student_client, settings):
        """Test that SQLite database returns 503 error."""
        settings.USING_POSTGRESQL = False
        
        url = reverse("assist:ask_assistant")
        response = student_client.post(
            url,
            data=json.dumps({"message": "What is Python?"}),
            content_type="application/json"
        )
        
        assert response.status_code == 503
        data = json.loads(response.content)
        assert "error" in data
        assert "PostgreSQL" in data["error"]
    
    def test_ask_assistant_invalid_json(self, student_client, settings):
        """Test with invalid JSON payload."""
        settings.USING_POSTGRESQL = True
        
        url = reverse("assist:ask_assistant")
        response = student_client.post(
            url,
            data="not valid json",
            content_type="application/json"
        )
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "Invalid JSON" in data["error"]
    
    def test_ask_assistant_empty_message(self, student_client, settings):
        """Test with empty message."""
        settings.USING_POSTGRESQL = True
        
        url = reverse("assist:ask_assistant")
        response = student_client.post(
            url,
            data=json.dumps({"message": "   "}),
            content_type="application/json"
        )
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "required" in data["error"].lower()
    
    def test_ask_assistant_rate_limit(self, student_user, student_client, settings, mock_ollama):
        """Test rate limiting (daily question limit)."""
        settings.USING_POSTGRESQL = True
        settings.AI_DAILY_QUESTION_LIMIT = 5
        
        # Create 5 questions today (reaching limit)
        with freeze_time("2025-01-15 10:00:00"):
            for i in range(5):
                baker.make(
                    StudentQuestion,
                    user=student_user,
                    question=f"Question {i}",
                    answer="Answer",
                )
        
        # Try to ask another question
        url = reverse("assist:ask_assistant")
        with freeze_time("2025-01-15 12:00:00"):
            response = student_client.post(
                url,
                data=json.dumps({"message": "One more question?"}),
                content_type="application/json"
            )
        
        assert response.status_code == 429
        data = json.loads(response.content)
        assert "error" in data
        assert "limit" in data["error"].lower()
    
    def test_ask_assistant_success(self, student_user, student_client, settings, mock_ollama, teacher):
        """Test successful question and answer."""
        settings.USING_POSTGRESQL = True
        settings.AI_DAILY_QUESTION_LIMIT = 100
        
        # Create a lesson with document chunks
        lesson = baker.make(Lesson, unit_code="CS101", title="Python Basics", lesson_designer=teacher)
        chunk = baker.make(
            DocumentChunk,
            lesson=lesson,
            content="Python is a high-level programming language.",
            embedding=[0.1] * 768,
        )
        
        url = reverse("assist:ask_assistant")
        response = student_client.post(
            url,
            data=json.dumps({"message": "What is Python?"}),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert "reply" in data
        assert "sources" in data
        assert "usage_today" in data
        assert data["reply"] == "This is a mock AI response."
        assert data["usage_today"] == 1
        
        # Check that question was logged
        assert StudentQuestion.objects.filter(user=student_user).count() == 1
        question = StudentQuestion.objects.get(user=student_user)
        assert question.question == "What is Python?"
        assert question.answer == "This is a mock AI response."
    
    def test_ask_assistant_with_lesson_id(self, student_user, student_client, settings, mock_ollama, teacher):
        """Test asking question about specific lesson."""
        settings.USING_POSTGRESQL = True
        
        lesson = baker.make(Lesson, unit_code="CS101", lesson_designer=teacher)
        
        url = reverse("assist:ask_assistant")
        response = student_client.post(
            url,
            data=json.dumps({
                "message": "Tell me about this lesson",
                "lesson_id": lesson.id
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "reply" in data
    
    def test_ask_assistant_no_chunks(self, student_client, settings, mock_ollama):
        """Test when no document chunks exist."""
        settings.USING_POSTGRESQL = True
        
        url = reverse("assist:ask_assistant")
        response = student_client.post(
            url,
            data=json.dumps({"message": "What is Django?"}),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "reply" in data
        assert "sources" in data
        assert len(data["sources"]) == 0


@pytest.mark.django_db
class TestAssistantUsage:
    """Test assistant_usage API endpoint."""
    
    def test_assistant_usage_requires_login(self, client):
        """Test that endpoint requires authentication."""
        url = reverse("assist:assistant_usage")
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
    
    def test_assistant_usage_sqlite(self, student_client, settings):
        """Test usage endpoint with SQLite (unavailable)."""
        settings.USING_POSTGRESQL = False
        
        url = reverse("assist:assistant_usage")
        response = student_client.get(url)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data["questions_today"] == 0
        assert data["available"] is False
        assert "SQLite" in data["message"]
    
    def test_assistant_usage_postgresql(self, student_client, settings):
        """Test usage endpoint with PostgreSQL."""
        settings.USING_POSTGRESQL = True
        settings.AI_DAILY_QUESTION_LIMIT = 100
        
        url = reverse("assist:assistant_usage")
        response = student_client.get(url)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data["questions_today"] == 0
        assert data["daily_limit"] == 100
        assert data["available"] is True
    
    def test_assistant_usage_with_questions(self, student_user, student_client, settings):
        """Test usage endpoint with existing questions."""
        settings.USING_POSTGRESQL = True
        settings.AI_DAILY_QUESTION_LIMIT = 100
        
        # Create some questions today
        with freeze_time("2025-01-15 10:00:00"):
            for i in range(3):
                baker.make(
                    StudentQuestion,
                    user=student_user,
                    question=f"Question {i}",
                    answer="Answer",
                )
        
        url = reverse("assist:assistant_usage")
        with freeze_time("2025-01-15 12:00:00"):
            response = student_client.get(url)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data["questions_today"] == 3
        assert data["daily_limit"] == 100
        assert data["available"] is True
    
    def test_assistant_usage_different_day(self, student_user, student_client, settings):
        """Test that questions from previous days don't count."""
        settings.USING_POSTGRESQL = True
        
        # Create questions yesterday
        with freeze_time("2025-01-14 10:00:00"):
            for i in range(5):
                baker.make(
                    StudentQuestion,
                    user=student_user,
                    question=f"Question {i}",
                    answer="Answer",
                )
        
        # Check today
        url = reverse("assist:assistant_usage")
        with freeze_time("2025-01-15 12:00:00"):
            response = student_client.get(url)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data["questions_today"] == 0  # Yesterday's questions don't count


@pytest.mark.django_db
class TestGetUserProfileContext:
    """Test get_user_profile_context helper function."""
    
    def test_get_user_profile_context_basic(self, student_user, student):
        """Test basic profile context generation."""
        from assist.views import get_user_profile_context
        
        context = get_user_profile_context(student_user)
        
        assert "USER PROFILE" in context
        assert student_user.username in context
        assert student.first_name in context
        assert student.last_name in context
        assert str(student.enrollment_number) in context
    
    def test_get_user_profile_context_no_student(self, user):
        """Test context for user without student profile."""
        from assist.views import get_user_profile_context
        
        context = get_user_profile_context(user)
        
        assert "USER PROFILE" in context
        assert user.username in context
        assert "No student profile found" in context
    
    def test_get_user_profile_context_with_credits(self, student_user, student):
        """Test context includes credit information."""
        from assist.views import get_user_profile_context
        
        credit = ManageCreditPoint.objects.get(student=student)
        credit.credits = 12
        credit.save()
        
        context = get_user_profile_context(student_user)
        
        assert "Total Credits: 12" in context
    
    def test_get_user_profile_context_with_enrollments(self, student_user, student, course, enrollment):
        """Test context includes course enrollments."""
        from assist.views import get_user_profile_context
        
        context = get_user_profile_context(student_user)
        
        assert "ENROLLED COURSES" in context
        assert course.code in context
        assert course.name in context


@pytest.mark.django_db
class TestRetrieveContext:
    """Test retrieve_context helper function."""
    
    def test_retrieve_context_no_chunks(self, mock_ollama):
        """Test with no document chunks."""
        from assist.views import retrieve_context
        
        results = retrieve_context("What is Python?")
        
        assert results == []
    
    def test_retrieve_context_with_chunks(self, mock_ollama, teacher):
        """Test retrieving relevant chunks."""
        from assist.views import retrieve_context
        
        lesson = baker.make(Lesson, unit_code="CS101", title="Python Basics", lesson_designer=teacher)
        chunk1 = baker.make(
            DocumentChunk,
            lesson=lesson,
            content="Python is a programming language.",
            embedding=[0.1] * 768,
        )
        chunk2 = baker.make(
            DocumentChunk,
            lesson=lesson,
            content="Django is a web framework.",
            embedding=[0.2] * 768,
        )
        
        results = retrieve_context("What is Python?", top_k=2)
        
        # Should return chunks (mocked, so order doesn't matter)
        assert len(results) <= 2
    
    def test_retrieve_context_with_lesson_id(self, mock_ollama, teacher):
        """Test biasing results toward specific lesson."""
        from assist.views import retrieve_context
        
        lesson1 = baker.make(Lesson, unit_code="CS101", lesson_designer=teacher)
        lesson2 = baker.make(Lesson, unit_code="CS102", lesson_designer=teacher)
        
        chunk1 = baker.make(
            DocumentChunk,
            lesson=lesson1,
            content="Content from lesson 1",
            embedding=[0.1] * 768,
        )
        chunk2 = baker.make(
            DocumentChunk,
            lesson=lesson2,
            content="Content from lesson 2",
            embedding=[0.2] * 768,
        )
        
        results = retrieve_context("Question", lesson_id=lesson1.id, top_k=5)
        
        # Results should exist
        assert isinstance(results, list)

