from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    Project, Milestone, SubTask, Resource, UserProfile, 
    PROJECT_STATUS_CHOICES, MILESTONE_STATUS_CHOICES, TASK_STATUS_CHOICES,
    PRIORITY_CHOICES, ROLE_CHOICES
)


class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=False)
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True, initial='viewer')

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered")
        return email


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['employee_id', 'skills', 'department', 'availability', 'profile_photo']
        widgets = {
            'skills': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Comma-separated skills'}),
            'department': forms.TextInput(attrs={'placeholder': 'Department'}),
            'availability': forms.Select(),
            'profile_photo': forms.FileInput(),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['project_id', 'name', 'customer_name', 'project_manager', 'start_date', 'end_date', 'status', 'priority', 'description', 'budget']
        widgets = {
            'project_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project ID'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project Name'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'project_manager': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(choices=PROJECT_STATUS_CHOICES, attrs={'class': 'form-control'}),
            'priority': forms.Select(choices=PRIORITY_CHOICES, attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Project Description'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Budget'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project_manager'].queryset = User.objects.filter(profile__role='project_manager')


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['name', 'description', 'baseline_delivery_date', 'actual_delivery_date', 'status', 'completion_percentage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Milestone Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'baseline_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actual_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(choices=MILESTONE_STATUS_CHOICES, attrs={'class': 'form-control'}),
            'completion_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }


class SubTaskForm(forms.ModelForm):
    class Meta:
        model = SubTask
        fields = ['name', 'description', 'assigned_to', 'start_date', 'due_date', 'status', 'priority', 'estimated_effort', 'actual_effort', 'dependency', 'comments']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(choices=TASK_STATUS_CHOICES, attrs={'class': 'form-control'}),
            'priority': forms.Select(choices=PRIORITY_CHOICES, attrs={'class': 'form-control'}),
            'estimated_effort': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Hours'}),
            'actual_effort': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Hours'}),
            'dependency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dependent Task ID'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Comments'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(profile__role__in=['engineer', 'project_manager'])


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['employee_id', 'skill_set', 'department', 'projects', 'availability']
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee ID'}),
            'skill_set': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Comma-separated skills'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'projects': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'availability': forms.Select(attrs={'class': 'form-control'}),
        }
