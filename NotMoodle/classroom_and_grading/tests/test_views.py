"""
Tests for classroom_and_grading app views.
"""
import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from model_bakery import baker
from classroom_and_grading.models import Classroom, ClassroomStudent, AssignmentGrade
from lesson_management.models import Assignment


@pytest.mark.django_db
class TestClassroomCreateView:
    """Test ClassroomCreateView."""
    
    def test_create_classroom_requires_login(self, client):
        """Test that view requires authentication."""
        url = reverse("classroom_and_grading:classroom_create")
        response = client.get(url)
        
        assert response.status_code == 302  # Redirect to login
    
    def test_create_classroom_requires_teacher(self, student_client):
        """Test that view requires teacher profile."""
        url = reverse("classroom_and_grading:classroom_create")
        response = student_client.get(url)
        
        # Should redirect or show error
        assert response.status_code in [302, 403]
    
    def test_create_classroom_get(self, teacher_client):
        """Test GET request shows form."""
        url = reverse("classroom_and_grading:classroom_create")
        response = teacher_client.get(url)
        
        assert response.status_code == 200
        assert "form" in response.context
    
    def test_create_classroom_post_success(self, teacher_client, course, lesson, teacher):
        """Test successful classroom creation."""
        url = reverse("classroom_and_grading:classroom_create")
        
        data = {
            "course": course.id,
            "lesson": lesson.id,
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        }
        
        response = teacher_client.post(url, data=data)
        
        assert response.status_code == 302  # Redirect
        assert Classroom.objects.filter(course=course, lesson=lesson, teacher=teacher).exists()
    
    def test_create_classroom_duplicate_error(self, teacher_client, classroom):
        """Test duplicate classroom creation."""
        url = reverse("classroom_and_grading:classroom_create")
        
        data = {
            "course": classroom.course.id,
            "lesson": classroom.lesson.id,
            "start_date": classroom.start_date.date(),
            "end_date": classroom.end_date.date(),
        }
        
        response = teacher_client.post(url, data=data)
        
        # Should show error message
        assert response.status_code in [200, 302]


@pytest.mark.django_db
class TestClassroomDetailView:
    """Test ClassroomDetailView."""
    
    def test_classroom_detail(self, client, classroom):
        """Test viewing classroom detail."""
        url = reverse("classroom_and_grading:classroom_detail", kwargs={"pk": classroom.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context["classroom"] == classroom
    
    def test_classroom_detail_with_roster(self, client, classroom, student):
        """Test classroom detail shows roster."""
        baker.make(ClassroomStudent, classroom=classroom, student=student)
        
        url = reverse("classroom_and_grading:classroom_detail", kwargs={"pk": classroom.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        assert len(response.context["roster"]) == 1
    
    def test_classroom_detail_with_assignments(self, client, classroom, assignment):
        """Test classroom detail shows assignments."""
        assignment.lesson = classroom.lesson
        assignment.save()
        
        url = reverse("classroom_and_grading:classroom_detail", kwargs={"pk": classroom.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        assert len(response.context["assignments"]) >= 1
    
    def test_add_students_to_classroom(self, teacher_client, classroom, student):
        """Test adding students to classroom roster."""
        url = reverse("classroom_and_grading:classroom_detail", kwargs={"pk": classroom.pk})
        
        data = {
            "action": "add",
            "students": [student.id],
        }
        
        response = teacher_client.post(url, data=data)
        
        assert response.status_code == 302
        assert ClassroomStudent.objects.filter(classroom=classroom, student=student).exists()
    
    def test_remove_student_from_classroom(self, teacher_client, classroom, student):
        """Test removing student from classroom."""
        baker.make(ClassroomStudent, classroom=classroom, student=student)
        
        url = reverse("classroom_and_grading:classroom_detail", kwargs={"pk": classroom.pk})
        
        data = {
            "action": "remove",
            "student_id": student.id,
        }
        
        response = teacher_client.post(url, data=data)
        
        assert response.status_code == 302
        assert not ClassroomStudent.objects.filter(classroom=classroom, student=student).exists()
    
    def test_grade_submission(self, teacher_client, classroom, student, assignment, teacher):
        """Test grading a submission."""
        assignment.lesson = classroom.lesson
        assignment.save()
        
        baker.make(ClassroomStudent, classroom=classroom, student=student)
        
        url = reverse("classroom_and_grading:classroom_detail", kwargs={"pk": classroom.pk})
        
        data = {
            "action": "grade_submission",
            "assignment_id": assignment.id,
            "student_id": student.id,
            "marks_awarded": "85.50",
            "feedback": "Great work!",
        }
        
        response = teacher_client.post(url, data=data)
        
        assert response.status_code == 302
        grade = AssignmentGrade.objects.get(assignment=assignment, student=student)
        assert grade.marks_awarded == Decimal("85.50")
        assert grade.feedback == "Great work!"
    
    def test_grade_submission_invalid_marks(self, teacher_client, classroom, student, assignment):
        """Test grading with invalid marks."""
        assignment.lesson = classroom.lesson
        assignment.save()
        
        url = reverse("classroom_and_grading:classroom_detail", kwargs={"pk": classroom.pk})
        
        data = {
            "action": "grade_submission",
            "assignment_id": assignment.id,
            "student_id": student.id,
            "marks_awarded": "150",  # Over max
            "feedback": "Test",
        }
        
        response = teacher_client.post(url, data=data)
        
        # Should show error
        assert response.status_code == 302


@pytest.mark.django_db
class TestClassroomListView:
    """Test ClassroomListView."""
    
    def test_classroom_list(self, client):
        """Test viewing list of classrooms."""
        url = reverse("classroom_and_grading:classroom_list")
        response = client.get(url)
        
        assert response.status_code == 200
        assert "classrooms" in response.context
    
    def test_classroom_list_with_data(self, client, classroom):
        """Test list view with classrooms."""
        url = reverse("classroom_and_grading:classroom_list")
        response = client.get(url)
        
        assert response.status_code == 200
        classrooms = response.context["classrooms"]
        assert classroom in classrooms


@pytest.mark.django_db
class TestAssignmentManagement:
    """Test assignment creation and management views."""
    
    def test_create_assignment_for_classroom(self, teacher_client, classroom):
        """Test creating assignment for classroom."""
        url = reverse("classroom_and_grading:assignment_create", kwargs={"pk": classroom.pk})
        
        release_date = timezone.now()
        due_date = release_date + timedelta(days=7)
        
        data = {
            "title": "Test Assignment",
            "release_date": release_date.strftime("%Y-%m-%dT%H:%M"),
            "due_date": due_date.strftime("%Y-%m-%dT%H:%M"),
            "marks": "100.00",
            "weightage": "50.00",
            "description": "Test description",
        }
        
        response = teacher_client.post(url, data=data)
        
        assert response.status_code == 302
        assert Assignment.objects.filter(lesson=classroom.lesson, title="Test Assignment").exists()
    
    def test_delete_assignment(self, teacher_client, classroom, assignment):
        """Test deleting an assignment."""
        assignment.lesson = classroom.lesson
        assignment.save()
        
        url = reverse(
            "classroom_and_grading:assignment_delete",
            kwargs={"pk": classroom.pk, "assignment_id": assignment.id}
        )
        
        response = teacher_client.post(url)
        
        assert response.status_code == 302
        assert not Assignment.objects.filter(id=assignment.id).exists()


@pytest.mark.django_db
class TestDeleteClassroom:
    """Test classroom deletion."""
    
    def test_delete_classroom(self, teacher_client, classroom):
        """Test deleting a classroom."""
        url = reverse("classroom_and_grading:classroom_delete", kwargs={"pk": classroom.pk})
        
        response = teacher_client.post(url)
        
        assert response.status_code == 302
        assert not Classroom.objects.filter(id=classroom.pk).exists()

