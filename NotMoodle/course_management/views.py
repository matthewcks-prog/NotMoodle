from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, ListView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db.models import Prefetch, Q
from .models import Course, Enrollment, CourseLesson
from .selectors import get_all_courses_ordered_by_name, get_enrolled_course_ids_for_student
from .services import enrol_student_in_course
from .forms import CourseForm, CourseLessonForm
from student_management.models import Student
from lesson_management.models import LessonEnrollment


def is_teacher(user):
    """Return True if the user appears to have a teacher role/profile.

    Falls back to is_staff, but primarily checks for attached teacher profile
    to avoid requiring staff flag for normal teachers.
    """
    return (
        getattr(user, "teacherprofile", None) is not None
        or getattr(user, "teacher_profile", None) is not None
        or getattr(user, "is_staff", False)
    )

@login_required
def student_course_list(request):
    # NEW: Check if student has dropped out
    try:
        student = Student.objects.get(user=request.user)
        if student.status == "dropout":
            return render(request, "student_management/dropout_notice.html", {
                "student": student
            })
    except Student.DoesNotExist:
        pass

    courses = get_all_courses_ordered_by_name()
    enrolled_course_ids = set()
    current_course_id = None

    try:
        student = Student.objects.get(user=request.user)
        enrollments = Enrollment.objects.filter(student=student)
        if enrollments.exists():
            current_course_id = enrollments.first().course_id
            enrolled_course_ids = {current_course_id}
    except Student.DoesNotExist:
        pass

    return render(
        request,
        "course_management/student_course_list.html",
        {
            "courses": courses,
            "enrolled_course_ids": enrolled_course_ids,
            "current_course_id": current_course_id,
        },
    )

@login_required
@user_passes_test(is_teacher)
def teacher_course_list(request):
    courses = get_all_courses_ordered_by_name()
    return render(request, "course_management/teacher_course_list.html", {"courses": courses})


@login_required
def enroll_in_course(request, course_id):
    # Some authenticated users may not have a Student profile (e.g., teachers).
    student = Student.objects.filter(user=request.user).first()
    if student is None:
        messages.error(request, "You need a student profile to enroll in courses. Please sign up.")
        return redirect("student_management:student_signup")
    
    # NEW: Check if student has dropped out
    if student.status == "dropout":
        return render(request, "student_management/dropout_notice.html", {
            "student": student
        })
    
    existing = Enrollment.objects.filter(student=student).select_related("course").first()
    if existing and existing.course_id != course_id:
        if request.GET.get("confirm") == "yes":
            # Clear all lesson enrollments when switching courses
            LessonEnrollment.objects.filter(student=student).delete()
            existing.delete()
            enrollment, _ = enrol_student_in_course(request, student, course_id)
            # Silent success; redirect straight to dashboard
            return redirect("student_management:student_dashboard")
        # No flash messages; rely on inline confirm on the page
        return redirect(f"{reverse_lazy('course_management:enroll_in_course', kwargs={'course_id': course_id})}?confirm=yes")
    enrollment, created = enrol_student_in_course(request, student, course_id)
    # Silent success; redirect to dashboard
    return redirect("student_management:student_dashboard")


@login_required
def enroll_success(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    student = Student.objects.filter(user=request.user).first()
    if student is None:
        messages.error(request, "You need a student profile to view enrollment details. Please sign up.")
        return redirect("student_management:student_signup")
    credits_completed = getattr(getattr(student, "credit", None), "credits", 0) or 0
    return render(
        request,
        "course_management/enroll_success.html",
        {
            "course": course,
            "credits_completed": credits_completed,
        },
    )


@login_required
@user_passes_test(is_teacher)
def manage_enrollments(request, course_id):
    course = get_object_or_404(Course, pk=course_id, status="active")
    students = Student.objects.all()
    enrolled_student_ids = set(
        Enrollment.objects.filter(course=course).values_list("student_id", flat=True)
    )

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        student = get_object_or_404(Student, pk=student_id)

        Enrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={"enrolled_by": "teacher"},
        )
        messages.success(request, f"{student.full_name()} enrolled in {course.name} by teacher.")
        return redirect("course_management:manage_enrollments", course_id=course.id)

    return render(
        request,
        "course_management/manage_enrollments.html",
        {"course": course, "students": students, "enrolled_student_ids": enrolled_student_ids},
    )


# Course Management Views for Teachers
@method_decorator([login_required, user_passes_test(is_teacher)], name="dispatch")
class CourseCreateView(CreateView):
    model = Course
    form_class = CourseForm
    template_name = "course_management/course_form.html"
    success_url = reverse_lazy("teacher_courses:teacher_course_list")
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass request to the form so it can set default director
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        # If director_name is typed, use it; else default to creating teacher's name
        typed_name = form.cleaned_data.get("director_name")
        if typed_name:
            form.instance.director_name = typed_name
        else:
            profile = (
                getattr(self.request.user, "teacherprofile", None)
                or getattr(self.request.user, "teacher_profile", None)
            )
            if profile:
                form.instance.director_name = profile.get_full_name()
        response = super().form_valid(form)
        # Save core units (CourseLesson rows)
        lessons = form.cleaned_data.get("core_units") or []
        CourseLesson.objects.filter(course=self.object).delete()
        for order, lesson in enumerate(lessons):
            CourseLesson.objects.create(course=self.object, lesson=lesson, order=order, is_required=True)
        messages.success(self.request, f"Course '{form.instance.name}' created successfully.")
        return response

@method_decorator([login_required, user_passes_test(is_teacher)], name="dispatch")
class CourseUpdateView(UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "course_management/course_form.html"
    success_url = reverse_lazy("teacher_courses:teacher_course_list")
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        # Just save the typed director_name (or keep existing if not changed)
        response = super().form_valid(form)
        lessons = form.cleaned_data.get("core_units") or []
        CourseLesson.objects.filter(course=self.object).delete()
        for order, lesson in enumerate(lessons):
            CourseLesson.objects.create(course=self.object, lesson=lesson, order=order, is_required=True)
        messages.success(self.request, f"Course '{form.instance.name}' updated successfully.")
        return response

@method_decorator([login_required, user_passes_test(is_teacher)], name="dispatch")
class CourseListView(ListView):
    model = Course
    template_name = "course_management/teacher_course_list.html"
    context_object_name = "courses"
    paginate_by = 20
    
    def get_queryset(self):
        qs = get_all_courses_ordered_by_name()
        q = self.request.GET.get("q") or ""
        status = self.request.GET.get("status") or ""
        
        if q:
            qs = qs.filter(
                Q(code__icontains=q) | Q(name__icontains=q) | Q(description__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        return ctx


@login_required
@user_passes_test(is_teacher)
def enrollment_management(request):
    """View all courses and manage student enrollments"""
    courses = get_all_courses_ordered_by_name()
    students = Student.objects.all().order_by("last_name", "first_name")
    
    # Get enrollment data for each course
    course_enrollments = {}
    for course in courses:
        enrolled_students = Enrollment.objects.filter(course=course).select_related("student")
        course_enrollments[course.id] = {
            "enrolled_students": enrolled_students,
            "enrolled_count": enrolled_students.count(),
            "enrolled_student_ids": set(enrolled_students.values_list("student_id", flat=True))
        }
    
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        student_id = request.POST.get("student_id")
        action = request.POST.get("action")  # "enroll" or "unenroll"
        
        if course_id and student_id and action:
            course = get_object_or_404(Course, pk=course_id)
            student = get_object_or_404(Student, pk=student_id)
            
            if action == "enroll":
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                    defaults={"enrolled_by": "teacher"}
                )
                if created:
                    messages.success(request, f"{student.full_name()} enrolled in {course.name}")
                else:
                    messages.info(request, f"{student.full_name()} is already enrolled in {course.name}")
            elif action == "unenroll":
                enrollment = Enrollment.objects.filter(student=student, course=course).first()
                if enrollment:
                    # Clean up lesson enrollments for lessons in this course
                    from lesson_management.models import LessonEnrollment
                    course_lessons = CourseLesson.objects.filter(course=course)
                    lesson_ids = [cl.lesson.id for cl in course_lessons]
                    LessonEnrollment.objects.filter(student=student, lesson_id__in=lesson_ids).delete()
                    
                    enrollment.delete()
                    messages.success(request, f"{student.full_name()} unenrolled from {course.name}")
                else:
                    messages.info(request, f"{student.full_name()} is not enrolled in {course.name}")
            
            return redirect("teacher_courses:enrollment_management")
    
    return render(request, "course_management/enrollment_management.html", {
        "courses": courses,
        "students": students,
        "course_enrollments": course_enrollments
    })
