# classrooms/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, DetailView, ListView
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.db import transaction
from django.views.generic.edit import UpdateView

from .models import Classroom, ClassroomStudent, TeacherProfile, AssignmentGrade, Assignment
from .forms import ClassroomCreateForm, ClassroomAddStudentsForm, AssignmentForm, AttachmentForm
from lesson_management.models import AssignmentAttachment
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

class ClassroomCreateView(LoginRequiredMixin, CreateView):
    model = Classroom
    form_class = ClassroomCreateForm
    template_name = "classroom_and_grading/classroom_form.html"  # your path

    def form_valid(self, form):
        # don't commit yet; we must attach teacher first
        obj = form.save(commit=False)

        try:
            # adjust if your TeacherProfile links differently
            obj.teacher = TeacherProfile.objects.get(user=self.request.user)
        except TeacherProfile.DoesNotExist:
            messages.error(self.request, "You must be a teacher to create a classroom.")
            return redirect("classroom_and_grading:classroom_list")

        # Check for duplicate classroom (unique constraint)
        from django.db import IntegrityError
        try:
            obj.save()
            messages.success(self.request, "Classroom created.")
            return redirect("classroom_and_grading:classroom_detail", pk=obj.pk)
        except IntegrityError as e:
            if 'uniq_classroom_slot_per_teacher' in str(e):
                messages.error(self.request, 
                    f"A classroom for {obj.course.name} - {obj.lesson.title} "
                    f"starting on {obj.start_date.strftime('%Y-%m-%d %H:%M')} "
                    f"already exists. Please choose a different start time or lesson.")
            else:
                messages.error(self.request, f"Error creating classroom: {str(e)}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("classroom_and_grading:classroom_detail", args=[self.object.pk])


class ClassroomDetailView(DetailView):
    model = Classroom
    template_name = "classroom_and_grading/classroom_detail.html"
    context_object_name = "classroom"

    def get_queryset(self):
        return (
            Classroom.objects
            .select_related("course", "lesson", "teacher")
            .prefetch_related("roster__student")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        classroom = self.object

        # Get assignments for this lesson (shared across classrooms)
        ctx["assignments"] = (
            Assignment.objects
            .filter(lesson=classroom.lesson)
            .prefetch_related("attachments")  # Don't prefetch ALL submissions yet
            .order_by("due_date")
        )
        
        # Get roster for THIS classroom only
        ctx["roster"] = (
            classroom.roster.select_related("student", "student__user")
            .order_by("student__last_name", "student__first_name")
        )

        ctx["add_form"] = ClassroomAddStudentsForm(classroom)
        
        # CRITICAL: Only get students enrolled in THIS classroom
        roster_student_ids = [r.student_id for r in ctx["roster"]]
        
        if not roster_student_ids:
            # No students in this classroom yet
            return ctx
        
        # Get assignment IDs
        assignment_ids = [a.id for a in ctx["assignments"]]
        
        # Get grades ONLY for students in THIS classroom
        existing_grades = (
            AssignmentGrade.objects
            .filter(
                assignment_id__in=assignment_ids,
                student_id__in=roster_student_ids  # ← CRITICAL: Filter by this classroom's students
            )
            .select_related("assignment", "student")
        )
        grade_map = {(g.assignment_id, g.student_id): g for g in existing_grades}
        
        # Filter submissions to ONLY students in THIS classroom
        from lesson_management.models import AssignmentSubmission
        classroom_submissions = (
            AssignmentSubmission.objects
            .filter(
                assignment_id__in=assignment_ids,
                student_id__in=roster_student_ids  # ← CRITICAL: Only this classroom's students
            )
            .select_related("student", "student__user", "assignment")
            .order_by("assignment_id", "submitted_at")
        )
        
        # Group submissions by assignment
        submission_map = {}
        for sub in classroom_submissions:
            if sub.assignment_id not in submission_map:
                submission_map[sub.assignment_id] = []
            # Attach cached_grade to submission
            sub.cached_grade = grade_map.get((sub.assignment_id, sub.student_id))
            submission_map[sub.assignment_id].append(sub)
        
        # Attach submissions to each assignment (only for THIS classroom's students)
        for a in ctx["assignments"]:
            a.classroom_submissions = submission_map.get(a.id, [])
        
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action")

        if action == "add":
            form = ClassroomAddStudentsForm(self.object, data=request.POST)
            if form.is_valid():
                result = form.save()
                if result["added"]:
                    messages.success(request, f"Added {result['added']} student(s) to this classroom.")
                if result["skipped"]:
                    messages.warning(
                        request,
                        f"Skipped {result['skipped']} student(s) already rostered in a classroom for this lesson."
                    )
            else:
                messages.error(request, "Please select valid students to add.")
            return redirect("classroom_and_grading:classroom_detail", pk=self.object.pk)

        if action == "remove":
            sid = request.POST.get("student_id")
            if sid:
                ClassroomStudent.objects.filter(
                    classroom=self.object, student_id=sid
                ).delete()
                messages.success(request, "Student removed.")
            return redirect("classroom_and_grading:classroom_detail", pk=self.object.pk)

        if action == "grade_submission":
            from .models import AssignmentGrade, TeacherProfile, Assignment
            from student_management.models import Student
            
            try:
                assignment_id = int(request.POST.get("assignment_id"))
                student_id = int(request.POST.get("student_id"))
                marks_awarded_str = request.POST.get("marks_awarded", "").strip()
                feedback = request.POST.get("feedback", "")
                
                assignment = Assignment.objects.get(pk=assignment_id)
                student = Student.objects.get(pk=student_id)
                teacher_profile = TeacherProfile.objects.get(user=request.user)
                
                # Convert empty string to None for nullable field
                marks_awarded = None if not marks_awarded_str else marks_awarded_str
                
                # Validate marks if provided
                if marks_awarded is not None:
                    try:
                        marks_value = float(marks_awarded)
                        if marks_value < 0 or marks_value > float(assignment.marks):
                            messages.error(request, f"Marks must be between 0 and {assignment.marks}")
                            return redirect("classroom_and_grading:classroom_detail", pk=self.object.pk)
                        # Use the validated float value
                        marks_awarded = marks_value
                    except ValueError:
                        messages.error(request, "Invalid marks value. Please enter a number.")
                        return redirect("classroom_and_grading:classroom_detail", pk=self.object.pk)
                
                grade, created = AssignmentGrade.objects.update_or_create(
                    assignment=assignment,
                    student_id=student_id,
                    defaults={
                        "marks_awarded": marks_awarded,
                        "feedback": feedback,
                        "graded_by": teacher_profile,
                    }
                )
                
                # More informative success message
                student_name = student.user.get_full_name() if student.user else f"Student {student_id}"
                if created:
                    messages.success(request, f"Grade saved for {student_name}: {marks_awarded}/{assignment.marks}")
                else:
                    messages.success(request, f"Grade updated for {student_name}: {marks_awarded}/{assignment.marks}")
                    
            except Assignment.DoesNotExist:
                messages.error(request, "Assignment not found.")
            except Student.DoesNotExist:
                messages.error(request, "Student not found.")
            except TeacherProfile.DoesNotExist:
                messages.error(request, "Teacher profile not found.")
            except Exception as e:
                messages.error(request, f"Error saving grade: {str(e)}")
            
            return redirect("classroom_and_grading:classroom_detail", pk=self.object.pk)

        messages.error(request, "Unknown action.")
        return redirect("classroom_and_grading:classroom_detail", pk=self.object.pk)

class ClassroomListView(ListView):
    model = Classroom
    template_name = "classroom_and_grading/classroom_list.html"
    context_object_name = "classrooms"


def assignment_create_for_classroom(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    print("DEBUG: method =", request.method)
    if request.method == "POST":
        print("DEBUG: POST data =", request.POST)
        print("DEBUG: FILES =", request.FILES)
        form = AssignmentForm(request.POST, lesson=classroom.lesson)
        attachment_form = AttachmentForm(request.POST, request.FILES)
        files = request.FILES.getlist("file")  # matches AttachmentForm field name
        print("DEBUG: FILES =>", [f.name for f in files])
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.lesson = classroom.lesson
            assignment.clean()
            assignment.save()

            for f in files:
                AssignmentAttachment.objects.create(assignment=assignment, file=f)

            messages.success(request, "Assignment created successfully.")
            return redirect("classroom_and_grading:classroom_detail", pk=classroom.pk)
        else:
            print("DEBUG: FORM ERRORS =>", form.errors)
    else:
        form = AssignmentForm(lesson=classroom.lesson)
        attachment_form = AttachmentForm()

    return render(
        request,
        "classroom_and_grading/assignment_form.html",
        {"classroom": classroom, "form": form, "attachment_form": attachment_form},
    )

class AssignmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = "classroom_and_grading/assignment_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.classroom = get_object_or_404(Classroom, pk=kwargs["classroom_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Only allow editing assignments tied to this classroom's lesson
        return Assignment.objects.filter(lesson_id=self.classroom.lesson_id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['lesson'] = self.classroom.lesson
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["classroom"] = self.classroom
        ctx["attachment_form"] = AttachmentForm()  # your MultiFileInput (multiple PDFs)
        ctx["existing_attachments"] = self.object.attachments.all().order_by("id")
        return ctx

    def form_valid(self, form):
        # Save assignment fields first
        response = super().form_valid(form)
        # 1) Deletions from checkboxes
        remove_ids = self.request.POST.getlist("remove_attachments")
        if remove_ids:
            self.object.attachments.filter(id__in=remove_ids).delete()
        # 2) New uploads (AttachmentForm has field name "file")
        for f in self.request.FILES.getlist("file"):
            if f:
                self.object.attachments.create(file=f)
        return response

    def get_success_url(self):
        return reverse(
            "classroom_and_grading:classroom_detail", args=[self.classroom.pk]
        )

@login_required
@require_POST
def upload_attachments_for_assignment(request, assignment_id):
    """Add more PDFs to an existing assignment (additive, multiple)."""
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    files = request.FILES.getlist("file")  # matches AttachmentForm field name

    if not files:
        return HttpResponseBadRequest("No files uploaded.")

    made = []
    for f in files:
        # AssignmentAttachment already has FileExtensionValidator(['pdf'])
        att = AssignmentAttachment.objects.create(assignment=assignment, file=f)
        made.append({
            "id": att.id,
            "name": att.filename(),
            "url": att.file.url,
        })
    return JsonResponse({"attachments": made})

@login_required
@require_POST
def delete_attachment(request, att_id):
    """Remove a single PDF from an assignment."""
    att = get_object_or_404(AssignmentAttachment, pk=att_id)
    att.delete()
    return JsonResponse({"ok": True})

@login_required
@require_POST
def delete_assignment_for_classroom(request, pk, assignment_id):
    """Delete an assignment that belongs to this classroom's lesson."""
    classroom = get_object_or_404(Classroom, pk=pk)
    assignment = get_object_or_404(
        Assignment,
        pk=assignment_id,
        lesson_id=classroom.lesson_id,  # safety check
    )
    title = assignment.title
    assignment.delete()  # cascades to attachments/submissions rows
    messages.success(request, f'Assignment "{title}" deleted.')
    return redirect("classroom_and_grading:classroom_detail", pk=classroom.pk)

@login_required
@require_POST
def delete_classroom(request, pk):
    """Delete a classroom and return to the list page."""
    classroom = get_object_or_404(Classroom, pk=pk)

    title = str(classroom.lesson) if classroom.lesson else f"Classroom {classroom.pk}"
    classroom.delete()  # cascades to ClassroomStudent, etc., per your FK settings
    messages.success(request, f'Classroom "{title}" deleted.')
    return redirect("classroom_and_grading:classroom_list")
