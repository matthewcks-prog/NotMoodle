from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Student, ManageCreditPoint


class CreditChangeForm(forms.Form):
    ACTIONS = [
        ("increase", "Increase by amount"),
        ("decrease", "Decrease by amount"),
    ]
    action = forms.ChoiceField(choices=ACTIONS)
    amount = forms.IntegerField(min_value=0)


class StudentSignupForm(UserCreationForm):
    # fields to populate both User and Student
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    email = forms.EmailField(required=True)

    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    phone_number = forms.CharField(max_length=15, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        # guard against duplicates in either table
        if User.objects.filter(email__iexact=email).exists() or \
           Student.objects.filter(email__iexact=email).exists():
            raise ValidationError("That email is already in use.")
        return email

    # enrollment number is auto-generated in the model; no user input required

    def save(self, commit=True):
        # 1) create auth user
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name  = self.cleaned_data["last_name"]
        if commit:
            user.save()

            # 2) create linked Student row
            student = Student.objects.create(
                user=user,  # <-- requires Student.user OneToOneField(User, null=True, blank=True)
                first_name=self.cleaned_data["first_name"],
                last_name=self.cleaned_data["last_name"],
                date_of_birth=self.cleaned_data["date_of_birth"],
                email=self.cleaned_data["email"],
                phone_number=self.cleaned_data.get("phone_number") or None,
                # course and year_of_study are optional and not collected at signup
                status="active",
            )

            # 3) ensure credit record exists
            ManageCreditPoint.objects.get_or_create(student=student)
        return user

# ---------- NEW: student login (uses Django's built-in validation) ----------
class StudentLoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)