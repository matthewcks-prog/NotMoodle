"""Views for NotMoodle AI Assistant API."""
import json
from typing import Dict, List, Optional
from datetime import date, datetime
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from pgvector.django import CosineDistance

from .models import DocumentChunk, StudentQuestion
from .ollama import embed_texts, chat, estimate_tokens
from student_management.models import Student, ManageCreditPoint
from course_management.models import Enrollment
from lesson_management.models import LessonEnrollment, Assignment, ReadingListProgress, VideoProgress
from classroom_and_grading.models import AssignmentGrade, ClassroomStudent


def get_user_profile_context(user) -> str:
    """
    Generate personalized context about the logged-in user.
    
    Includes:
    - User profile information
    - Enrolled courses
    - Enrolled lessons with progress
    - Grades and assignments
    - Upcoming assignments
    - Credits
    
    Args:
        user: Django User object
    
    Returns:
        Formatted string with user profile information
    """
    context_parts = []
    
    # Basic user information
    context_parts.append(f"=== USER PROFILE ===")
    context_parts.append(f"Username: {user.username}")
    context_parts.append(f"Full Name: {user.get_full_name() or 'Not specified'}")
    context_parts.append(f"Email: {user.email}")
    
    # Try to get student profile
    try:
        student = Student.objects.get(user=user)
        context_parts.append(f"Student Name: {student.full_name()}")
        context_parts.append(f"Enrollment Number: {student.enrollment_number}")
        context_parts.append(f"Date of Birth: {student.date_of_birth}")
        context_parts.append(f"Year of Study: {student.year_of_study or 'Not specified'}")
        context_parts.append(f"GPA: {student.gpa or 'Not yet calculated'}")
        context_parts.append(f"Status: {student.get_status_display()}")
        
        # Get credits
        try:
            credit = ManageCreditPoint.objects.get(student=student)
            context_parts.append(f"Total Credits: {credit.credits}")
        except ManageCreditPoint.DoesNotExist:
            context_parts.append(f"Total Credits: 0")
        
        # Enrolled courses
        context_parts.append(f"\n=== ENROLLED COURSES ===")
        enrollments = Enrollment.objects.filter(student=student).select_related('course')
        if enrollments.exists():
            for enrollment in enrollments:
                course = enrollment.course
                context_parts.append(f"- {course.code}: {course.name}")
                context_parts.append(f"  Status: {course.get_status_display()}")
                context_parts.append(f"  Credits Required: {course.total_credits_required}")
                context_parts.append(f"  Enrolled on: {enrollment.enrolled_at.strftime('%Y-%m-%d')}")
                context_parts.append(f"  Enrolled by: {enrollment.get_enrolled_by_display()}")
        else:
            context_parts.append("No courses enrolled yet.")
        
        # Enrolled lessons with progress
        context_parts.append(f"\n=== ENROLLED LESSONS ===")
        lesson_enrollments = LessonEnrollment.objects.filter(
            student=student
        ).select_related('lesson', 'lesson__lesson_designer').order_by('-enrolled_at')
        
        if lesson_enrollments.exists():
            for le in lesson_enrollments:
                lesson = le.lesson
                context_parts.append(f"\n- {lesson.unit_code}: {lesson.title}")
                context_parts.append(f"  Description: {lesson.description[:100]}..." if len(lesson.description) > 100 else f"  Description: {lesson.description}")
                context_parts.append(f"  Credits: {lesson.lesson_credits}")
                context_parts.append(f"  Estimated Effort: {lesson.estimated_effort} hours/week")
                context_parts.append(f"  Status: {lesson.get_status_display()}")
                context_parts.append(f"  Enrolled on: {le.enrolled_at.strftime('%Y-%m-%d')}")
                
                # Check video progress
                try:
                    video_progress = VideoProgress.objects.get(student=student, lesson=lesson)
                    context_parts.append(f"  Video: {'Watched ✓' if video_progress.watched else 'Not watched yet'}")
                except VideoProgress.DoesNotExist:
                    context_parts.append(f"  Video: Not watched yet")
                
                # Reading list progress
                reading_list = lesson.reading_list.all()
                if reading_list.exists():
                    completed_readings = ReadingListProgress.objects.filter(
                        student=student,
                        reading__lesson=lesson,
                        done=True
                    ).count()
                    total_readings = reading_list.count()
                    context_parts.append(f"  Reading Progress: {completed_readings}/{total_readings} completed")
                
                # Calculate lesson grade
                passed, percentage, details = lesson.student_passed(student)
                if details.get('has_grades'):
                    context_parts.append(f"  Overall Grade: {percentage:.2f}% ({'PASSED' if passed else 'NOT PASSED'})")
                    context_parts.append(f"  Graded Assignments: {details['graded_assignments']}/{details['total_assignments']}")
                
        else:
            context_parts.append("No lessons enrolled yet.")
        
        # Upcoming assignments
        context_parts.append(f"\n=== UPCOMING ASSIGNMENTS ===")
        now = timezone.now()
        
        # Get all lessons the student is enrolled in
        enrolled_lesson_ids = lesson_enrollments.values_list('lesson_id', flat=True)
        
        # Find upcoming assignments (not yet due)
        upcoming_assignments = Assignment.objects.filter(
            lesson_id__in=enrolled_lesson_ids,
            due_date__gte=now
        ).select_related('lesson').order_by('due_date')[:10]
        
        if upcoming_assignments.exists():
            for assignment in upcoming_assignments:
                context_parts.append(f"\n- {assignment.title}")
                context_parts.append(f"  Lesson: {assignment.lesson.unit_code} - {assignment.lesson.title}")
                context_parts.append(f"  Release Date: {assignment.release_date.strftime('%Y-%m-%d %H:%M')}")
                context_parts.append(f"  Due Date: {assignment.due_date.strftime('%Y-%m-%d %H:%M')}")
                context_parts.append(f"  Total Marks: {assignment.marks}")
                context_parts.append(f"  Weightage: {assignment.weightage}%")
                
                # Check if submitted
                from lesson_management.models import AssignmentSubmission
                try:
                    submission = AssignmentSubmission.objects.get(assignment=assignment, student=student)
                    context_parts.append(f"  Status: Submitted on {submission.submitted_at.strftime('%Y-%m-%d %H:%M')}")
                except AssignmentSubmission.DoesNotExist:
                    context_parts.append(f"  Status: Not yet submitted")
                
                # Check if graded
                try:
                    grade = AssignmentGrade.objects.get(assignment=assignment, student=student)
                    if grade.marks_awarded is not None:
                        percentage = (grade.marks_awarded / assignment.marks * 100) if assignment.marks > 0 else 0
                        context_parts.append(f"  Grade: {grade.marks_awarded}/{assignment.marks} ({percentage:.1f}%)")
                        if grade.feedback:
                            context_parts.append(f"  Feedback: {grade.feedback[:100]}..." if len(grade.feedback) > 100 else f"  Feedback: {grade.feedback}")
                except AssignmentGrade.DoesNotExist:
                    context_parts.append(f"  Grade: Not yet graded")
        else:
            context_parts.append("No upcoming assignments.")
        
        # Past assignments (recently due)
        context_parts.append(f"\n=== RECENT PAST ASSIGNMENTS ===")
        past_assignments = Assignment.objects.filter(
            lesson_id__in=enrolled_lesson_ids,
            due_date__lt=now
        ).select_related('lesson').order_by('-due_date')[:5]
        
        if past_assignments.exists():
            for assignment in past_assignments:
                context_parts.append(f"\n- {assignment.title}")
                context_parts.append(f"  Lesson: {assignment.lesson.unit_code}")
                context_parts.append(f"  Due Date: {assignment.due_date.strftime('%Y-%m-%d')}")
                
                # Check grade
                try:
                    grade = AssignmentGrade.objects.get(assignment=assignment, student=student)
                    if grade.marks_awarded is not None:
                        percentage = (grade.marks_awarded / assignment.marks * 100) if assignment.marks > 0 else 0
                        context_parts.append(f"  Grade: {grade.marks_awarded}/{assignment.marks} ({percentage:.1f}%)")
                except AssignmentGrade.DoesNotExist:
                    context_parts.append(f"  Grade: Not yet graded")
        
    except Student.DoesNotExist:
        context_parts.append("\nNote: No student profile found for this user.")
        context_parts.append("User may be a teacher or administrator.")
    
    return "\n".join(context_parts)


def retrieve_context(
    question: str,
    lesson_id: Optional[int] = None,
    top_k: int = 5
) -> List[Dict[str, str]]:
    """
    Retrieve relevant document chunks for a question using vector similarity.
    
    Args:
        question: User's question text
        lesson_id: Optional lesson ID to bias results toward
        top_k: Number of chunks to retrieve
    
    Returns:
        List of dicts with 'content', 'lesson_title', 'lesson_code' keys
    """
    # Get question embedding
    try:
        embeddings = embed_texts([question])
        question_embedding = embeddings[0]
    except Exception as e:
        print(f"Error generating question embedding: {e}")
        return []
    
    # Build query
    queryset = DocumentChunk.objects.select_related("lesson")
    
    if lesson_id:
        # If lesson specified, get top results from that lesson
        # plus some global results
        lesson_chunks = list(
            queryset.filter(lesson_id=lesson_id)
            .annotate(distance=CosineDistance('embedding', question_embedding))
            .order_by('distance')
            [:max(3, top_k // 2)]
        )
        
        # Get remaining from other lessons
        remaining = top_k - len(lesson_chunks)
        if remaining > 0:
            global_chunks = list(
                queryset.exclude(lesson_id=lesson_id)
                .annotate(distance=CosineDistance('embedding', question_embedding))
                .order_by('distance')
                [:remaining]
            )
            chunks = lesson_chunks + global_chunks
        else:
            chunks = lesson_chunks
    else:
        # Get top_k globally
        chunks = list(
            queryset
            .annotate(distance=CosineDistance('embedding', question_embedding))
            .order_by('distance')
            [:top_k]
        )
    
    # Format results
    results = []
    for chunk in chunks:
        results.append({
            "content": chunk.content,
            "lesson_title": chunk.lesson.title,
            "lesson_code": chunk.lesson.unit_code,
        })
    
    return results


@csrf_exempt
@require_POST
@login_required
def ask_assistant(request):
    """
    Chat endpoint for NotMoodle AI Assistant.
    
    POST /api/notmoodle/ask/
    Body: {"message": "...", "lesson_id": optional int}
    
    Returns:
        JSON: {"reply": "...", "sources": [...], "usage_today": int}
        Or error: {"error": "..."}
    """
    # Check if PostgreSQL is available (required for pgvector)
    if not settings.USING_POSTGRESQL:
        return JsonResponse(
            {
                "error": "AI Assistant requires PostgreSQL with pgvector extension. "
                        "Currently using SQLite. Please set up PostgreSQL to enable this feature. "
                        "See AI_ASSISTANT_GUIDE.md for setup instructions."
            },
            status=503
        )
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    message = data.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)
    
    lesson_id = data.get("lesson_id")
    
    # Check rate limit
    today = date.today()
    questions_today = StudentQuestion.objects.filter(
        user=request.user,
        created_at__date=today
    ).count()
    
    if questions_today >= settings.AI_DAILY_QUESTION_LIMIT:
        return JsonResponse(
            {
                "error": f"Daily question limit reached ({settings.AI_DAILY_QUESTION_LIMIT}). Please try again tomorrow."
            },
            status=429
        )
    
    # Retrieve context
    try:
        context_chunks = retrieve_context(message, lesson_id=lesson_id, top_k=5)
    except Exception as e:
        print(f"Error retrieving context: {e}")
        context_chunks = []
    
    # Get personalized user context
    user_profile_context = get_user_profile_context(request.user)
    
    # Build context string
    if context_chunks:
        context_text = "\n\n".join([
            f"[From {chunk['lesson_code']} - {chunk['lesson_title']}]\n{chunk['content']}"
            for chunk in context_chunks
        ])
    else:
        context_text = "No relevant course content found."
    
    # Build system prompt with personalized information
    system_prompt = f"""You are NotMoodle AI, a helpful and knowledgeable personal tutor for students in a Learning Management System.

Your role:
- Provide PERSONALIZED assistance to the logged-in student
- Help students understand their enrolled courses and lessons
- Answer questions based on both the student's personal information AND the course content provided below
- Track and reference the student's progress, grades, and upcoming assignments
- Explain concepts clearly with examples when helpful
- Break down complex topics into digestible steps
- Be encouraging, supportive, and patient

Guidelines:
- ALWAYS address the student by name when appropriate
- Reference their specific enrollments, grades, and assignments when relevant
- When asked about "my courses", "my lessons", "my grades", etc., use the student profile information below
- If asked about enrolled lessons or courses, refer to the STUDENT PROFILE section first
- Use both the student's personal data AND course materials to provide comprehensive answers
- If the context contains the answer, provide it clearly and confidently
- If the context is insufficient, acknowledge what information is available and what's missing
- For conceptual questions, explain in a teaching style with examples
- Keep responses focused and concise (2-4 paragraphs maximum)
- Use markdown formatting for better readability (bold, lists, etc.)

{user_profile_context}

===================================

Context from course materials:
{context_text}
"""
    
    # Generate response
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        response = chat(messages)
    except Exception as e:
        print(f"Error generating chat response: {e}")
        return JsonResponse(
            {"error": "Failed to generate response. Please try again."},
            status=500
        )
    
    # Log question
    tokens_in = estimate_tokens(system_prompt + message)
    tokens_out = estimate_tokens(response)
    
    StudentQuestion.objects.create(
        user=request.user,
        question=message,
        answer=response,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    
    # Format sources
    sources = []
    for chunk in context_chunks:
        sources.append({
            "lesson": f"{chunk['lesson_code']} - {chunk['lesson_title']}",
            "excerpt": chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
        })
    
    return JsonResponse({
        "reply": response,
        "sources": sources,
        "usage_today": questions_today + 1,
    })


@login_required
def assistant_usage(request):
    """
    Get current user's AI assistant usage stats.
    
    GET /api/notmoodle/usage/
    
    Returns:
        JSON: {"questions_today": int, "daily_limit": int, "available": bool}
    """
    # Check if PostgreSQL is available
    if not settings.USING_POSTGRESQL:
        return JsonResponse({
            "questions_today": 0,
            "daily_limit": settings.AI_DAILY_QUESTION_LIMIT,
            "available": False,
            "message": "AI Assistant requires PostgreSQL. Currently using SQLite."
        })
    
    today = date.today()
    questions_today = StudentQuestion.objects.filter(
        user=request.user,
        created_at__date=today
    ).count()
    
    return JsonResponse({
        "questions_today": questions_today,
        "daily_limit": settings.AI_DAILY_QUESTION_LIMIT,
        "available": True,
    })
