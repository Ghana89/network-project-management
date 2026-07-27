from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Role Choices
ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('project_manager', 'Project Manager'),
    ('engineer', 'Resource/Engineer'),
    ('viewer', 'Viewer/Stakeholder'),
]

PROJECT_STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('on_hold', 'On Hold'),
    ('completed', 'Completed'),
    ('archived', 'Archived'),
]

MILESTONE_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('delayed', 'Delayed'),
]

TASK_STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('on_hold', 'On Hold'),
    ('delayed', 'Delayed'),
]

PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]


class UserProfile(models.Model):
    """Extended user profile with role and skills"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    mobile_number = models.CharField(max_length=20, blank=True, null=True, help_text="Mobile number for the user")
    skills = models.TextField(blank=True, null=True, help_text="Comma-separated skills")
    department = models.CharField(max_length=100, blank=True, null=True)
    availability = models.CharField(max_length=50, default='available', choices=[
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('on_leave', 'On Leave'),
    ])
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="Mobile number with country code")
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when user was deleted")
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_users', help_text="Admin who deleted the user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def soft_delete(self, deleted_by_user=None):
        """Soft delete the user profile"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by_user
        self.save()

    def restore(self):
        """Restore a soft deleted user"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()


class Project(models.Model):
    """Project model"""
    project_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255)
    project_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_projects')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='not_started')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    description = models.TextField(blank=True, null=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.project_id} - {self.name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    @property
    def progress_percentage(self):
        """Calculate project completion percentage"""
        milestones = self.milestones.all()
        if not milestones.exists():
            return 0
        avg_completion = sum([m.completion_percentage for m in milestones]) / len(milestones)
        return round(avg_completion)

    @property
    def is_overdue(self):
        """Check if project is overdue"""
        return self.end_date < timezone.now().date() and self.status != 'completed'


class Milestone(models.Model):
    """Milestone model"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    baseline_delivery_date = models.DateField()
    actual_delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=MILESTONE_STATUS_CHOICES, default='pending')
    completion_percentage = models.IntegerField(default=0, help_text="0-100")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    class Meta:
        ordering = ['order', 'baseline_delivery_date']
        verbose_name = "Milestone"
        verbose_name_plural = "Milestones"

    @property
    def is_overdue(self):
        """Check if milestone is overdue"""
        return self.baseline_delivery_date < timezone.now().date() and self.status != 'completed'

    @property
    def days_remaining(self):
        """Calculate days remaining"""
        delta = self.baseline_delivery_date - timezone.now().date()
        return delta.days


class SubTask(models.Model):
    """Sub-task model"""
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='sub_tasks')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    start_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='not_started')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    estimated_effort = models.IntegerField(help_text="Estimated effort in hours", default=0)
    actual_effort = models.IntegerField(help_text="Actual effort in hours", default=0, blank=True)
    dependency = models.CharField(max_length=255, blank=True, null=True, help_text="Dependent task ID")
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.milestone.name} - {self.name}"

    class Meta:
        ordering = ['due_date', 'priority']
        verbose_name = "Sub Task"
        verbose_name_plural = "Sub Tasks"

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        return self.due_date < timezone.now().date() and self.status not in ['completed', 'on_hold']

    @property
    def days_remaining(self):
        """Calculate days remaining"""
        delta = self.due_date - timezone.now().date()
        return delta.days


class Resource(models.Model):
    """Resource/Team member model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resource')
    employee_id = models.CharField(max_length=50, unique=True)
    skill_set = models.TextField(help_text="Comma-separated skills")
    department = models.CharField(max_length=100)
    projects = models.ManyToManyField(Project, related_name='team_members', blank=True)
    availability = models.CharField(max_length=50, choices=[
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('on_leave', 'On Leave'),
    ], default='available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"

    class Meta:
        verbose_name = "Resource"
        verbose_name_plural = "Resources"

    @property
    def assigned_tasks_count(self):
        """Count assigned tasks"""
        return self.user.assigned_tasks.exclude(status='completed').count()

    @property
    def workload(self):
        """Calculate total estimated effort"""
        tasks = self.user.assigned_tasks.exclude(status='completed')
        return sum([task.estimated_effort for task in tasks])


class Notification(models.Model):
    """Notification model for task assignments and updates"""
    NOTIFICATION_TYPES = [
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('milestone_completed', 'Milestone Completed'),
        ('project_update', 'Project Update'),
        ('task_overdue', 'Task Overdue'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_task = models.ForeignKey(SubTask, on_delete=models.SET_NULL, null=True, blank=True)
    related_milestone = models.ForeignKey(Milestone, on_delete=models.SET_NULL, null=True, blank=True)
    related_project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ProjectAccess(models.Model):
    """Model to manage project access permissions for users"""
    ACCESS_ROLES = [
        ('engineer', 'Engineer/Resource'),
        ('project_manager', 'Project Manager'),
        ('stakeholder', 'Stakeholder/Viewer'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='access_permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_access')
    access_role = models.CharField(max_length=20, choices=ACCESS_ROLES, default='engineer')
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_project_access')
    granted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'user')
        verbose_name = "Project Access"
        verbose_name_plural = "Project Access Permissions"

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.get_access_role_display()})"


class ProjectLog(models.Model):
    """Audit log for project activities"""
    # project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='logs')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Project Log"
        verbose_name_plural = "Project Logs"

    from django.db.models.signals import post_save
    from django.dispatch import receiver

    @receiver(post_save, sender=User)
    def create_or_ensure_user_profile(sender, instance, created, **kwargs):
        if created:
            try:
                UserProfile.objects.create(user=instance)
            except Exception:
                # In rare cases (migrations, partial setups) silently ignore
                pass
        else:
            UserProfile.objects.get_or_create(user=instance)

    def __str__(self):
        return f"{self.project.name} - {self.action}"
