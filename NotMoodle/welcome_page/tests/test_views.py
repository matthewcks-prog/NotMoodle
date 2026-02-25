"""Tests for welcome_page views."""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from model_bakery import baker
from welcome_page.models import ContactMessage
from student_management.models import Student
from course_management.models import Course


@pytest.mark.django_db
class TestWelcomePageViews:
    """Test welcome page views."""
    
    def test_welcome_page(self, client):
        """Test welcome page renders."""
        url = reverse("welcome_page:welcome_page")
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_about_page(self, client):
        """Test about page renders."""
        url = reverse("welcome_page:about")
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_contact_page_get(self, client):
        """Test contact page GET."""
        url = reverse("welcome_page:contact")
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_contact_page_post_success(self, client):
        """Test submitting contact form."""
        url = reverse("welcome_page:contact")
        
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "Test message",
        }
        
        response = client.post(url, data=data)
        
        assert response.status_code == 302  # Redirect
        assert ContactMessage.objects.filter(email="john@example.com").exists()
    
    def test_contact_page_post_missing_fields(self, client):
        """Test contact form with missing fields."""
        url = reverse("welcome_page:contact")
        
        data = {
            "name": "John Doe",
            # Missing email and message
        }
        
        response = client.post(url, data=data)
        
        # Should show error
        assert response.status_code == 200
    
    def test_news_page(self, client):
        """Test news page renders."""
        url = reverse("welcome_page:news")
        response = client.get(url)
        
        assert response.status_code == 200
        assert "items" in response.context
    
    def test_courses_page_anonymous(self, client):
        """Test courses page for anonymous users."""
        course = baker.make(Course, code="CS101", name="Intro to CS", status="active")
        
        url = reverse("welcome_page:courses")
        response = client.get(url)
        
        assert response.status_code == 200
        assert "courses" in response.context
    
    def test_courses_page_authenticated_student(self, student_client, student):
        """Test courses page for authenticated student."""
        course = baker.make(Course, code="CS101", status="active")
        
        url = reverse("welcome_page:courses")
        response = student_client.get(url)
        
        assert response.status_code == 200
    
    def test_login_choice_anonymous(self, client):
        """Test login choice page for anonymous users."""
        url = reverse("welcome_page:login_choice")
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_login_choice_authenticated_student(self, student_client):
        """Test login choice redirects authenticated student."""
        url = reverse("welcome_page:login_choice")
        response = student_client.get(url)
        
        assert response.status_code == 302  # Redirect to dashboard


@pytest.mark.django_db
class TestErrorHandlers:
    """Test custom error handlers."""
    
    def test_error_404(self, client):
        """Test 404 error handler."""
        response = client.get("/nonexistent-url-12345/")
        
        assert response.status_code == 404
    
    def test_error_404_explicit(self, client):
        """Test explicit 404 page."""
        url = reverse("error_404")
        response = client.get(url)
        
        assert response.status_code == 404

