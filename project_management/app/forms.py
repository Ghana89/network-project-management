from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    Project, Milestone, SubTask, Resource, UserProfile, ProjectAccess,
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

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # Only superusers can create admin accounts
        if current_user and not current_user.is_superuser:
            self.fields['role'].choices = [
                choice for choice in ROLE_CHOICES 
                if choice[0] != 'admin'
            ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered")
        return email

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == 'admin':
            raise forms.ValidationError("You don't have permission to create admin accounts.")
        return role


class AdminUserEditForm(forms.ModelForm):
    """Form for admins to edit user details and role (but not superuser accounts)"""
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active')

    def __init__(self, *args, **kwargs):
        self.user_being_edited = kwargs.pop('user_being_edited', None)
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate role from UserProfile if available
        if self.user_being_edited and hasattr(self.user_being_edited, 'profile'):
            self.fields['role'].initial = self.user_being_edited.profile.role
        
        # Only superusers can change roles to/from admin
        if self.current_user and not self.current_user.is_superuser:
            self.fields['role'].choices = [
                choice for choice in ROLE_CHOICES 
                if choice[0] != 'admin'
            ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Allow the same email or check if new email is unique
        if self.instance and email == self.instance.email:
            return email
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered")
        return email

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == 'admin':
            raise forms.ValidationError("You don't have permission to assign admin role.")
        return role

    def clean(self):
        cleaned_data = super().clean()
        # Prevent editing superuser accounts
        if self.instance and self.instance.is_superuser:
            raise forms.ValidationError("Superuser accounts cannot be edited.")
        return cleaned_data


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(required=True, label='Email Address')


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['employee_id', 'phone_number', 'skills', 'department', 'availability', 'profile_photo']
        widgets = {
            'mobile_number': forms.TextInput(attrs={'placeholder': 'Mobile number'}),
            'skills': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Comma-separated skills'}),
            'department': forms.TextInput(attrs={'placeholder': 'Department'}),
            'availability': forms.Select(),
            'profile_photo': forms.FileInput(),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'project_id', 'name', 'customer_name', 'project_manager',
            'start_date', 'end_date', 'status', 'priority',
            'description', 'budget'
        ]

        widgets = {
            'project_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Project ID'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Project Name'
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer Name'
            }),
            'project_manager': forms.Select(attrs={
                'class': 'form-control'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        self.fields['project_manager'].queryset = User.objects.filter(
            profile__role='project_manager'
        )

        if (
            self.current_user
            and hasattr(self.current_user, 'profile')
            and self.current_user.profile.role == 'project_manager'
            and not self.current_user.is_superuser
        ):
            self.fields['project_manager'].initial = self.current_user
            self.fields['project_manager'].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        if (
            self.current_user
            and hasattr(self.current_user, 'profile')
            and self.current_user.profile.role == 'project_manager'
            and not self.current_user.is_superuser
        ):
            cleaned_data['project_manager'] = self.current_user

        return cleaned_data

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


class ProjectAccessForm(forms.ModelForm):
    """Form for granting project access to users"""
    user = forms.ModelChoiceField(
        queryset=User.objects.exclude(is_superuser=True),
        label='Select User',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select a user to grant project access'
    )

    class Meta:
        model = ProjectAccess
        fields = ['user', 'access_role']
        widgets = {
            'access_role': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'access_role': 'Access Role',
        }

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Filter out users who already have access to this project
        if self.project:
            existing_users = ProjectAccess.objects.filter(project=self.project).values_list('user_id', flat=True)
            self.fields['user'].queryset = User.objects.exclude(id__in=existing_users).exclude(is_superuser=True)


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
