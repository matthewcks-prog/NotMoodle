"""Models for NotMoodle AI Assistant (RAG-powered chatbot)."""
from django.db import models
from django.conf import settings
from pgvector.django import VectorField


class DocumentChunk(models.Model):
    """
    Text chunk extracted from a lesson with its vector embedding.
    
    Used for semantic search/retrieval to ground AI responses in course content.
    """
    lesson = models.ForeignKey(
        "lesson_management.Lesson",
        on_delete=models.CASCADE,
        related_name="chunks"
    )
    content = models.TextField(help_text="Text content of this chunk")
    embedding = VectorField(
        dimensions=768,  # nomic-embed-text produces 768-dim vectors
        help_text="Vector embedding for semantic search"
    )
    token_count = models.IntegerField(
        default=0,
        help_text="Approximate token count for this chunk"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["lesson", "-created_at"]),
        ]
        ordering = ["lesson", "id"]

    def __str__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Chunk {self.id} from {self.lesson.unit_code}: {preview}"


class StudentQuestion(models.Model):
    """
    Log of student questions to the AI assistant.
    
    Used for usage tracking, rate limiting, and analytics.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_questions"
    )
    question = models.TextField(help_text="Student's question")
    answer = models.TextField(help_text="AI assistant's answer")
    tokens_in = models.IntegerField(
        default=0,
        help_text="Approximate input tokens"
    )
    tokens_out = models.IntegerField(
        default=0,
        help_text="Approximate output tokens"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        preview = self.question[:50] + "..." if len(self.question) > 50 else self.question
        return f"Q from {self.user.username} at {self.created_at:%Y-%m-%d}: {preview}"
