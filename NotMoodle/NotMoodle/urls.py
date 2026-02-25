from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from welcome_page import views as wp_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("oauth/", include("social_django.urls", namespace="social")),
    path("", include(("welcome_page.urls", "welcome_page"), namespace="welcome_page")),
    # Canonical login endpoints (explicit views instead of RedirectView)
    path("login/students/", lambda request: redirect("student_management:student_login"), name="login_students"),
    path("login/teachers/", lambda request: redirect("teachersManagement:teacher_login"), name="login_teachers"),

    # App namespaces
    path("teachers/", include(("teachersManagement.urls", "teachersManagement"), namespace="teachersManagement")),
    path("teachers/courses/", include(("course_management.urls_teachers", "teacher_courses"), namespace="teacher_courses")),
    path("students/", include(("student_management.urls", "student_management"), namespace="student_management")),
    path(
        "classrooms/",
        include(("classroom_and_grading.urls", "classroom_and_grading"), namespace="classroom_and_grading"),
    ),
    path("courses/", include(("course_management.urls", "course_management"), namespace="course_management")),
    # Student-facing lessons (stable namespace)
    path("lessons/", include(("lesson_management.urls", "lessons"), namespace="lessons")),
    # AI Assistant
    path("", include(("assist.urls", "assist"), namespace="assist")),

    # Direct route for generic 404 page (for explicit redirects)
    path("404/", wp_views.error_404, name="error_404"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# Error handlers for the whole project
handler404 = "welcome_page.views.error_404"
handler500 = "welcome_page.views.error_500"
handler403 = "welcome_page.views.error_403"
handler400 = "welcome_page.views.error_400"

