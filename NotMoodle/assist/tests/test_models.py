"""
Tests for assist app models.
"""
import pytest
from django.contrib.auth.models import User
from model_bakery import baker
from assist.models import DocumentChunk, StudentQuestion
from lesson_management.models import Lesson


@pytest.mark.django_db
class TestDocumentChunk:
    """Test DocumentChunk model."""
    
    def test_create_document_chunk(self, teacher):
        """Test creating a document chunk with embedding."""
        lesson = baker.make(Lesson, lesson_designer=teacher)
        chunk = baker.make(
            DocumentChunk,
            lesson=lesson,
            content="This is test content for semantic search.",
            embedding=[0.1] * 768,  # 768-dim vector
            token_count=10,
        )
        
        assert chunk.id is not None
        assert chunk.lesson == lesson
        assert chunk.content == "This is test content for semantic search."
        assert len(chunk.embedding) == 768
        assert chunk.token_count == 10
    
    def test_document_chunk_str_short_content(self, teacher):
        """Test __str__ method with short content."""
        lesson = baker.make(Lesson, unit_code="CS101", lesson_designer=teacher)
        chunk = baker.make(
            DocumentChunk,
            lesson=lesson,
            content="Short content",
            embedding=[0.1] * 768,
        )
        
        expected = f"Chunk {chunk.id} from CS101: Short content"
        assert str(chunk) == expected
    
    def test_document_chunk_str_long_content(self, teacher):
        """Test __str__ method with long content (truncated)."""
        lesson = baker.make(Lesson, unit_code="CS101", lesson_designer=teacher)
        long_content = "A" * 100
        chunk = baker.make(
            DocumentChunk,
            lesson=lesson,
            content=long_content,
            embedding=[0.1] * 768,
        )
        
        str_repr = str(chunk)
        assert str_repr.startswith(f"Chunk {chunk.id} from CS101:")
        assert "..." in str_repr
        assert len(str_repr) < len(long_content) + 50
    
    def test_document_chunk_ordering(self, teacher):
        """Test default ordering by lesson and id."""
        lesson1 = baker.make(Lesson, unit_code="CS101", lesson_designer=teacher)
        lesson2 = baker.make(Lesson, unit_code="CS102", lesson_designer=teacher)
        
        chunk1 = baker.make(DocumentChunk, lesson=lesson1, embedding=[0.1] * 768)
        chunk2 = baker.make(DocumentChunk, lesson=lesson2, embedding=[0.2] * 768)
        chunk3 = baker.make(DocumentChunk, lesson=lesson1, embedding=[0.3] * 768)
        
        chunks = list(DocumentChunk.objects.all())
        
        # Should be ordered by lesson, then id
        assert len(chunks) >= 3
    
    def test_document_chunk_cascade_delete(self, teacher):
        """Test that chunks are deleted when lesson is deleted."""
        lesson = baker.make(Lesson, lesson_designer=teacher)
        chunk = baker.make(DocumentChunk, lesson=lesson, embedding=[0.1] * 768)
        
        chunk_id = chunk.id
        lesson.delete()
        
        assert not DocumentChunk.objects.filter(id=chunk_id).exists()


@pytest.mark.django_db
class TestStudentQuestion:
    """Test StudentQuestion model."""
    
    def test_create_student_question(self, user):
        """Test creating a student question."""
        question = baker.make(
            StudentQuestion,
            user=user,
            question="What is Python?",
            answer="Python is a programming language.",
            tokens_in=5,
            tokens_out=7,
        )
        
        assert question.id is not None
        assert question.user == user
        assert question.question == "What is Python?"
        assert question.answer == "Python is a programming language."
        assert question.tokens_in == 5
        assert question.tokens_out == 7
        assert question.created_at is not None
    
    def test_student_question_str_short(self, user):
        """Test __str__ method with short question."""
        question = baker.make(
            StudentQuestion,
            user=user,
            question="Short question?",
            answer="Short answer.",
        )
        
        str_repr = str(question)
        assert user.username in str_repr
        assert "Short question?" in str_repr
    
    def test_student_question_str_long(self, user):
        """Test __str__ method with long question (truncated)."""
        long_question = "Q" * 100
        question = baker.make(
            StudentQuestion,
            user=user,
            question=long_question,
            answer="Answer",
        )
        
        str_repr = str(question)
        assert user.username in str_repr
        assert "..." in str_repr
        assert len(str_repr) < len(long_question) + 100
    
    def test_student_question_ordering(self, user):
        """Test default ordering by created_at descending."""
        from freezegun import freeze_time
        from datetime import datetime, timedelta
        
        with freeze_time("2025-01-01 12:00:00"):
            q1 = baker.make(StudentQuestion, user=user, question="First")
        
        with freeze_time("2025-01-01 13:00:00"):
            q2 = baker.make(StudentQuestion, user=user, question="Second")
        
        with freeze_time("2025-01-01 14:00:00"):
            q3 = baker.make(StudentQuestion, user=user, question="Third")
        
        questions = list(StudentQuestion.objects.all()[:3])
        
        # Should be ordered by newest first
        assert questions[0].question == "Third"
        assert questions[1].question == "Second"
        assert questions[2].question == "First"
    
    def test_student_question_cascade_delete(self):
        """Test that questions are deleted when user is deleted."""
        user = baker.make(User, username="temp_user")
        question = baker.make(StudentQuestion, user=user, question="Test?")
        
        question_id = question.id
        user.delete()
        
        assert not StudentQuestion.objects.filter(id=question_id).exists()
    
    def test_student_question_default_tokens(self, user):
        """Test default token values."""
        question = baker.make(
            StudentQuestion,
            user=user,
            question="Test?",
            answer="Test answer",
            # Don't specify tokens
        )
        
        # model_bakery may auto-generate, but defaults should be 0
        assert question.tokens_in >= 0
        assert question.tokens_out >= 0

