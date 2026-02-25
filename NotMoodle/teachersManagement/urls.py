from django.urls import path, include
from django.shortcuts import redirect
from . import views

app_name = "teachersManagement"

urlpatterns = [
    path("", lambda request: redirect("teachersManagement:teacher_login")),
    path("login/", views.teacher_login, name="teacher_login"),
    path("logout/", views.teacher_logout, name="teacher_logout"),
    path("home/", views.teacher_home, name="teacher_home"),
    path("lesson/", include(("lesson_management.urls", "lessons"), namespace="lessons")),
    #
    path("students/status/", views.StudentStatusListView.as_view(), name="student_status_list"),
    path("students/status/<int:pk>/", views.StudentStatusUpdateView.as_view(), name="student_status_edit"),
    path("generate-student-report/", views.generate_student_report, name="generate_student_report"),
]
