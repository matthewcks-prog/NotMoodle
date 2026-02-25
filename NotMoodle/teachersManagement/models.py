from django.db import models
from django.contrib.auth.models import User

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    department = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    # NEW: Additional fields for admin-entered information
    display_name = models.CharField(max_length=200, blank=True, help_text="Full display name for the teacher")
    contact_email = models.EmailField(blank=True, help_text="Primary contact email for the teacher")

    def __str__(self):
        # Prioritize display_name, then user's full name, then username
        return self.display_name or self.user.get_full_name() or self.user.username
    
    def get_full_name(self):
        """Return the best available full name"""
        return self.display_name or self.user.get_full_name() or self.user.username
    
    def get_email(self):
        """Return the best available email"""
        return self.contact_email or self.user.email
