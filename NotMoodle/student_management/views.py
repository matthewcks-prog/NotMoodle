from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.contrib.auth import login, logout
from django.utils import timezone
from django.db.models import Q

from .models import Student, ManageCreditPoint
from .forms import CreditChangeForm, StudentSignupForm, StudentLoginForm
from course_management.models import Enrollment
from lesson_management.models import LessonEnrollment, Lesson, Assignment, AssignmentSubmission
from classroom_and_grading.models import Classroom, ClassroomStudent
from teachersManagement.models import TeacherProfile


# ------------------------------------------------------------
# STAFF VIEWS
# ------------------------------------------------------------
def staff_required(user):
    return user.is_staff or user.is_superuser


@method_decorator([login_required, user_passes_test(staff_required)], name="dispatch")
class StudentListView(View):
    template_name = "student_management/student_list.html"

    def get(self, request):
        students = Student.objects.order_by("last_name", "first_name").only(
            "id", "first_name", "last_name", "enrollment_number"
        )
        return render(request, self.template_name, {"students": students})


@method_decorator([login_required, user_passes_test(staff_required)], name="dispatch")
class ManageCreditView(View):
    template_name = "student_management/manage_credit.html"

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        credit, _ = ManageCreditPoint.objects.get_or_create(student=student)
        form = CreditChangeForm(initial={"action": "increase", "amount": 6})
        return render(request, self.template_name, {
            "student": student,
            "credit": credit,
            "form": form
        })

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        credit, _ = ManageCreditPoint.objects.get_or_create(student=student)
        form = CreditChangeForm(request.POST)

        if form.is_valid():
            action = form.cleaned_data["action"]
            amount = form.cleaned_data["amount"]

            if action == "increase":
                credit.increase(amount=amount)
                messages.success(request, f"{student.full_name} credits increased by {amount}.")
            elif action == "decrease":
                credit.decrease(amount=amount)
                messages.success(request, f"{student.full_name} credits decreased by {amount}.")

            return redirect("student_management:student_list")

        # invalid form -> re-render
        return render(request, self.template_name, {
            "student": student,
            "credit": credit,
            "form": form
        })


# ------------------------------------------------------------
# STUDENT AUTH
# ------------------------------------------------------------
def student_signup(request):
    if request.method == "POST":
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("student_management:student_home")
    else:
        form = StudentSignupForm()
    return render(request, "welcome_page/student_signup.html", {"form": form})


def student_login(request):
    if request.method == "POST":
        form = StudentLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not hasattr(user, "student"):
                return render(request, "student_management/login.html", {
                    "form": form,
                    "error": "This account is not a student."
                })
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect(reverse("student_management:student_dashboard"))
        return render(request, "student_management/login.html", {
            "form": form,
            "error": "Invalid username or password."
        })
    else:
        form = StudentLoginForm()
    return render(request, "student_management/login.html", {"form": form})


def student_logout(request):
    logout(request)
    return redirect("welcome_page:welcome_page")


# ------------------------------------------------------------
# STUDENT HOME + DASHBOARD
# ------------------------------------------------------------
@login_required(login_url="student_management:student_login")
def student_home(request):
    if not hasattr(request.user, "student"):
        return redirect("student_management:student_login")

    student = request.user.student
    has_enrollment = Enrollment.objects.filter(student=student).exists()
    if not has_enrollment:
        return redirect("course_management:student_course_list")

    return render(request, "student_management/home.html", {"has_enrollment": has_enrollment})


@login_required(login_url="student_management:student_login")
def student_dashboard(request):
    if not hasattr(request.user, "student"):
        return redirect("student_management:student_login")

    student = request.user.student

    # Handle dropout case
    if student.status == "dropout":
        return render(request, "student_management/dropout_notice.html", {"student": student})

    # Enrollment and course info
    enrollment = (Enrollment.objects
                  .filter(student=student)
                  .select_related("course", "course__director", "course__director__user")
                  .first())

    if not enrollment:
        messages.info(request, "Please enroll in a course before accessing your dashboard.")
        return redirect("course_management:student_course_list")

    total_required = enrollment.course.total_credits_required if enrollment else 144

    # Lessons from LessonEnrollment
    lesson_enrollments = (LessonEnrollment.objects
                          .filter(student=student)
                          .select_related("lesson"))

    # Get or create credit point record for student
    credit_record, _ = ManageCreditPoint.objects.get_or_create(student=student)
    stored_credits = credit_record.credits

    # Check graduation eligibility and get earned credits
    is_eligible, total_earned_credits, core_complete = enrollment.course.check_graduation_eligibility(student)

    # Update stored credits to match exactly what's been earned through passing lessons
    credit_record.credits = total_earned_credits
    credit_record.save()
    stored_credits = total_earned_credits

    # Check if student has met ALL graduation requirements
    graduation_requirements_met = (
        total_earned_credits >= enrollment.course.total_credits_required and  # Has enough credits
        core_complete  # Has completed all required lessons
    )
    
    # Show graduation message if requirements are met
    if graduation_requirements_met:
        messages.success(
            request,
            f"Congratulations! You have successfully completed and graduated from {enrollment.course.code} - {enrollment.course.name}!!",
            extra_tags="graduation"
        )
    
    if is_eligible:
        messages.success(
            request, 
            f"Congratulations! You have graduated from the {enrollment.course.name}!!"
        )

    # Prepare lists for active and passed lessons (for UI display)
    passed_lessons = []
    active_lessons = []
    
    for le in lesson_enrollments:
        passed, percentage, details = le.lesson.student_passed(student)
        lesson_data = {
            "id": le.lesson.id,
            "title": le.lesson.title,
            "unit_code": le.lesson.unit_code,
            "credits": le.lesson.lesson_credits,
            "progressPct": round(percentage, 1) if details.get('has_grades') else 0,
            "passed": passed,
            "percentage": round(percentage, 1)
        }
        
        # Sort into passed vs active lists (for UI display)
        if passed:
            passed_lessons.append(lesson_data)
        else:
            active_lessons.append(lesson_data)

    # ------------------------------------------------------------
    # UPCOMING ASSIGNMENTS — based on lesson enrollments
    # ------------------------------------------------------------
    now = timezone.now()
    
    # Only show assignments for lessons where student is in a classroom
    upcoming_qs = (
        Assignment.objects
        .filter(lesson__classrooms__roster__student=student)
        # Upcoming means due in the future (strictly not past/now). Ignore release_date constraint
        .filter(due_date__gt=now)
        .select_related("lesson")
        .order_by("due_date", "id")
        .distinct()
    )
    
    # Get IDs of assignments the student has already submitted
    submitted_assignment_ids = set(
        AssignmentSubmission.objects
        .filter(student=student)
        .values_list('assignment_id', flat=True)
    )
    
    # Filter out assignments that have already been submitted
    upcoming_assignments = [
        {
            "title": asn.title,
            "due": (asn.due_date.isoformat() if asn.due_date else None),
            "lesson": asn.lesson.title,
            "lesson_id": asn.lesson.id,
            "assignment_id": asn.id,
            "marks": float(asn.marks) if asn.marks else 0,
            "weightage": float(asn.weightage) if asn.weightage else 0
        }
        for asn in upcoming_qs
        if asn.id not in submitted_assignment_ids  # Only show unsubmitted assignments
    ]

    # ------------------------------------------------------------
    # CORE LESSONS CHECKLIST
    # ------------------------------------------------------------
    core_lessons = []
    if enrollment and enrollment.course:
        # Get all core lessons (is_required=True) for this course
        course_lessons = enrollment.course.course_lessons.filter(is_required=True).select_related('lesson')
        
        # Get student's lesson enrollments for quick lookup
        student_lesson_enrollments = set(
            LessonEnrollment.objects.filter(student=student).values_list('lesson_id', flat=True)
        )
        
        for course_lesson in course_lessons:
            lesson = course_lesson.lesson
            is_enrolled = lesson.id in student_lesson_enrollments
            
            if is_enrolled:
                passed, percentage, details = lesson.student_passed(student)
                status = "completed" if passed else "in_progress"
            else:
                passed = False
                percentage = 0
                status = "not_enrolled"
            
            core_lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "unit_code": lesson.unit_code,
                "order": course_lesson.order,
                "completed": passed,  # True if 50%+ marks
                "percentage": round(percentage, 1),
                "credits": lesson.lesson_credits,
                "status": status,
                "is_enrolled": is_enrolled
            }
            core_lessons.append(core_lesson_data)
        
        # Sort by order
        core_lessons.sort(key=lambda x: x['order'])

    # ------------------------------------------------------------
    # CONTEXT
    # ------------------------------------------------------------
    context_json = {
        "credits": {
            "earned": stored_credits,  # Use the actual stored credits from database
            "required": total_required
        },
        "activeLessons": active_lessons,
        "completedLessons": passed_lessons,  # Lessons with 50%+ are completed
        "upcoming": upcoming_assignments,  # upcoming from enrolled lessons or classroom rosters
        "coreLessons": core_lessons,  # Core lessons checklist
    }

    # Grades section: get all grades for this student
    from classroom_and_grading.models import AssignmentGrade
    grades = AssignmentGrade.objects.filter(student=student).select_related("assignment", "assignment__lesson")
    grades_by_unit = {}
    for g in grades:
        unit = g.assignment.lesson.unit_code
        if unit not in grades_by_unit:
            grades_by_unit[unit] = []
        grades_by_unit[unit].append(g)

    ctx = {
        "student": student,
        "credits_completed": stored_credits,  # Use the actual stored credits from database
        "total_required": total_required,
        "is_graduated": is_eligible,
        "core_complete": core_complete,
        "enrollment": enrollment,
        "context_json": context_json,
        "grades_by_unit": grades_by_unit,
    }

    return render(request, "student_management/dashboard.html", ctx)

