"""URL configuration for assist app."""
from django.urls import path
from . import views

app_name = "assist"

urlpatterns = [
    path("api/notmoodle/ask/", views.ask_assistant, name="ask_assistant"),
    path("api/notmoodle/usage/", views.assistant_usage, name="assistant_usage"),
]
