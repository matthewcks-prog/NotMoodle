from django.urls import path
from . import views

app_name = "teacher_courses"

urlpatterns = [
    path("", views.CourseListView.as_view(), name="teacher_course_list"),
    path("create/", views.CourseCreateView.as_view(), name="course_create"),
    path("<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course_edit"),
    path("<int:course_id>/manage/", views.manage_enrollments, name="manage_enrollments"),
    path("enrollments/", views.enrollment_management, name="enrollment_management"),
]


