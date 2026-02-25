from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
# NEW imports
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import ListView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q
from student_management.models import Student
from classroom_and_grading.models import ClassroomStudent, AssignmentGrade
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime

def teacher_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(request, "teachersManagement/login.html",
                          {"error": "Invalid username or password.",
                           "next": request.POST.get("next") or request.GET.get("next", "")})

        # Adjust this to your actual related_name. Default is user.teacherprofile
        if getattr(user, "teacherprofile", None) is None and getattr(user, "teacher_profile", None) is None:
            return render(request, "teachersManagement/login.html",
                          {"error": "This account is not a teacher.",
                           "next": request.POST.get("next") or request.GET.get("next", "")})

        if not user.is_active:
            return render(request, "teachersManagement/login.html",
                          {"error": "Account is inactive. Contact admin.",
                           "next": request.POST.get("next") or request.GET.get("next", "")})

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        nxt = request.POST.get("next") or request.GET.get("next") or reverse("teachersManagement:teacher_home")
        return redirect(nxt)

    return render(request, "teachersManagement/login.html", {"next": request.GET.get("next", "")})

def teacher_logout(request):
    logout(request)
    return redirect("welcome_page:welcome_page")

@login_required(login_url="teachersManagement:teacher_login")
def teacher_home(request):
    if getattr(request.user, "teacherprofile", None) is None and getattr(request.user, "teacher_profile", None) is None:
        return redirect("teachersManagement:teacher_login")
    
    # Get comprehensive data for teacher dashboard
    from course_management.models import Course, Enrollment, CourseLesson
    from lesson_management.models import Lesson, LessonEnrollment
    from student_management.models import Student
    from django.db.models import Count
    
    # Get all courses with enrollment counts
    courses_data = []
    all_courses = (
        Course.objects.all()
        .prefetch_related('enrollments', 'course_lessons__lesson')
    )
    
    for course in all_courses:
        # Get students enrolled in this course (primary enrollment)
        course_enrollments = Enrollment.objects.filter(course=course)
        
        # Lessons attached to this course (published only)
        attached_lessons = (
            course.course_lessons
            .select_related('lesson')
            .filter(lesson__status='published')
        )
        
        # For each student enrolled in the course, show their progress across all lessons
        students_data = []
        for enrollment in course_enrollments:
            student = enrollment.student
            
            # Get student details
            student_data = {
                "id": student.id,
                "name": student.full_name(),
                "email": student.user.email,
                "enrollment_number": student.enrollment_number,
                "course_code": course.code,
            }
            
            # Get ALL lessons this student has taken (core + electives)
            # Not just lessons attached to the enrolled course
            student_lesson_enrollments = LessonEnrollment.objects.filter(
                student=student
            ).select_related('lesson').filter(lesson__status='published')
            
           # Get unique lessons from enrollments
            student_lessons = [enrollment.lesson for enrollment in student_lesson_enrollments]
            
            # Calculate overall progress for this student across all lessons
            total_progress = 0
            total_marks = 0
            total_earned_marks = 0
            total_assignments = 0
            graded_assignments = 0
            weighted_percentage = 0
            lesson_details = []
            passed = False
            
            # Get actual awarded credits from ManageCreditPoint (not calculated on-the-fly)
            from student_management.models import ManageCreditPoint
            credit_obj = ManageCreditPoint.objects.filter(student=student).first()
            actual_credits_earned = credit_obj.credits if credit_obj else 0
            
            from lesson_management.models import ReadingList, ReadingListProgress, VideoProgress
            
            for lesson in student_lessons:
                # Check if student is enrolled in a classroom for this lesson
                is_in_classroom = ClassroomStudent.objects.filter(
                    student=student,
                    classroom__lesson=lesson
                ).exists()
                
                # Skip lessons where student is not in a classroom
                if not is_in_classroom:
                    continue
                
                # Calculate lesson progress
                lesson_total_items = ReadingList.objects.filter(lesson=lesson).count()
                if lesson.youtube_link:
                    lesson_total_items += 1
                
                lesson_completed = ReadingListProgress.objects.filter(
                    student=student, reading__lesson=lesson, done=True
                ).count()
                if lesson.youtube_link:
                    vp = VideoProgress.objects.filter(student=student, lesson=lesson, watched=True).exists()
                    lesson_completed += 1 if vp else 0
                
                lesson_progress_pct = int((lesson_completed / lesson_total_items) * 100) if lesson_total_items else 0
                total_progress += lesson_progress_pct
                
                # Calculate assignment grades for this lesson (only for classroom-enrolled students)
                assignments = lesson.assignments.all()
                total_assignments += assignments.count()
                lesson_total_marks = 0
                lesson_earned_marks = 0
                lesson_graded_assignments = 0
                lesson_assignment_details = []
                
                for assignment in assignments:
                    lesson_total_marks += float(assignment.marks)
                    try:
                        grade = AssignmentGrade.objects.get(assignment=assignment, student=student)
                        if grade.marks_awarded is not None:
                            lesson_earned_marks += float(grade.marks_awarded)
                            lesson_graded_assignments += 1
                            lesson_assignment_details.append({
                                "title": assignment.title,
                                "marks_awarded": float(grade.marks_awarded),
                                "max_marks": float(assignment.marks),
                                "weightage": float(assignment.weightage),
                                "feedback": grade.feedback
                            })
                        else:
                            lesson_assignment_details.append({
                                "title": assignment.title,
                                "marks_awarded": "Not graded",
                                "max_marks": float(assignment.marks),
                                "weightage": float(assignment.weightage),
                                "feedback": grade.feedback or "Not graded"
                            })
                    except AssignmentGrade.DoesNotExist:
                        lesson_assignment_details.append({
                            "title": assignment.title,
                            "marks_awarded": "Not graded",
                            "max_marks": float(assignment.marks),
                            "weightage": float(assignment.weightage),
                            "feedback": "Not graded"
                        })
                
                # Calculate weighted percentage for this lesson
                lesson_weighted_percentage = 0
                if assignments.exists():
                    total_weightage = sum(float(a.weightage) for a in assignments)
                    if total_weightage > 0:
                        weighted_score = 0
                        for assignment in assignments:
                            try:
                                grade = AssignmentGrade.objects.get(assignment=assignment, student=student)
                                if grade.marks_awarded is not None and assignment.marks > 0:
                                    percentage_achieved = (float(grade.marks_awarded) / float(assignment.marks)) * 100
                                    weighted_contribution = (percentage_achieved * float(assignment.weightage)) / 100
                                    weighted_score += weighted_contribution
                                    graded_assignments += 1  # Count total graded assignments
                            except AssignmentGrade.DoesNotExist:
                                continue
                        lesson_weighted_percentage = round(weighted_score, 1)
                        weighted_percentage = max(weighted_percentage, lesson_weighted_percentage)  # Track highest weighted percentage
                
                # Update overall totals
                total_marks += lesson_total_marks
                total_earned_marks += lesson_earned_marks
                
                # Use student_passed() method to check if lesson is passed (more reliable)
                lesson_passed, lesson_percentage, pass_details = lesson.student_passed(student)
                
                # Add lesson details
                lesson_details.append({
                    "lesson_title": lesson.title,
                    "lesson_code": lesson.unit_code,
                    "progress_pct": lesson_progress_pct,
                    "credits": getattr(lesson, "lesson_credits", 0) or 0,
                    "total_marks": lesson_total_marks,
                    "earned_marks": lesson_earned_marks,
                    "graded_assignments": lesson_graded_assignments,
                    "total_assignments": assignments.count(),
                    "weighted_percentage": float(lesson_percentage),  # Use student_passed() result
                    "passed": lesson_passed,  # Use student_passed() result
                    "assignment_details": lesson_assignment_details
                })
            
            # Calculate overall averages (only for classroom-enrolled lessons)
            num_classroom_lessons = len(lesson_details)  # Only lessons where student is in classroom
            avg_progress = int(total_progress / num_classroom_lessons) if num_classroom_lessons > 0 else 0
            
            # Calculate overall weighted percentage as average of all lesson weighted percentages
            total_weighted_percentage = sum(ld['weighted_percentage'] for ld in lesson_details)
            overall_weighted_percentage = total_weighted_percentage / num_classroom_lessons if num_classroom_lessons > 0 else 0
            
            # Student passes overall if their weighted percentage >= 50
            overall_passed = overall_weighted_percentage >= 50
            
            student_data = {
                "id": student.id,
                "name": student.full_name(),
                "email": student.user.email if student.user else "",
                "enrollment_number": student.enrollment_number,
                "course_code": course.code,
                "progressPct": avg_progress,
                "credits": actual_credits_earned,  # Use actual awarded credits from ManageCreditPoint
                "total_marks": total_marks,
                "earned_marks": total_earned_marks,
                "total_assignments": total_assignments,
                "graded_assignments": graded_assignments,
                "weighted_percentage": round(overall_weighted_percentage, 1),
                "passed": overall_passed,
                "lesson_details": lesson_details
            }
            students_data.append(student_data)
            
        # Course enrollment count (students enrolled in the course)
        enrolled_count = course_enrollments.count()
        
        course_data = {
            "id": course.id,
            "title": course.name,
            "code": course.code,
            "status": course.status,
            "total_credits_required": course.total_credits_required,
            "students": students_data,  # Changed from lessons to students
            "enrolledCount": enrolled_count,
        }
        courses_data.append(course_data)
    
    # Calculate metrics
    total_students = Student.objects.count()
    total_courses = Course.objects.count()
    # Count all lessons so new creations reflect immediately regardless of status
    total_lessons_count = Lesson.objects.count()
    
    # Prepare context for JSON
    context_json = {
        "metrics": {
            "students": total_students,
            "courses": total_courses,
            "totalLessons": total_lessons_count,
        },
        "courses": courses_data
    }
    
    return render(request, "teachersManagement/home.html", {"context_json": context_json})

# NEW: helper to verify teacher role
def is_teacher(user):
    return getattr(user, "teacherprofile", None) is not None or getattr(user, "teacher_profile", None) is not None

# NEW: list students for status editing
@method_decorator([login_required(login_url="teachersManagement:teacher_login"), user_passes_test(is_teacher)], name="dispatch")
class StudentStatusListView(ListView):
    model = Student
    template_name = "teachersManagement/student_status_list.html"
    context_object_name = "students"
    paginate_by = 25

    def get_queryset(self):
        # Support both 'q' and 'search' parameters for backward compatibility
        q = self.request.GET.get("search") or self.request.GET.get("q") or ""
        status = self.request.GET.get("status") or ""
        qs = Student.objects.select_related("user").order_by("last_name", "first_name")
        
        if q:
            try:
                q_num = int(q)
            except ValueError:
                q_num = None
            name_email_filter = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(user__email__icontains=q)
            if q_num is not None:
                qs = qs.filter(name_email_filter | Q(enrollment_number__startswith=q_num))
            else:
                qs = qs.filter(name_email_filter)
        
        if status:
            # Map template values to model field values
            if status == "dropped":
                qs = qs.filter(status="dropout")
            else:
                qs = qs.filter(status=status)
        
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search"] = self.request.GET.get("search", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        return ctx


@login_required(login_url="teachersManagement:teacher_login")
@user_passes_test(is_teacher)
@require_http_methods(["POST"])
def generate_student_report(request):
    """Generate a PDF report for student progress"""
    try:
        # Parse JSON data from request
        data = json.loads(request.body)
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph("Student Progress Report", title_style))
        story.append(Paragraph(f"Course: {data['course']['title']} ({data['course']['code']})", normal_style))
        story.append(Spacer(1, 20))
        
        # Student Information
        story.append(Paragraph("Student Information", heading_style))
        student_info = [
            ["Student Name:", data['student']['name']],
            ["Email:", data['student']['email']],
            ["Enrollment Number:", data['student']['enrollment_number']],
            ["Report Generated:", data['generated_at']]
        ]
        
        student_table = Table(student_info, colWidths=[2*inch, 3.5*inch])
        student_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(student_table)
        story.append(Spacer(1, 24))
        
        # Course Completion Progress
        story.append(Paragraph("Course Completion Progress", heading_style))
        
        # Calculate completion status
        total_credits_needed = data['course'].get('total_credits_required', 144)
        credits_earned = data['progress']['credits']
        completion_percentage = (credits_earned / total_credits_needed * 100) if total_credits_needed > 0 else 0
        
        # Determine overall status
        if data['assignments']['passed'] and credits_earned >= total_credits_needed:
            overall_status = "GRADUATED"
            status_color = colors.green
        elif data['assignments']['passed']:
            overall_status = "IN PROGRESS (Passing)"
            status_color = colors.blue
        else:
            overall_status = "IN PROGRESS (Not Passing)"
            status_color = colors.orange
        
        completion_data = [
            ["Overall Status:", overall_status],
            ["Credits Earned:", f"{credits_earned} / {total_credits_needed} credits ({completion_percentage:.1f}%)"],
            ["Overall Weighted Percentage:", f"{data['assignments']['weighted_percentage']}%"],
            ["Academic Standing:", "PASS" if data['assignments']['weighted_percentage'] >= 50 else "FAIL"],
        ]
        
        completion_table = Table(completion_data, colWidths=[2.5*inch, 3*inch])
        completion_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Highlight overall status
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#FFF9E6')),
            ('TEXTCOLOR', (1, 0), (1, 0), status_color),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            # Highlight academic standing
            ('TEXTCOLOR', (1, -1), (1, -1), colors.green if data['assignments']['weighted_percentage'] >= 50 else colors.red),
            ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ]))
        story.append(completion_table)
        story.append(Spacer(1, 24))
        
        # Assignment Summary - Recalculate based on actual lesson details (classroom-enrolled only)
        story.append(Paragraph("Assignment Summary", heading_style))
        
        # Recalculate assignment statistics from lesson details
        total_assignments_count = 0
        graded_assignments_count = 0
        total_marks_available = 0
        total_marks_earned = 0
        
        for lesson_detail in data['assignments']['details']:
            for assignment_detail in lesson_detail.get('assignment_details', []):
                total_assignments_count += 1
                total_marks_available += float(assignment_detail.get('max_marks', 0))
                
                if assignment_detail.get('marks_awarded') != 'Not graded':
                    graded_assignments_count += 1
                    total_marks_earned += float(assignment_detail.get('marks_awarded', 0))
        
        ungraded_count = total_assignments_count - graded_assignments_count
        
        assignment_summary_data = [
            ["Total Assignments:", f"{total_assignments_count}"],
            ["Graded Assignments:", f"{graded_assignments_count}"],
            ["Ungraded Assignments:", f"{ungraded_count}"],
            ["Total Marks Available:", f"{total_marks_available:.1f}"],
            ["Marks Earned:", f"{total_marks_earned:.1f}"],
        ]
        
        assignment_summary_table = Table(assignment_summary_data, colWidths=[2.5*inch, 3*inch])
        assignment_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(assignment_summary_table)
        story.append(Spacer(1, 24))
        
        # Lesson-by-Lesson Breakdown
        if data['assignments']['details']:
            story.append(Paragraph("Lesson-by-Lesson Breakdown", heading_style))
            story.append(Spacer(1, 8))
            
            # Process each lesson's assignments
            for idx, lesson_detail in enumerate(data['assignments']['details']):
                lesson_title = lesson_detail.get('lesson_title', 'Unknown Lesson')
                lesson_code = lesson_detail.get('lesson_code', '')
                lesson_credits = lesson_detail.get('credits', 0)
                lesson_weighted_pct = lesson_detail.get('weighted_percentage', 0)
                lesson_passed = lesson_detail.get('passed', False)
                
                # Lesson header with status
                lesson_status = "PASS" if lesson_passed else "FAIL"
                lesson_status_color = colors.green if lesson_passed else colors.red
                
                lesson_header_style = ParagraphStyle(
                    'LessonHeader',
                    parent=styles['Normal'],
                    fontSize=11,
                    fontName='Helvetica-Bold',
                    spaceAfter=6,
                    textColor=colors.HexColor('#1e40af')
                )
                
                story.append(Paragraph(
                    f"<b>{lesson_code}: {lesson_title}</b> | Credits: {lesson_credits} | Score: {lesson_weighted_pct:.1f}% | Status: <font color='{'green' if lesson_passed else 'red'}'>{lesson_status}</font>",
                    lesson_header_style
                ))
                
                if lesson_detail.get('assignment_details'):
                    # Table headers with status column
                    assignment_headers = [
                        Paragraph("<b>Assignment</b>", ParagraphStyle('HeaderLeft', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT)),
                        Paragraph("<b>Status</b>", ParagraphStyle('HeaderCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                        Paragraph("<b>Marks</b>", ParagraphStyle('HeaderCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                        Paragraph("<b>Max</b>", ParagraphStyle('HeaderCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                        Paragraph("<b>Weight</b>", ParagraphStyle('HeaderCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                        Paragraph("<b>Contribution</b>", ParagraphStyle('HeaderCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                    ]
                    assignment_data = [assignment_headers]
                    
                    # Cell styles
                    table_cell_style = ParagraphStyle(
                        'TableCell', parent=styles['Normal'], fontSize=8, leading=10, wordWrap='CJK'
                    )
                    table_cell_style_left = ParagraphStyle(
                        'TableCellLeft', parent=table_cell_style, alignment=TA_LEFT
                    )
                    table_cell_style_center = ParagraphStyle(
                        'TableCellCenter', parent=table_cell_style, alignment=TA_CENTER
                    )
                    
                    # Track graded vs ungraded
                    graded_count = 0
                    ungraded_count = 0
                    
                    for assignment in lesson_detail['assignment_details']:
                        title_par = Paragraph(assignment['title'], table_cell_style_left)
                        
                        # Check if assignment has been graded
                        if assignment['marks_awarded'] == "Not graded":
                            ungraded_count += 1
                            status_par = Paragraph("<font color='orange'><b>Not Graded</b></font>", table_cell_style_center)
                            marks_par = Paragraph("-", table_cell_style_center)
                            max_par = Paragraph(f"{float(assignment['max_marks']):.1f}", table_cell_style_center)
                            weight_par = Paragraph(f"{float(assignment['weightage']):.1f}%", table_cell_style_center)
                            contrib_par = Paragraph("-", table_cell_style_center)
                            
                            assignment_data.append([
                                title_par,
                                status_par,
                                marks_par,
                                max_par,
                                weight_par,
                                contrib_par,
                            ])
                            continue
                        
                        graded_count += 1
                        
                        # Calculate contribution: (marks_awarded / max_marks) * weightage
                        marks_awarded = float(assignment['marks_awarded'])
                        max_marks = float(assignment['max_marks'])
                        weightage = float(assignment['weightage'])
                        
                        if max_marks > 0:
                            contribution = (marks_awarded / max_marks) * weightage
                            percentage = (marks_awarded / max_marks) * 100
                        else:
                            contribution = 0
                            percentage = 0
                        
                        # Determine status based on percentage
                        if percentage >= 50:
                            status_text = "<font color='green'><b>Pass</b></font>"
                        else:
                            status_text = "<font color='red'><b>Fail</b></font>"
                        
                        status_par = Paragraph(status_text, table_cell_style_center)
                        
                        assignment_data.append([
                            title_par,
                            status_par,
                            Paragraph(f"{marks_awarded:.1f}", table_cell_style_center),
                            Paragraph(f"{max_marks:.1f}", table_cell_style_center),
                            Paragraph(f"{weightage:.1f}%", table_cell_style_center),
                            Paragraph(f"{contribution:.2f}%", table_cell_style_center),
                        ])
                    
                    # Calculate total weighted percentage for this lesson (only graded assignments)
                    total_contribution = sum(
                        (float(a['marks_awarded']) / float(a['max_marks'])) * float(a['weightage'])
                        if a['marks_awarded'] != "Not graded" and float(a['max_marks']) > 0 else 0
                        for a in lesson_detail['assignment_details']
                    )
                    
                    # Add summary row with graded/ungraded counts
                    summary_style = ParagraphStyle(
                        'Summary', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, fontName='Helvetica-Bold'
                    )
                    summary_center_style = ParagraphStyle(
                        'SummaryCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, fontName='Helvetica-Bold'
                    )
                    
                    assignment_data.append([
                        Paragraph(f"<b>Summary: {graded_count} Graded, {ungraded_count} Ungraded</b>", summary_style),
                        '',
                        '',
                        '',
                        Paragraph("<b>Total:</b>", summary_center_style),
                        Paragraph(f"<b>{total_contribution:.1f}%</b>", summary_center_style),
                    ])
                    
                    # Adjusted column widths
                    assignment_table = Table(assignment_data, colWidths=[2.2*inch, 0.9*inch, 0.7*inch, 0.6*inch, 0.7*inch, 1*inch], repeatRows=1)
                    assignment_table.setStyle(TableStyle([
                        # Header row styling
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
                        
                        # Data rows styling
                        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#FEFCE8')),
                        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -2), 8),
                        ('ALIGN', (0, 1), (0, -2), 'LEFT'),
                        ('ALIGN', (1, 1), (-1, -2), 'CENTER'),
                        
                        # Summary row styling
                        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E0E7FF')),
                        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, -1), (-1, -1), 9),
                        ('SPAN', (0, -1), (3, -1)),
                        ('ALIGN', (0, -1), (0, -1), 'LEFT'),
                        ('ALIGN', (4, -1), (-1, -1), 'CENTER'),
                        
                        # General table styling
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 1), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                        ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
                    ]))
                    story.append(assignment_table)
                    story.append(Spacer(1, 16))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Student_Report_{data["student"]["name"].replace(" ", "_")}.pdf"'
        response.write(pdf_content)
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# NEW: update only status + is_active
@method_decorator([login_required(login_url="teachersManagement:teacher_login"), user_passes_test(is_teacher)], name="dispatch")
class StudentStatusUpdateView(UpdateView):
    model = Student
    fields = ["status"]
    template_name = "teachersManagement/student_status_form.html"
    success_url = reverse_lazy("teachersManagement:student_status_list")

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, f"Updated {form.instance.full_name()} enrollment status.")
        return resp