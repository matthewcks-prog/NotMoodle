from django import forms
from student_management.models import Student

# i created a new form in student management form that register the student as a user as well
class StudentSignupForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "first_name", "last_name", "date_of_birth",
            "email", "phone_number", "gpa",
        ]
        
        widgets = {
            "date_of_birth" : forms.DateInput(attrs={"type": "date"}),
            "gpa": forms.NumberInput(attrs={"min": "0", "max": "4", "step": "0.01"}),
            # year_of_study is not collected at signup
        }