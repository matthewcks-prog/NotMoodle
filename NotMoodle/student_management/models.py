from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.
class EnrollmentSequence(models.Model):
    # AutoField primary key serves as a monotonically increasing counter
    # No additional fields required
    pass


class Student(models.Model):
    
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name="student", null=True, blank=True
    )

    # --- your existing fields below ---
    first_name = models.CharField(max_length=50)
    last_name  = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # numeric and auto-incrementing, hidden from forms (editable=False)
    enrollment_number = models.BigIntegerField(unique=True, editable=False)
    course = models.CharField(max_length=100, blank=True, null=True)
    year_of_study = models.IntegerField(blank=True, null=True)
    gpa = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(4.0)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ("active", "Active"),
        ("reactive", "Reactivated Enrollment"),
        ("dropout", "Dropped Out")
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.enrollment_number} - {self.full_name()}"

    def save(self, *args, **kwargs):
        # Assign enrollment_number if not already set, using a DB-backed sequence model for concurrency safety
        if not self.enrollment_number:
            seq = EnrollmentSequence.objects.create()
            self.enrollment_number = seq.id
        super().save(*args, **kwargs)


class ManageCreditPoint(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="credit")
    credits = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(9999)])

    def increase(self, amount=6):
        type(self).objects.filter(pk=self.pk).update(credits=F("credits") + amount)
        self.refresh_from_db(fields=["credits"])

    def decrease(self, amount=6):
        # Atomic clamp at zero to avoid negatives under concurrency
        type(self).objects.filter(pk=self.pk).update(
            credits=models.Case(
                models.When(credits__gte=amount, then=F("credits") - amount),
                default=0,
                output_field=models.IntegerField(),
            )
        )
        self.refresh_from_db(fields=["credits"])

    def __str__(self):
        return f"{self.student.enrollment_number} credits: {self.credits}"