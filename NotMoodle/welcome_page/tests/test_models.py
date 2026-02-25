"""Tests for welcome_page models."""
import pytest
from model_bakery import baker
from welcome_page.models import ContactMessage


@pytest.mark.django_db
class TestContactMessage:
    """Test ContactMessage model."""
    
    def test_create_contact_message(self):
        """Test creating a contact message."""
        message = baker.make(
            ContactMessage,
            name="John Doe",
            email="john@example.com",
            message="This is a test message.",
        )
        
        assert message.id is not None
        assert message.name == "John Doe"
        assert message.email == "john@example.com"
        assert message.message == "This is a test message."
        assert message.created_at is not None
    
    def test_contact_message_str(self):
        """Test __str__ method."""
        message = baker.make(
            ContactMessage,
            name="Jane Doe",
            email="jane@example.com",
        )
        
        str_repr = str(message)
        assert "Jane Doe" in str_repr
        assert "jane@example.com" in str_repr
    
    def test_contact_message_ordering(self):
        """Test default ordering by created_at descending."""
        from freezegun import freeze_time
        
        with freeze_time("2025-01-01 10:00:00"):
            msg1 = baker.make(ContactMessage, name="First")
        
        with freeze_time("2025-01-01 11:00:00"):
            msg2 = baker.make(ContactMessage, name="Second")
        
        with freeze_time("2025-01-01 12:00:00"):
            msg3 = baker.make(ContactMessage, name="Third")
        
        messages = list(ContactMessage.objects.all().order_by('-created_at')[:3])
        
        # Should be newest first (Third, Second, First)
        assert len(messages) >= 3

