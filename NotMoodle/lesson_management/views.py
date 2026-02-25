# lesson_management/views.py
"""
Assignment Workflow System
===========================

This module handles the complete assignment lifecycle:

1. CREATION (Teacher):
   - Teachers create/edit lessons with assignments via LessonCreateView/LessonUpdateView
   - Assignments are added using inline formsets with validation (weightage ≤ 100%)
   - Teachers receive detailed feedback on assignments added/updated/deleted

2. CLASSROOM ENROLLMENT:
   - Teachers create classrooms linking courses and lessons
   - Teachers enroll students in classrooms via ClassroomAddStudentsForm
   - Students are automatically enrolled in the lesson when added to classroom

3. VIEWING (Student):
   - Students view assignments in lesson_detail view ONLY if enrolled in a classroom
   - Assignments display: title, due date, marks, weightage, description, files
   - Students can download assignment PDFs and submit their work

4. SUBMISSION (Student):
   - Students submit assignments via submit_assignment view
   - One submission per assignment (no resubmissions)
   - Submissions are visible to teachers in classroom detail view

5. GRADING (Teacher):
   - Teachers grade submissions in ClassroomDetailView (classroom_and_grading app)
   - Each submission shows: student name, submitted file, grade input, feedback input
   - Grades are saved to AssignmentGrade model with grader reference
   - Students see grades in lesson_detail view immediately after grading
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django import forms
from .models import Lesson, ReadingList, ReadingListProgress, VideoProgress, Assignment
from .forms import LessonForm, AssignmentSubmissionForm
from student_management.models import ManageCreditPoint
from .models import LessonEnrollment, AssignmentSubmission
from student_management.models import Student
from django.contrib import messages
from django.db.models import Exists, OuterRef
from django.http import FileResponse, Http404
from classroom_and_grading.models import ClassroomStudent
from django.utils import timezone

def is_teacher(user):
    return hasattr(user, "teacherprofile") or hasattr(user, "teacher_profile")

class TeacherOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return is_teacher(self.request.user)

class LessonListView(LoginRequiredMixin, TeacherOnlyMixin, ListView):
    model = Lesson
    template_name = "lessons/lesson_list.html"
    context_object_name = "lessons"
    paginate_by = 10
    login_url = reverse_lazy("teachersManagement:teacher_login")

    def get_queryset(self):
        qs = (
            Lesson.objects
            .select_related("lesson_designer")      # TeacherProfile
            .prefetch_related("prerequisites", "assignments")
            .annotate(prereq_cnt=Count("prerequisites", distinct=True))
        )
        q = self.request.GET.get("q") or ""
        status = self.request.GET.get("status") or ""
        if q:
            qs = qs.filter(
                Q(unit_code__icontains=q) |
                Q(title__icontains=q) |
                Q(description__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("unit_code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        return ctx

class LessonCreateView(LoginRequiredMixin, TeacherOnlyMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = "lessons/lesson_form.html"
    success_url = reverse_lazy("teachersManagement:lessons:list")
    login_url = reverse_lazy("teachersManagement:teacher_login")

    def get_initial(self):
        initial = super().get_initial()
        # Set the lesson_designer to the logged-in teacher by default
        profile = getattr(self.request.user, "teacherprofile",
                 getattr(self.request.user, "teacher_profile", None))
        if profile:
            initial['lesson_designer'] = profile
        return initial

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        from django.forms import inlineformset_factory
        ReadingFormSet = inlineformset_factory(
            Lesson,
            ReadingList,
            fields=["title", "url", "description", "order"],
            extra=0,
            can_delete=True,
        )
        AssignmentFormSet = inlineformset_factory(
            Lesson,
            Assignment,
            fields=["title", "release_date", "due_date", "marks", "weightage", "description", "pdf"],
            extra=0,
            can_delete=True,
            widgets={
                "release_date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
                "due_date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            }
        )
        if form.is_valid():
            # attach designer and save lesson first
            profile = getattr(self.request.user, "teacherprofile",
                     getattr(self.request.user, "teacher_profile", None))
            form.instance.lesson_designer = profile
            self.object = form.save()
            reading_formset = ReadingFormSet(self.request.POST, instance=self.object)
            assignment_formset = AssignmentFormSet(self.request.POST, self.request.FILES, instance=self.object)
            if reading_formset.is_valid() and assignment_formset.is_valid():
                # Validate total weightage before saving
                from decimal import Decimal
                total_weightage = Decimal('0')
                assignments_to_save = 0
                for assignment_form in assignment_formset:
                    if assignment_form.cleaned_data and not assignment_form.cleaned_data.get('DELETE', False):
                        weightage = assignment_form.cleaned_data.get('weightage', 0)
                        if weightage:
                            total_weightage += Decimal(str(weightage))
                        assignments_to_save += 1
                
                if total_weightage > 100:
                    messages.error(request, f"Total weightage cannot exceed 100%. Current total: {total_weightage}%")
                    context = self.get_context_data(form=form, reading_formset=reading_formset, assignment_formset=assignment_formset)
                    return render(request, self.template_name, context)
                
                reading_formset.save()
                saved_assignments = assignment_formset.save()
                
                # Provide detailed feedback
                if assignments_to_save > 0:
                    messages.success(request, f"Lesson saved successfully with {assignments_to_save} assignment(s).")
                else:
                    messages.success(request, "Lesson saved successfully. No assignments were added.")
                
                return redirect(self.get_success_url())
            # If invalid, re-render with errors
            context = self.get_context_data(form=form, reading_formset=reading_formset, assignment_formset=assignment_formset)
            return render(request, self.template_name, context)
        # Form invalid
        context = self.get_context_data(form=form)
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        # For CreateView, we need to set self.object = None before calling super()
        if not hasattr(self, 'object'):
            self.object = None
        
        context = super().get_context_data(**kwargs)
        from django.forms import inlineformset_factory
        ReadingFormSet = inlineformset_factory(
            Lesson,
            ReadingList,
            fields=["title", "url", "description", "order"],
            extra=0,
            can_delete=True,
        )
        AssignmentFormSet = inlineformset_factory(
            Lesson,
            Assignment,
            fields=["title", "release_date", "due_date", "marks", "weightage", "description", "pdf"],
            extra=0,  # No blank forms by default - use "Add assignment" button
            can_delete=True,
            widgets={
                "release_date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
                "due_date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            }
        )
        # For create, we provide an empty instance to render blank rows
        if self.request.method == "POST":
            context["reading_formset"] = kwargs.get("reading_formset") or ReadingFormSet(self.request.POST, instance=self.object if self.object else Lesson())
            context["assignment_formset"] = kwargs.get("assignment_formset") or AssignmentFormSet(self.request.POST, self.request.FILES, instance=self.object if self.object else Lesson())
        else:
            context["reading_formset"] = ReadingFormSet(instance=Lesson())
            context["assignment_formset"] = AssignmentFormSet(instance=Lesson())
        # Keep old "formset" for backward compatibility with template
        context["formset"] = context["reading_formset"]
        return context

class LessonUpdateView(LoginRequiredMixin, TeacherOnlyMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "lessons/lesson_form.html"
    success_url = reverse_lazy("teachersManagement:lessons:list")
    login_url = reverse_lazy("teachersManagement:teacher_login")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        from django.forms import inlineformset_factory
        
        ReadingFormSet = inlineformset_factory(
            Lesson,
            ReadingList,
            fields=["title", "url", "description", "order"],
            extra=0,
            can_delete=True,
        )
        
        # Custom form for datetime handling
        class AssignmentInlineForm(forms.ModelForm):
            release_date = forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
                input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
                required=True
            )
            due_date = forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
                input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
                required=True
            )
            
            class Meta:
                model = Assignment
                fields = ["title", "release_date", "due_date", "marks", "weightage", "description", "pdf"]
        
        AssignmentFormSet = inlineformset_factory(
            Lesson,
            Assignment,
            form=AssignmentInlineForm,
            extra=0,
            can_delete=True,
        )
        
        reading_formset = ReadingFormSet(self.request.POST, instance=self.object)
        assignment_formset = AssignmentFormSet(self.request.POST, self.request.FILES, instance=self.object)
        
        # Debug logging
        if not assignment_formset.is_valid():
            print("DEBUG: Assignment formset errors:", assignment_formset.errors)
            print("DEBUG: Assignment formset non-form errors:", assignment_formset.non_form_errors())
        
        if form.is_valid() and reading_formset.is_valid() and assignment_formset.is_valid():
            return self.forms_valid(form, reading_formset, assignment_formset)
        return self.forms_invalid(form, reading_formset, assignment_formset)

    def forms_valid(self, form, reading_formset, assignment_formset):
        from decimal import Decimal
        from django.core.exceptions import ValidationError
        
        # Count assignments before saving
        assignments_to_add = 0
        assignments_to_update = 0
        assignments_to_delete = 0
        total_weightage = Decimal('0')
        
        for assignment_form in assignment_formset:
            if assignment_form.cleaned_data:
                if assignment_form.cleaned_data.get('DELETE', False):
                    assignments_to_delete += 1
                elif assignment_form.instance.pk:
                    assignments_to_update += 1
                    weightage = assignment_form.cleaned_data.get('weightage', 0)
                    if weightage:
                        total_weightage += Decimal(str(weightage))
                else:
                    assignments_to_add += 1
                    weightage = assignment_form.cleaned_data.get('weightage', 0)
                    if weightage:
                        total_weightage += Decimal(str(weightage))
        
        if total_weightage > 100:
            messages.error(self.request, f"Total weightage cannot exceed 100%. Current total: {total_weightage}%")
            return self.forms_invalid(form, reading_formset, assignment_formset)
        
        profile = getattr(self.request.user, "teacherprofile",
                 getattr(self.request.user, "teacher_profile", None))
        form.instance.lesson_designer = profile
        self.object = form.save()
        reading_formset.instance = self.object
        reading_formset.save()
        assignment_formset.instance = self.object
        assignment_formset.save()
        
        # Provide detailed feedback
        feedback_parts = ["Lesson saved successfully."]
        if assignments_to_add > 0:
            feedback_parts.append(f"{assignments_to_add} assignment(s) added.")
        if assignments_to_update > 0:
            feedback_parts.append(f"{assignments_to_update} assignment(s) updated.")
        if assignments_to_delete > 0:
            feedback_parts.append(f"{assignments_to_delete} assignment(s) deleted.")
        if assignments_to_add == 0 and assignments_to_update == 0 and assignments_to_delete == 0:
            feedback_parts.append("No assignment changes.")
        
        messages.success(self.request, " ".join(feedback_parts))
        return redirect(self.get_success_url())

    def forms_invalid(self, form, reading_formset, assignment_formset):
        # Add detailed error messages
        if form.errors:
            messages.error(self.request, f"Lesson form errors: {form.errors}")
        
        if reading_formset.errors:
            for i, error_dict in enumerate(reading_formset.errors):
                if error_dict:
                    messages.error(self.request, f"Reading item {i+1} errors: {error_dict}")
        
        if assignment_formset.errors:
            for i, error_dict in enumerate(assignment_formset.errors):
                if error_dict:
                    messages.error(self.request, f"Assignment {i+1} errors: {error_dict}")
        
        # Also check for non-form errors
        if reading_formset.non_form_errors():
            messages.error(self.request, f"Reading list errors: {reading_formset.non_form_errors()}")
        
        if assignment_formset.non_form_errors():
            messages.error(self.request, f"Assignment list errors: {assignment_formset.non_form_errors()}")
        
        context = self.get_context_data(form=form, reading_formset=reading_formset, assignment_formset=assignment_formset)
        return render(self.request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.forms import inlineformset_factory
        
        ReadingFormSet = inlineformset_factory(
            Lesson,
            ReadingList,
            fields=["title", "url", "description", "order"],
            extra=1,
            can_delete=True,
        )
        
        # Custom form for datetime handling
        class AssignmentInlineForm(forms.ModelForm):
            release_date = forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
                input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
                required=True
            )
            due_date = forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
                input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
                required=True
            )
            
            class Meta:
                model = Assignment
                fields = ["title", "release_date", "due_date", "marks", "weightage", "description", "pdf"]
        
        AssignmentFormSet = inlineformset_factory(
            Lesson,
            Assignment,
            form=AssignmentInlineForm,
            extra=1,
            can_delete=True,
        )
        
        if self.request.method == "POST":
            context["reading_formset"] = kwargs.get("reading_formset") or ReadingFormSet(self.request.POST, instance=self.object)
            context["assignment_formset"] = kwargs.get("assignment_formset") or AssignmentFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context["reading_formset"] = ReadingFormSet(instance=self.object)
            context["assignment_formset"] = AssignmentFormSet(instance=self.object)
        # Keep old "formset" for backward compatibility with template
        context["formset"] = context["reading_formset"]
        return context

# ---- Student-facing lessons list (no teacher check) ----
@login_required
def student_lessons_list(request):
    # NEW: Check if student has dropped out
    if hasattr(request.user, "student") and request.user.student.status == "dropout":
        return render(request, "student_management/dropout_notice.html", {
            "student": request.user.student
        })
    
    lessons = (
        Lesson.objects
        .filter(status="published")
        .prefetch_related("prerequisites")  # Add prefetch for prerequisites
        .order_by("unit_code")
    )
    q = request.GET.get("q") or ""
    if q:
        lessons = lessons.filter(
            Q(unit_code__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )
    enrolled_ids = set()
    lesson_stats = {}  # Dictionary to store marks and pass status for each lesson
    lesson_prerequisites = {}  # Dictionary to store prerequisite info for each lesson
    
    if hasattr(request.user, "student"):
        student = request.user.student
        enrolled_ids = set(
            LessonEnrollment.objects.filter(student=student)
            .values_list("lesson_id", flat=True)
        )
        
        # Calculate marks and pass status for enrolled lessons
        # Also check prerequisite status for all lessons
        for lesson in lessons:
            if lesson.id in enrolled_ids:
                passed, percentage, details = lesson.student_passed(student)
                lesson_stats[lesson.id] = {
                    'percentage': round(percentage, 1),
                    'passed': passed,
                    'has_grades': details.get('graded_assignments', 0) > 0,
                    'total_assignments': details.get('total_assignments', 0)
                }
            
            # Check prerequisites for all lessons
            prerequisites = lesson.prerequisites.all()
            if prerequisites.exists():
                prereq_info = []
                for prereq in prerequisites:
                    prereq_passed, _, _ = prereq.student_passed(student)
                    prereq_info.append({
                        'lesson': prereq,
                        'passed': prereq_passed
                    })
                lesson_prerequisites[lesson.id] = prereq_info
    
    return render(request, "lessons/lesson_list_student.html", {
        "lessons": lessons, 
        "q": q, 
        "enrolled_ids": enrolled_ids,
        "lesson_stats": lesson_stats,
        "lesson_prerequisites": lesson_prerequisites
    })


@login_required(login_url="student_management:student_login")
def enroll_in_lesson(request, lesson_id):
    if not hasattr(request.user, "student"):
        return redirect("student_management:student_login")
    lesson = get_object_or_404(Lesson, pk=lesson_id, status="published")
    student = request.user.student

    # NEW: Check if student has dropped out
    if student.status == "dropout":
        return render(request, "student_management/dropout_notice.html", {
            "student": student
        })

    # Electives policy: students may enroll in any published lesson (regardless of course membership).
    # Graduation remains governed by completion of core lessons for the student's course elsewhere.

    # Enforce prerequisites: student must have PASSED all prerequisite lessons (not just enrolled)
    prerequisites = lesson.prerequisites.all()
    if prerequisites.exists():
        failed_prereqs = []
        for prereq in prerequisites:
            passed, _, _ = prereq.student_passed(student)
            if not passed:
                failed_prereqs.append(prereq.title)
        
        if failed_prereqs:
            messages.error(
                request, 
                f"You must pass the following prerequisite lesson(s) before enrolling: {', '.join(failed_prereqs)}"
            )
            return redirect("lessons:student_list")

    enrollment, created = LessonEnrollment.objects.get_or_create(student=student, lesson=lesson)
    if created:
        # Credits are now awarded when student passes (>50%), not on enrollment
        messages.success(request, f"Successfully enrolled in {lesson.title}.")
    else:
        messages.info(request, f"You are already enrolled in {lesson.title}.")

    return redirect("lessons:student_list")


@login_required(login_url="student_management:student_login")
def lesson_detail(request, lesson_id):
    """Detailed lesson view for students"""
    if not hasattr(request.user, "student"):
        return redirect("student_management:student_login")

    lesson = get_object_or_404(Lesson, pk=lesson_id, status="published")
    student = request.user.student

    # Teacher grading POST
    if is_teacher(request.user) and request.method == "POST" and request.POST.get("grade_assignment_id"):
        from classroom_and_grading.models import AssignmentGrade
        assignment_id = int(request.POST["grade_assignment_id"])
        marks_awarded = request.POST.get("marks_awarded")
        feedback = request.POST.get("feedback", "")
        assignment = get_object_or_404(Assignment, pk=assignment_id, lesson=lesson)
        # Find the student submission for this assignment
        submission = AssignmentSubmission.objects.filter(assignment=assignment, assignment__lesson=lesson, student=student).first()
        if submission:
            grade, _ = AssignmentGrade.objects.update_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    "marks_awarded": marks_awarded,
                    "feedback": feedback,
                    "graded_by": request.user.teacherprofile if hasattr(request.user, "teacherprofile") else request.user.teacher_profile,
                }
            )

    # Check if student is enrolled
    is_enrolled = LessonEnrollment.objects.filter(student=student, lesson=lesson).exists()

    # classroom_enrol (already in your code) ...
    classroom_enrol = None
    qs = (ClassroomStudent.objects
            .select_related("classroom",
                            "classroom__teacher",
                            "classroom__teacher__user",
                            "classroom__course",
                            "classroom__lesson")
            .filter(student=student, classroom__lesson=lesson))
    now = timezone.now()
    row = (qs.filter(classroom__start_date__lte=now, classroom__end_date__gte=now).first()
           or qs.order_by("-classroom__start_date").first())
    classroom_enrol = row.classroom if row else None

    # --- NEW: assignments + student's submissions + grades -------------------
    assignments = list(Assignment.objects.filter(lesson=lesson).order_by("id"))

    # map: assignment_id -> AssignmentSubmission object (if exists)
    submission_map = {
        sub.assignment_id: sub
        for sub in AssignmentSubmission.objects
                  .filter(student=student, assignment__in=assignments)
                  .select_related("assignment")
    }

    # map: assignment_id -> AssignmentGrade object (if exists)
    from classroom_and_grading.models import AssignmentGrade
    grade_map = {
        g.assignment_id: g
        for g in AssignmentGrade.objects.filter(student=student, assignment__in=assignments)
    }

    # reading/video/progress/prereqs (your existing code) ...
    reading_list = list(lesson.reading_list.all())
    reading_progress_map = {rp.reading_id: rp.done for rp in ReadingListProgress.objects.filter(student=student, reading__lesson=lesson)}
    completed_reading_ids = {rid for rid, done in reading_progress_map.items() if done}
    video_progress = VideoProgress.objects.filter(student=student, lesson=lesson).first()
    video_watched = bool(video_progress and video_progress.watched)
    prerequisites = lesson.prerequisites.all()

    # Check which prerequisites are PASSED (not just enrolled)
    passed_prerequisites = []
    failed_prerequisites = []
    if prerequisites:
        for prereq in prerequisites:
            prereq_passed, _, _ = prereq.student_passed(student)
            if prereq_passed:
                passed_prerequisites.append(prereq)
            else:
                failed_prerequisites.append(prereq)

    total_items = len(reading_list) + (1 if lesson.youtube_link else 0)
    completed_items = sum(1 for r in reading_list if reading_progress_map.get(r.id)) + (1 if video_watched and lesson.youtube_link else 0)
    progress_pct = int((completed_items / total_items) * 100) if total_items else 0

    # Calculate pass/fail status
    passed, percentage, details = lesson.student_passed(student)
    
    context = {
        'lesson': lesson,
        'is_enrolled': is_enrolled,
        'classroom_enrol': classroom_enrol,
        'assignments': assignments,
        'submission_map': submission_map,
        'grade_map': grade_map,
        'reading_list': reading_list,
        'completed_reading_ids': list(completed_reading_ids),
        'video_watched': video_watched,
        'progress_pct': progress_pct,
        'prerequisites': prerequisites,
        'completed_prerequisites': passed_prerequisites,
        'missing_prerequisites': failed_prerequisites,
        'student': student,
        'is_teacher': is_teacher(request.user),
        'passed': passed,
        'overall_percentage': round(percentage, 1),
        'has_grades': details.get('graded_assignments', 0) > 0,
        'total_assignments_count': details.get('total_assignments', 0),
    }
    return render(request, "lessons/lesson_detail.html", context)


@login_required(login_url="student_management:student_login")
def toggle_reading_progress(request, lesson_id, reading_id):
    if request.method != "POST":
        return redirect("lessons:detail", lesson_id=lesson_id)
    if not hasattr(request.user, "student"):
        return redirect("student_management:student_login")
    lesson = get_object_or_404(Lesson, pk=lesson_id, status="published")
    reading = get_object_or_404(ReadingList, pk=reading_id, lesson=lesson)
    student = request.user.student
    # must be enrolled
    if not LessonEnrollment.objects.filter(student=student, lesson=lesson).exists():
        messages.error(request, "You must enroll to track progress.")
        return redirect("lessons:detail", lesson_id=lesson.id)
    obj, _ = ReadingListProgress.objects.get_or_create(student=student, reading=reading)
    obj.done = not obj.done
    obj.save()
    return redirect("lessons:detail", lesson_id=lesson.id)


@login_required(login_url="student_management:student_login")
def toggle_video_progress(request, lesson_id):
    if request.method != "POST":
        return redirect("lessons:detail", lesson_id=lesson_id)
    if not hasattr(request.user, "student"):
        return redirect("student_management:student_login")
    lesson = get_object_or_404(Lesson, pk=lesson_id, status="published")
    student = request.user.student
    if not LessonEnrollment.objects.filter(student=student, lesson=lesson).exists():
        messages.error(request, "You must enroll to track progress.")
        return redirect("lessons:detail", lesson_id=lesson.id)
    obj, _ = VideoProgress.objects.get_or_create(student=student, lesson=lesson)
    obj.watched = not obj.watched
    obj.save()
    return redirect("lessons:detail", lesson_id=lesson.id)

@login_required
def download_assignment_pdf(request, pk):
    assignment = get_object_or_404(Assignment.objects.select_related("lesson"), pk=pk)

    # Authorization: allow if teacher of a classroom for this lesson OR
    # student who is enrolled in a classroom for this lesson
    lesson = assignment.lesson
    if is_teacher(request.user):
        teacher_profile = getattr(request.user, "teacherprofile", getattr(request.user, "teacher_profile", None))
        is_authorized = ClassroomStudent.objects.filter(
            classroom__lesson=lesson,
            classroom__teacher=teacher_profile,
        ).exists() or lesson.lesson_designer_id == getattr(teacher_profile, "id", None)
    else:
        if not hasattr(request.user, "student"):
            is_authorized = False
        else:
            is_authorized = ClassroomStudent.objects.filter(
                classroom__lesson=lesson,
                student=request.user.student,
            ).exists()

    if not is_authorized:
        raise Http404("Not authorized to access this assignment PDF.")

    if not assignment.pdf:
        raise Http404("No PDF attached.")
    return FileResponse(
        assignment.pdf.open("rb"),
        as_attachment=True,
        filename=assignment.pdf_filename
    )

@login_required
def submit_assignment(request, lesson_id, assignment_id):
    if request.method != "POST":
        return redirect("lessons:detail", lesson_id=lesson_id)

    assignment = get_object_or_404(Assignment, pk=assignment_id, lesson_id=lesson_id)
    # Authorization: must be a student and enrolled in a classroom for this lesson
    if not hasattr(request.user, "student"):
        messages.error(request, "You must be logged in as a student to submit.")
        return redirect("lessons:detail", lesson_id=lesson_id)
    student = request.user.student
    if not ClassroomStudent.objects.filter(classroom__lesson_id=lesson_id, student=student).exists():
        messages.error(request, "You are not enrolled in a classroom for this lesson.")
        return redirect("lessons:detail", lesson_id=lesson_id)

    # hard block: one submission only
    if AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists():
        messages.error(request, "You have already submitted this assignment.")
        return redirect("lessons:detail", lesson_id=lesson_id)

    pdf = request.FILES.get("pdf")
    if not pdf:
        messages.error(request, "Please upload a PDF.")
        return redirect("lessons:detail", lesson_id=lesson_id)

    AssignmentSubmission.objects.create(
        assignment=assignment,
        student=student,
        pdf=pdf,
    )
    messages.success(request, "Submission uploaded.")
    return redirect("lessons:detail", lesson_id=lesson_id)


# ---- Teacher grading screen per lesson ----
@login_required
def teacher_grade_lesson(request, lesson_id):
    if not is_teacher(request.user):
        return redirect("teachersManagement:teacher_login")

    lesson = get_object_or_404(Lesson, pk=lesson_id)
    teacher_profile = getattr(request.user, "teacherprofile", getattr(request.user, "teacher_profile", None))

    # Ensure this teacher is associated with a classroom for this lesson or is the designer
    is_linked_teacher = ClassroomStudent.objects.filter(classroom__lesson=lesson, classroom__teacher=teacher_profile).exists() or lesson.lesson_designer_id == getattr(teacher_profile, "id", None)
    if not is_linked_teacher:
        messages.error(request, "You are not authorized to grade this lesson.")
        return redirect("teachersManagement:lessons:list")

    from classroom_and_grading.models import AssignmentGrade

    if request.method == "POST" and request.POST.get("grade_assignment_id"):
        try:
            assignment_id = int(request.POST["grade_assignment_id"])
            student_id = int(request.POST["grade_student_id"])
        except (KeyError, ValueError):
            messages.error(request, "Invalid grading request.")
            return redirect("lessons:teacher_grade_lesson", lesson_id=lesson.id)

        marks_awarded = request.POST.get("marks_awarded")
        feedback = request.POST.get("feedback", "")

        assignment = get_object_or_404(Assignment, pk=assignment_id, lesson=lesson)
        student = get_object_or_404(Student, pk=student_id)

        # Only grade if the student has submitted
        submitted = AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists()
        if not submitted:
            messages.error(request, "No submission to grade for this student.")
        else:
            AssignmentGrade.objects.update_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    "marks_awarded": marks_awarded,
                    "feedback": feedback,
                    "graded_by": teacher_profile,
                },
            )
            messages.success(request, "Grade saved.")

        return redirect("lessons:teacher_grade_lesson", lesson_id=lesson.id)

    # Build context of submissions grouped by assignment
    assignments = list(Assignment.objects.filter(lesson=lesson).order_by("due_date", "id"))
    submissions = (
        AssignmentSubmission.objects
        .filter(assignment__in=assignments)
        .select_related("assignment", "student", "student__user")
        .order_by("assignment_id", "-submitted_at")
    )

    # map existing grades
    from classroom_and_grading.models import AssignmentGrade
    grade_map = {
        (g.assignment_id, g.student_id): g
        for g in AssignmentGrade.objects.filter(assignment__in=assignments)
    }

    return render(request, "lessons/teacher_grade_lesson.html", {
        "lesson": lesson,
        "assignments": assignments,
        "submissions": submissions,
        "grade_map": grade_map,
    })
