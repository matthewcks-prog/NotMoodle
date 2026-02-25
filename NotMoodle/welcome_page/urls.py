from django.urls import path
from . import views

app_name = "welcome_page"

urlpatterns = [
    path("", views.welcome_page, name="welcome_page"),
    path("signup/", views.student_signup, name="student_signup"),
    # keep legacy thanks route but it now redirects to home in view
    path("thanks/", views.signup_thanks, name="signup_thanks"),
    path("login/", views.login_choice, name="login"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("courses/", views.courses, name="courses"),
    path("news/", views.news, name="news"),
]
