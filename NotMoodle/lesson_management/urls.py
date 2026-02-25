from django.urls import path
from . import views

app_name = "lessons"

urlpatterns = [
    path("", views.LessonListView.as_view(), name="list"),
    path("new/", views.LessonCreateView.as_view(), name="new"),
    path("<int:pk>/edit/", views.LessonUpdateView.as_view(), name="edit"),

    path("student/", views.student_lessons_list, name="student_list"),
    path("student/<int:lesson_id>/enroll/", views.enroll_in_lesson, name="enroll"),
    path("student/<int:lesson_id>/", views.lesson_detail, name="detail"),
    path("student/<int:lesson_id>/reading/<int:reading_id>/toggle/", views.toggle_reading_progress, name="toggle_reading"),
    path("student/<int:lesson_id>/video/toggle/", views.toggle_video_progress, name="toggle_video"),

    path("assignments/<int:pk>/download/", views.download_assignment_pdf, name="assignment_download"),
    path("student/<int:lesson_id>/assignments/<int:assignment_id>/submit/",
         views.submit_assignment, name="submit_assignment"),
]
