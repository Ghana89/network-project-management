from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from .models import (
    Project, Milestone, SubTask, Resource, UserProfile, Notification, ProjectLog,
    PROJECT_STATUS_CHOICES, MILESTONE_STATUS_CHOICES, TASK_STATUS_CHOICES,
    PRIORITY_CHOICES
)
from .forms import (
    AdminUserCreationForm, UserProfileForm, ProjectForm, MilestoneForm,
    SubTaskForm, ResourceForm
)


# Helper functions to check user role
def is_admin(user):
    return user.profile.role == 'admin'


def is_project_manager(user):
    return user.profile.role in ['project_manager', 'admin']


def is_engineer(user):
    return user.profile.role in ['engineer', 'project_manager', 'admin']


# Authentication Views
@login_required
@user_passes_test(is_admin)
def user_management(request):
    users = User.objects.all().order_by('-date_joined')
    context = {'users': users}
    return render(request, 'users/user_list.html', context)


@login_required
@user_passes_test(is_admin)
def user_create(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            # Create profile with selected role
            UserProfile.objects.create(user=user, role=role)
            return redirect('user_management')
    else:
        form = AdminUserCreationForm()
    return render(request, 'users/user_create.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            return render(request, 'auth/login.html', {'error': 'Invalid credentials'})
    return render(request, 'auth/login.html')


def user_logout(request):
    logout(request)
    return redirect('login')




# Dashboard View
@login_required
def dashboard(request):
    user_profile = request.user.profile
    context = {}

    if user_profile.role == 'admin':
        context['total_projects'] = Project.objects.count()
        context['active_projects'] = Project.objects.exclude(status__in=['completed', 'archived']).count()
        context['total_users'] = User.objects.count()
        context['total_resources'] = Resource.objects.count()
    elif user_profile.role == 'project_manager':
        context['managed_projects'] = Project.objects.filter(project_manager=request.user)
        context['total_projects'] = context['managed_projects'].count()
        context['active_projects'] = context['managed_projects'].exclude(status__in=['completed', 'archived']).count()
    elif user_profile.role == 'engineer':
        context['assigned_tasks'] = SubTask.objects.filter(assigned_to=request.user).exclude(status='completed')
        context['completed_tasks'] = SubTask.objects.filter(assigned_to=request.user, status='completed').count()
    else:  # viewer
        context['active_projects'] = Project.objects.exclude(status__in=['completed', 'archived'])

    # Common dashboard widgets
    context['upcoming_milestones'] = Milestone.objects.filter(
        baseline_delivery_date__gte=timezone.now().date()
    ).order_by('baseline_delivery_date')[:5]
    
    context['overdue_tasks'] = SubTask.objects.filter(
        due_date__lt=timezone.now().date(),
        status__in=['not_started', 'in_progress', 'delayed']
    )
    
    context['overdue_milestones'] = Milestone.objects.filter(
        baseline_delivery_date__lt=timezone.now().date(),
        status__in=['pending', 'in_progress']
    )
    
    context['unread_notifications'] = request.user.notifications.filter(is_read=False).count()

    return render(request, 'dashboard/dashboard.html', context)


# Project Views
@login_required
@user_passes_test(is_project_manager)
def project_list(request):
    if request.user.profile.role == 'admin':
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(project_manager=request.user)

    # Filtering
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    search = request.GET.get('search')

    if status:
        projects = projects.filter(status=status)
    if priority:
        projects = projects.filter(priority=priority)
    if search:
        projects = projects.filter(Q(name__icontains=search) | Q(project_id__icontains=search))

    paginator = Paginator(projects, 10)
    page = request.GET.get('page')
    projects = paginator.get_page(page)

    context = {
        'projects': projects,
        'status_choices': PROJECT_STATUS_CHOICES,
        'priority_choices': PRIORITY_CHOICES,
        'search': search,
        'status': status,
        'priority': priority,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
@user_passes_test(is_project_manager)
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            ProjectLog.objects.create(
                project=project,
                user=request.user,
                action='Project Created',
                description=f'Project {project.name} created'
            )
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Create Project'})


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Check permissions
    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        if request.user.profile.role == 'viewer':
            pass  # Viewers can see project details
        else:
            return redirect('dashboard')

    milestones = project.milestones.all()
    context = {
        'project': project,
        'milestones': milestones,
        'project_progress': project.progress_percentage,
        'overdue_milestones': [m for m in milestones if m.is_overdue],
        'upcoming_milestones': milestones.filter(baseline_delivery_date__gte=timezone.now().date()),
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
@user_passes_test(is_project_manager)
def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            ProjectLog.objects.create(
                project=project,
                user=request.user,
                action='Project Updated',
                description=f'Project {project.name} updated'
            )
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Edit Project', 'project': project})


@login_required
@user_passes_test(is_project_manager)
def project_archive(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        project.is_archived = True
        project.status = 'archived'
        project.save()
        ProjectLog.objects.create(
            project=project,
            user=request.user,
            action='Project Archived',
            description=f'Project {project.name} archived'
        )
        return redirect('project_list')

    return render(request, 'projects/project_archive.html', {'project': project})


# Milestone Views
@login_required
@user_passes_test(is_project_manager)
def milestone_create(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        form = MilestoneForm(request.POST)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.project = project
            milestone.order = project.milestones.count()
            milestone.save()
            ProjectLog.objects.create(
                project=project,
                user=request.user,
                action='Milestone Created',
                description=f'Milestone {milestone.name} created'
            )
            return redirect('project_detail', project_id=project.id)
    else:
        form = MilestoneForm()

    return render(request, 'milestones/milestone_form.html', {'form': form, 'title': 'Create Milestone', 'project': project})


@login_required
@user_passes_test(is_project_manager)
def milestone_edit(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id)
    project = milestone.project

    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        form = MilestoneForm(request.POST, instance=milestone)
        if form.is_valid():
            milestone = form.save()
            ProjectLog.objects.create(
                project=project,
                user=request.user,
                action='Milestone Updated',
                description=f'Milestone {milestone.name} updated'
            )
            return redirect('project_detail', project_id=project.id)
    else:
        form = MilestoneForm(instance=milestone)

    return render(request, 'milestones/milestone_form.html', {'form': form, 'title': 'Edit Milestone', 'project': project})


@login_required
@user_passes_test(is_project_manager)
def milestone_delete(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id)
    project = milestone.project

    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        milestone_name = milestone.name
        milestone.delete()
        ProjectLog.objects.create(
            project=project,
            user=request.user,
            action='Milestone Deleted',
            description=f'Milestone {milestone_name} deleted'
        )
        return redirect('project_detail', project_id=project.id)

    return render(request, 'milestones/milestone_delete.html', {'milestone': milestone})


@login_required
def milestone_detail(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id)
    sub_tasks = milestone.sub_tasks.all()

    context = {
        'milestone': milestone,
        'sub_tasks': sub_tasks,
        'task_status_choices': TASK_STATUS_CHOICES,
    }
    return render(request, 'milestones/milestone_detail.html', context)


# SubTask Views
@login_required
@user_passes_test(is_project_manager)
def subtask_create(request, milestone_id):
    milestone = get_object_or_404(Milestone, id=milestone_id)

    if request.user.profile.role not in ['admin'] and milestone.project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SubTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.milestone = milestone
            task.save()
            
            # Create notification for assigned resource
            if task.assigned_to:
                Notification.objects.create(
                    user=task.assigned_to,
                    notification_type='task_assigned',
                    title=f'New Task Assigned: {task.name}',
                    message=f'You have been assigned to task "{task.name}" in milestone "{milestone.name}"',
                    related_task=task
                )

            ProjectLog.objects.create(
                project=milestone.project,
                user=request.user,
                action='Sub-Task Created',
                description=f'Task {task.name} created under milestone {milestone.name}'
            )
            return redirect('milestone_detail', milestone_id=milestone.id)
    else:
        form = SubTaskForm()

    return render(request, 'subtasks/subtask_form.html', {'form': form, 'title': 'Create Task', 'milestone': milestone})


@login_required
@user_passes_test(is_engineer)
def subtask_edit(request, task_id):
    task = get_object_or_404(SubTask, id=task_id)
    project = task.milestone.project

    # Check permissions
    if request.user.profile.role not in ['admin'] and project.project_manager != request.user and task.assigned_to != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SubTaskForm(request.POST, instance=task)
        if form.is_valid():
            old_status = task.status
            old_assigned = task.assigned_to
            
            task = form.save()

            # Create notification if status changed
            if old_status != task.status and task.assigned_to:
                Notification.objects.create(
                    user=task.assigned_to,
                    notification_type='task_updated',
                    title=f'Task Status Updated: {task.name}',
                    message=f'Task "{task.name}" status changed from {old_status} to {task.status}',
                    related_task=task
                )

            # Create notification if assignment changed
            if old_assigned != task.assigned_to and task.assigned_to:
                Notification.objects.create(
                    user=task.assigned_to,
                    notification_type='task_assigned',
                    title=f'Task Assigned: {task.name}',
                    message=f'You have been assigned to task "{task.name}"',
                    related_task=task
                )

            ProjectLog.objects.create(
                project=project,
                user=request.user,
                action='Sub-Task Updated',
                description=f'Task {task.name} updated'
            )
            return redirect('milestone_detail', milestone_id=task.milestone.id)
    else:
        form = SubTaskForm(instance=task)

    return render(request, 'subtasks/subtask_form.html', {'form': form, 'title': 'Edit Task', 'task': task})


@login_required
@user_passes_test(is_project_manager)
def subtask_delete(request, task_id):
    task = get_object_or_404(SubTask, id=task_id)
    project = task.milestone.project

    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        task_name = task.name
        milestone_id = task.milestone.id
        task.delete()
        ProjectLog.objects.create(
            project=project,
            user=request.user,
            action='Sub-Task Deleted',
            description=f'Task {task_name} deleted'
        )
        return redirect('milestone_detail', milestone_id=milestone_id)

    return render(request, 'subtasks/subtask_delete.html', {'task': task})


@login_required
def subtask_detail(request, task_id):
    task = get_object_or_404(SubTask, id=task_id)
    return render(request, 'subtasks/subtask_detail.html', {'task': task})


# Resource Views
@login_required
@user_passes_test(is_admin)
def resource_list(request):
    resources = Resource.objects.all()
    search = request.GET.get('search')

    if search:
        resources = resources.filter(Q(employee_id__icontains=search) | Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search))

    paginator = Paginator(resources, 10)
    page = request.GET.get('page')
    resources = paginator.get_page(page)

    context = {'resources': resources, 'search': search}
    return render(request, 'resources/resource_list.html', context)


@login_required
@user_passes_test(is_admin)
def resource_detail(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    assigned_tasks = resource.user.assigned_tasks.exclude(status='completed')
    completed_tasks = resource.user.assigned_tasks.filter(status='completed').count()

    context = {
        'resource': resource,
        'assigned_tasks': assigned_tasks,
        'completed_tasks': completed_tasks,
        'total_workload': resource.workload,
        'projects': resource.projects.all(),
    }
    return render(request, 'resources/resource_detail.html', context)


# Notifications
@login_required
def notifications(request):
    user_notifications = request.user.notifications.all()
    unread = user_notifications.filter(is_read=False)

    paginator = Paginator(user_notifications, 10)
    page = request.GET.get('page')
    notifications_page = paginator.get_page(page)

    context = {
        'notifications': notifications_page,
        'unread_count': unread.count(),
    }
    return render(request, 'notifications/notifications.html', context)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})


# Reports
@login_required
@user_passes_test(lambda u: u.profile.role in ['admin', 'project_manager'])
def project_status_report(request):
    if request.user.profile.role == 'admin':
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(project_manager=request.user)

    context = {'projects': projects}
    return render(request, 'reports/project_status_report.html', context)


@login_required
@user_passes_test(lambda u: u.profile.role in ['admin', 'project_manager'])
def milestone_report(request):
    if request.user.profile.role == 'admin':
        milestones = Milestone.objects.all()
    else:
        milestones = Milestone.objects.filter(project__project_manager=request.user)

    context = {'milestones': milestones}
    return render(request, 'reports/milestone_report.html', context)


@login_required
@user_passes_test(lambda u: u.profile.role in ['admin', 'project_manager'])
def delayed_tasks_report(request):
    delayed_tasks = SubTask.objects.filter(
        status__in=['not_started', 'in_progress', 'delayed'],
        due_date__lt=timezone.now().date()
    )

    context = {'delayed_tasks': delayed_tasks}
    return render(request, 'reports/delayed_tasks_report.html', context)


@login_required
@user_passes_test(lambda u: u.profile.role in ['admin', 'project_manager'])
def resource_utilization_report(request):
    resources = Resource.objects.annotate(
        total_tasks=Count('user__assigned_tasks')
    ).all()

    context = {'resources': resources}
    return render(request, 'reports/resource_utilization_report.html', context)


# PDF Export
@login_required
def export_project_pdf(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#003366',
        spaceAfter=30,
    )

    elements.append(Paragraph(f"Project Report: {project.name}", title_style))
    elements.append(Spacer(1, 0.3*inch))

    # Project Details
    project_data = [
        ['Project ID', project.project_id],
        ['Customer', project.customer_name],
        ['Status', project.get_status_display()],
        ['Priority', project.get_priority_display()],
        ['Start Date', project.start_date.strftime('%Y-%m-%d')],
        ['End Date', project.end_date.strftime('%Y-%m-%d')],
        ['Progress', f"{project.progress_percentage}%"],
    ]

    table = Table(project_data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), '#E0E0E0'),
        ('TEXTCOLOR', (0, 0), (-1, -1), '#000000'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, '#CCCCCC'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))

    # Milestones
    elements.append(Paragraph("Milestones", styles['Heading2']))
    milestone_data = [['Milestone', 'Status', 'Delivery Date', 'Completion %']]
    for milestone in project.milestones.all():
        milestone_data.append([
            milestone.name,
            milestone.get_status_display(),
            milestone.baseline_delivery_date.strftime('%Y-%m-%d'),
            f"{milestone.completion_percentage}%"
        ])

    table = Table(milestone_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#003366'),
        ('TEXTCOLOR', (0, 0), (-1, 0), '#FFFFFF'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, '#CCCCCC'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="project_report_{project.project_id}.pdf"'
    return response


# Settings/Profile
@login_required
def profile_view(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user_profile)

    context = {'form': form, 'user_profile': user_profile}
    return render(request, 'profile/profile.html', context)


# API endpoints for AJAX
@login_required
@require_http_methods(["GET"])
def api_get_task_stats(request):
    """Get task statistics for dashboard"""
    if request.user.profile.role == 'engineer':
        total = SubTask.objects.filter(assigned_to=request.user).count()
        completed = SubTask.objects.filter(assigned_to=request.user, status='completed').count()
        in_progress = SubTask.objects.filter(assigned_to=request.user, status='in_progress').count()
        overdue = SubTask.objects.filter(
            assigned_to=request.user,
            due_date__lt=timezone.now().date(),
            status__in=['not_started', 'in_progress']
        ).count()
    else:
        total = SubTask.objects.count()
        completed = SubTask.objects.filter(status='completed').count()
        in_progress = SubTask.objects.filter(status='in_progress').count()
        overdue = SubTask.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=['not_started', 'in_progress']
        ).count()

    return JsonResponse({
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'overdue': overdue,
    })


@login_required
@require_http_methods(["GET"])
def api_project_progress(request, project_id):
    """Get project progress data"""
    project = get_object_or_404(Project, id=project_id)
    milestones = project.milestones.all()

    data = {
        'project_name': project.name,
        'overall_progress': project.progress_percentage,
        'milestones': [
            {
                'name': m.name,
                'progress': m.completion_percentage,
                'status': m.status,
            }
            for m in milestones
        ]
    }
    return JsonResponse(data)
