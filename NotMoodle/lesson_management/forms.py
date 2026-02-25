from django import forms
from django.core.exceptions import ValidationError
from .models import Lesson, Assignment, AssignmentAttachment, AssignmentSubmission


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "unit_code",
            "title",
            "description",
            "objectives",
            "estimated_effort",
            "youtube_link",
            "prerequisites",
            "lesson_credits",
            "status",
        ]
        widgets = {
            # taller, rounded, with placeholder text
            "description": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Describe your lesson...",
            }),
            "objectives": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "List the learning objectives...",
            }),
            # render as vertical list we style in CSS
            "prerequisites": forms.CheckboxSelectMultiple(attrs={
                "class": "checkbox-list",
            }),
            # the rest get attrs in __init__ to keep things DRY
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Placeholders / rounded inputs for text/number fields
        self.fields["unit_code"].widget.attrs.update({
            "placeholder": "e.g., CS101",
        })
        self.fields["title"].widget.attrs.update({
            "placeholder": "Lesson title",
        })
        self.fields["estimated_effort"].widget.attrs.update({
            "min": 1, "max": 60, "step": 1,
        })
        self.fields["youtube_link"].widget.attrs.update({
            "placeholder": "https://www.youtube.com/watch?v=...",
        })
        self.fields["lesson_credits"].widget.attrs.update({
            "min": 0, "step": 1,
        })
        # keep prerequisites optional
        self.fields["prerequisites"].required = False

        # filter out archived lessons and order nicely
        self.fields["prerequisites"].queryset = (
            Lesson.objects.exclude(status="archived").order_by("unit_code")
        )

        # when editing, exclude self to avoid self-dependency
        if self.instance and self.instance.pk:
            self.fields["prerequisites"].queryset = (
                self.fields["prerequisites"].queryset.exclude(pk=self.instance.pk)
            )


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["title", "release_date", "due_date", "marks", "weightage", "description"]
        widgets = {
            "release_date": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M"
            ),
            "due_date": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M"
            ),
        }
    
    def __init__(self, *args, **kwargs):
        self.lesson = kwargs.pop('lesson', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        release_date = cleaned_data.get("release_date")
        due_date = cleaned_data.get("due_date")
        
        if release_date and due_date:
            if due_date < release_date:
                raise ValidationError({
                    'due_date': 'Due date cannot be before release date.'
                })
        
        return cleaned_data
        
    def clean_weightage(self):
        weightage = self.cleaned_data.get('weightage', 0)
        
        if weightage < 0 or weightage > 100:
            raise ValidationError("Weightage must be between 0 and 100.")
        
        # Check total weightage for the lesson
        if self.lesson:
            # Get all other assignments in this lesson
            other_assignments = Assignment.objects.filter(lesson=self.lesson)
            
            # Exclude current instance if editing
            if self.instance and self.instance.pk:
                other_assignments = other_assignments.exclude(pk=self.instance.pk)
            
            # Calculate total weightage
            from decimal import Decimal
            total_weightage = sum(Decimal(str(a.weightage)) for a in other_assignments)
            total_weightage += Decimal(str(weightage))
            
            if total_weightage > 100:
                raise ValidationError(
                    f"Total weightage cannot exceed 100%. Current total with other assignments: {total_weightage}%"
                )
        
        return weightage

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class AttachmentForm(forms.ModelForm):
    # 👇 override to make it optional
    file = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={"multiple": True, "accept": "application/pdf"})
    )

    class Meta:
        model = AssignmentAttachment
        fields = ["file"]

class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ["pdf"]

    def clean_pdf(self):
        f = self.cleaned_data["pdf"]
        # Basic PDF validation (extension + content type)
        if not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Please upload a .pdf file.")
        ct = getattr(f, "content_type", "")
        if ct and ct not in ("application/pdf", "application/x-pdf"):
            raise forms.ValidationError("File must be a PDF.")
        # Optional size limit (e.g., 20MB)
        if f.size > 20 * 1024 * 1024:
            raise forms.ValidationError("PDF must be ≤ 20MB.")
        return f