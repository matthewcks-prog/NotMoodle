from django.contrib import admin
from .models import Student
# Register your models here.

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("enrollment_number", "first_name", "last_name", "email", "year_of_study", "gpa")
    list_filter = ("year_of_study",)
    search_fields = ("enrollment_number", "first_name", "last_name", "email")
    