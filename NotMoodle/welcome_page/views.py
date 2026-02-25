from django.shortcuts import render, redirect
from django.contrib import messages
from student_management.forms import StudentSignupForm
from .models import ContactMessage
from course_management.models import Course
from django.contrib.auth import login as auth_login
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest

# Create your views here.
def welcome_page(request):
    return render(request, "welcome_page/welcome_page.html")

def student_signup(request):
    if request.method == "POST":
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            # send student to course selection, not dashboard
            return redirect("course_management:student_course_list")
    else:
        form = StudentSignupForm()
    return render(request, "welcome_page/student_signup.html", {"form": form})

def signup_thanks(request):
    # No longer used; keep for compatibility but redirect to home
    return redirect("welcome_page:welcome_page")

def login_choice(request):
    if request.user.is_authenticated:
        # If already logged in, send to appropriate dashboard/home
        if getattr(request.user, "is_staff", False):
            return redirect("teachersManagement:teacher_home")
        if hasattr(request.user, "student"):
            return redirect("student_management:student_dashboard")
        return redirect("welcome_page:welcome_page")
    return render(request, "welcome_page/login_choice.html")

# note: avoid defining a view named 'login' to prevent overshadowing django.contrib.auth.login


def about(request):
    return render(request, "welcome_page/about.html")


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        message_text = request.POST.get("message", "").strip()
        if name and email and message_text:
            ContactMessage.objects.create(name=name, email=email, message=message_text)
            messages.success(request, "Thanks for reaching out! Your message has been recorded.")
            return redirect("welcome_page:contact")
        messages.error(request, "Please fill in all fields.")
    return render(request, "welcome_page/contact.html")


def courses(request):
    courses_qs = Course.objects.all().order_by("name")
    # If the user is authenticated and is a student, reuse the richer student list UI
    if request.user.is_authenticated and hasattr(request.user, "student"):
        # NEW: Check if student has dropped out
        if request.user.student.status == "dropout":
            return render(request, "student_management/dropout_notice.html", {
                "student": request.user.student
            })
        
        # mimic context of student_course_list
        from course_management.selectors import get_enrolled_course_ids_for_student
        enrolled_ids = get_enrolled_course_ids_for_student(request.user.student.id)
        # attach simple progress text for template, if available
        credits_completed = getattr(getattr(request.user.student, "credit", None), "credits", 0) or 0
        for c in courses_qs:
            setattr(c, "progress_text", f"{credits_completed} / {getattr(c, 'total_credits_required', 144)} credits")
        
        return render(request, "course_management/student_course_list.html", {
            "courses": courses_qs,
            "enrolled_course_ids": enrolled_ids,
        })
    # Otherwise show the public courses page
    return render(request, "welcome_page/courses.html", {"courses": courses_qs})


def news(request):
    items = [
        {
            "title": "NotMoodle is now live!!",
            "body": "Students and instructors can now login and start using the platform :)",
            "date": "2025‑10‑01",
        },
        {
            "title": "October maintenance window",
            "body": "Minor performance upgrades will roll out this weekend .",
            "date": "2025‑10‑05",
        },
    ]
    return render(request, "welcome_page/news.html", {"items": items})


# ---- Error pages ----
def error_404(request, exception=None):
    # General purpose 404 page renderer
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "404.html", status=500)


def error_403(request, exception=None):
    return render(request, "404.html", status=403)


def error_400(request, exception=None):
    return render(request, "404.html", status=400)