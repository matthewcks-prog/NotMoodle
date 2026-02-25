from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import TeacherProfile

class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = True
    extra = 0
    # NEW: Include the new fields in the inline
    fields = ('department', 'hire_date', 'display_name', 'contact_email')

class UserAdmin(BaseUserAdmin):
    inlines = [TeacherProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "is_active", "is_staff")

# re-register User with inline
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Also expose TeacherProfile as its own admin model for direct management
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "get_display_name", "get_contact_email", "department", "hire_date")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "department", "display_name", "contact_email")
    list_filter = ("department", "hire_date")
    
    # NEW: Add fieldsets for better organization
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Display Information', {
            'fields': ('display_name', 'contact_email'),
            'description': 'Information shown to students and in course listings'
        }),
        ('Administrative Details', {
            'fields': ('department', 'hire_date')
        }),
    )
    
    # NEW: Custom methods to display in list_display
    def get_display_name(self, obj):
        return obj.get_full_name()
    get_display_name.short_description = 'Display Name'
    
    def get_contact_email(self, obj):
        return obj.get_email()
    get_contact_email.short_description = 'Contact Email'
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct