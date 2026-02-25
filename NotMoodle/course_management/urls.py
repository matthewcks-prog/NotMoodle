from django.urls import path
from . import views

app_name = "course_management"

urlpatterns = [
    path("student/", views.student_course_list, name="student_course_list"),
    path("teacher/", views.teacher_course_list, name="teacher_course_list"),
    path("<int:course_id>/enroll/", views.enroll_in_course, name="enroll_in_course"),
    path("<int:course_id>/enroll/success/", views.enroll_success, name="enroll_success"),
    path("<int:course_id>/manage/", views.manage_enrollments, name="manage_enrollments"),
]
