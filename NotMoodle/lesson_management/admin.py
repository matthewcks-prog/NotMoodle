# lesson_management/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Lesson, Assignment, ReadingList, AssignmentAttachment, LessonCreditAwarded

# ----- ReadingList inline under Lesson -----
class ReadingListInline(admin.TabularInline):
    model = ReadingList
    extra = 1
    fields = ("title", "url", "description", "order")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "unit_code",
        "title",
        "lesson_designer",
        "status",
        "lesson_credits",
        "date_of_creation",
        "date_of_update",
    )
    list_filter = ("status", "lesson_designer")
    search_fields = (
        "unit_code",
        "title",
        "lesson_designer__user__first_name",
        "lesson_designer__user__last_name",
    )
    filter_horizontal = ("prerequisites",)
    inlines = [ReadingListInline]


# ----- Attachments inline under Assignment -----
class AssignmentAttachmentInline(admin.TabularInline):  # use StackedInline if you prefer tall rows
    model = AssignmentAttachment
    extra = 1
    fields = ("file", "preview", "uploaded_at")
    readonly_fields = ("preview", "uploaded_at")

    def preview(self, obj):
        if obj.pk and obj.file:
            url = obj.file.url
            # Lightweight: just a link (works everywhere)
            return format_html('<a href="{}" target="_blank">Open PDF</a>', url)
        return "-"

    preview.short_description = "Preview"


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "release_date", "due_date", "marks", "attachment_count")
    list_filter = ("lesson", "release_date", "due_date")
    search_fields = ("title", "lesson__title")
    date_hierarchy = "due_date"
    inlines = [AssignmentAttachmentInline]

    def attachment_count(self, obj):
        return obj.attachments.count()
    attachment_count.short_description = "Files"


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    list_display = ("lesson", "title", "order")
    list_filter = ("lesson",)
    search_fields = ("title", "lesson__title")
    ordering = ("lesson", "order")


@admin.register(LessonCreditAwarded)
class LessonCreditAwardedAdmin(admin.ModelAdmin):
    list_display = ("student", "lesson", "credits_amount", "awarded_at")
    list_filter = ("lesson", "awarded_at")
    search_fields = ("student__first_name", "student__last_name", "student__enrollment_number", "lesson__unit_code", "lesson__title")
    readonly_fields = ("student", "lesson", "credits_amount", "awarded_at")
    date_hierarchy = "awarded_at"
    
    def has_add_permission(self, request):
        # Prevent manual creation - credits should only be awarded via signal
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion for corrections/adjustments
        return request.user.is_superuser
