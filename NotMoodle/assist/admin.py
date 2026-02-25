from django.contrib import admin
from .models import DocumentChunk, StudentQuestion


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ["id", "lesson", "token_count", "created_at"]
    list_filter = ["created_at", "lesson"]
    search_fields = ["content", "lesson__title"]
    readonly_fields = ["embedding", "created_at"]


@admin.register(StudentQuestion)
class StudentQuestionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "question_preview", "tokens_in", "tokens_out", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "question", "answer"]
    readonly_fields = ["created_at"]

    def question_preview(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_preview.short_description = "Question"
