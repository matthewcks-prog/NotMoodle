from django import forms
from .models import Course, CourseLesson
from lesson_management.models import Lesson
from teachersManagement.models import TeacherProfile

class CourseForm(forms.ModelForm):
    director_name = forms.CharField(
        label="Director",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Type a director's name"})
    )
    core_units = forms.ModelMultipleChoiceField(
        label="Core units",
        queryset=Lesson.objects.filter(status='published').order_by('unit_code'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )

    class Meta:
        model = Course
        fields = ['code', 'name', 'description', 'total_credits_required', 'status', 'director_name', 'core_units']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CS101'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Introduction to Computer Science'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Course description...'}),
            'total_credits_required': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 1000}),
            'status': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Default director to the logged-in teacher when creating a course
        if request is not None and not self.instance.pk:
            profile = getattr(getattr(request, 'user', None), 'teacherprofile', None) or getattr(getattr(request, 'user', None), 'teacher_profile', None)
            if profile:
                self.fields['director_name'].initial = profile.get_full_name()
        if self.instance.pk:
            # Pre-populate core_units for existing courses
            self.fields['core_units'].initial = [
                cl.lesson for cl in self.instance.course_lessons.all()
            ]

class CourseLessonForm(forms.ModelForm):
    class Meta:
        model = CourseLesson
        fields = ['lesson', 'order', 'is_required']
        widgets = {
            'lesson': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_required': forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show published lessons
        self.fields['lesson'].queryset = Lesson.objects.filter(status='published').order_by('unit_code')
