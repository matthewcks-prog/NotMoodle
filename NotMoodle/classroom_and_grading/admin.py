from django.contrib import admin
from .models import Classroom, ClassroomStudent, AssignmentGrade

class ClassroomStudentInline(admin.TabularInline):
    model = ClassroomStudent
    extra = 0
    readonly_fields = ('added_at',)

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'lesson', 'teacher', 'start_date', 'end_date', 'created_at')
    list_filter = ('course', 'lesson', 'teacher', 'start_date')
    search_fields = ('course__name', 'lesson__title', 'teacher__user__username')
    inlines = [ClassroomStudentInline]
    
    def delete_model(self, request, obj):
        """Override delete to show what will be deleted"""
        # Get count of related objects that will be CASCADE deleted
        roster_count = obj.roster.count()
        
        # Delete the classroom (CASCADE will handle ClassroomStudent)
        obj.delete()
        
        self.message_user(
            request,
            f"Deleted classroom and removed {roster_count} student roster entries. "
            f"Note: Assignment grades are preserved as they are part of the permanent academic record.",
            level='warning'
        )

@admin.register(ClassroomStudent)
class ClassroomStudentAdmin(admin.ModelAdmin):
    list_display = ("classroom", "student", "added_at")
    list_filter = ("classroom",)
    search_fields = ("student__id", "student__first_name", "student__last_name")

@admin.register(AssignmentGrade)
class AssignmentGradeAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "marks_awarded", "graded_by", "graded_at")
    list_filter = ("assignment__lesson", "graded_by", "graded_at")
    search_fields = ("student__first_name", "student__last_name", "assignment__title")
    readonly_fields = ("graded_at",)
