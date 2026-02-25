from django.contrib import admin
from .models import Course, Enrollment

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "get_director_name", "status", "created_at")
    list_filter = ("status", "director")
    search_fields = ("code", "name", "director__user__first_name", "director__user__last_name", "director__display_name", "director__contact_email")
    autocomplete_fields = ["director"]
    
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'description', 'status')
        }),
        ('Course Management', {
            'fields': ('director', 'total_credits_required'),
            'description': 'Assign a teacher to direct this course'
        }),
    )
    
    # NEW: Custom method to display director name properly
    def get_director_name(self, obj):
        if obj.director:
            return obj.director.get_full_name()
        return "No director assigned"
    get_director_name.short_description = 'Director'

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "enrolled_by", "enrolled_at")
    list_filter = ("enrolled_by", "course__status")
    search_fields = ("student__first_name", "student__last_name", "course__code", "course__name")