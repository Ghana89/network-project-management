from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import EmailMessage, get_connection, send_mail
import logging
import smtplib
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.conf import settings
from django.urls import reverse
from datetime import timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from .models import (
    Project, Milestone, SubTask, Resource, UserProfile, Notification, ProjectLog, ProjectAccess,
    PROJECT_STATUS_CHOICES, MILESTONE_STATUS_CHOICES, TASK_STATUS_CHOICES,
    PRIORITY_CHOICES, ROLE_CHOICES
)
from .forms import (
    AdminUserCreationForm, AdminUserEditForm, ForgotPasswordForm, UserProfileForm, ProjectForm,
    MilestoneForm, SubTaskForm, ResourceForm, ProjectAccessForm
)


import logging
logger = logging.getLogger(__name__)

# Helper functions to check user role
def is_admin(user):
    return user.profile.role == 'admin'


def is_project_manager(user):
    return user.profile.role in ['project_manager', 'admin']


def is_engineer(user):
    return user.profile.role in ['engineer', 'project_manager', 'admin']


# Home View
def home(request):
    """Home page for unauthenticated users"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


# Authentication Views
@login_required
@user_passes_test(is_admin)
def user_management(request):
    active_users = User.objects.filter(profile__is_deleted=False).order_by('-date_joined')
    deleted_count = UserProfile.objects.filter(is_deleted=True).count()
    context = {
        'users': active_users,
        'deleted_count': deleted_count,
    }
    return render(request, 'users/user_list.html', context)


@login_required
@user_passes_test(is_admin)
def user_create(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST, current_user=request.user)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            # Update profile with selected role (post_save signal creates it automatically)
            profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
            if not created:
                profile.role = role
                profile.save()

            # Send welcome email with password-setup link when an email is provided
            if user.email:
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                setup_link = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
                )
                subject = 'Welcome to Network Project Management — set your password'
                message = (
                    f'Hi {user.get_full_name() or user.username},\n\n'
                    f'An account was created for you at Network Project Management.\n'
                    f'Username: {user.username}\n\n'
                    f'Please set your password using the link below:\n{setup_link}\n\n'
                    'If you did not expect this email, please contact the administrator.'
                )

                email_sent = False
                try:
                    logger.info(f'Sending welcome email to {user.email} (backend: {settings.EMAIL_BACKEND})')
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                    email_sent = True
                    logger.info(f'Welcome email sent successfully to {user.email}')
                    messages.success(request, f'User created successfully! Welcome email sent to {user.email}.')
                except Exception as e:
                    logger.exception(f'Failed to send welcome email to {user.email}: {str(e)}')
                    
                    # In DEBUG, also print to console backend as a fallback
                    if settings.DEBUG and settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                        try:
                            logger.info('Attempting fallback to console backend...')
                            console_connection = get_connection('django.core.mail.backends.console.EmailBackend')
                            email_message = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                            console_connection.send_messages([email_message])
                            email_sent = True
                            logger.info(f'Welcome email printed to console for {user.email}')
                        except Exception as fallback_e:
                            logger.exception(f'Fallback console backend also failed: {str(fallback_e)}')
                            email_sent = False

                if not email_sent:
                    messages.warning(request, f'User created but welcome email to {user.email} could not be sent. Please contact support.')
            else:
                messages.info(request, f'User created but no email address provided.')


            return redirect('user_management')
    else:
        form = AdminUserCreationForm(current_user=request.user)
    return render(request, 'users/user_create.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def user_edit(request, user_id):
    """Edit user details and role (cannot edit superuser accounts)"""
    user_to_edit = get_object_or_404(User, id=user_id)
    
    # Prevent editing superuser accounts
    if user_to_edit.is_superuser:
        messages.error(request, 'Superuser accounts cannot be edited by regular admins.')
        return redirect('user_management')
    
    # Get current role before edit
    old_role = user_to_edit.profile.role if hasattr(user_to_edit, 'profile') else None
    
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=user_to_edit, user_being_edited=user_to_edit, current_user=request.user)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            
            # Update profile role
            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
            profile.role = role
            profile.save()
            
            messages.success(request, f'User {user.username} updated successfully.')
            
            # Send email notification if user has email
            if user.email:
                role_changed = old_role != role
                subject = 'Your Network Project Management Account Was Updated'
                message = (
                    f'Hi {user.get_full_name() or user.username},\n\n'
                    f'Your account at Network Project Management was updated.\n\n'
                    f'Updated Details:\n'
                    f'  • Username: {user.username}\n'
                    f'  • Email: {user.email}\n'
                    f'  • Name: {user.get_full_name() or "—"}\n'
                )
                
                if role_changed:
                    message += f'  • Role: {dict(ROLE_CHOICES).get(role, role)} (changed from {dict(ROLE_CHOICES).get(old_role, old_role)})\n'
                else:
                    message += f'  • Role: {dict(ROLE_CHOICES).get(role, role)}\n'
                
                message += f'\n  • Account Status: {"Active" if user.is_active else "Inactive"}\n'
                message += '\nIf you have questions about these changes, please contact the administrator.'
                
                try:
                    logger.info(f'Sending account update email to {user.email}')
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                    logger.info(f'Account update email sent successfully to {user.email}')
                    if role_changed:
                        messages.info(request, f'Update notification email sent to {user.email}.')
                except Exception as e:
                    logger.exception(f'Failed to send account update email to {user.email}: {str(e)}')
                    
                    # Fallback to console backend in DEBUG mode
                    if settings.DEBUG and settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                        try:
                            logger.info('Attempting fallback to console backend...')
                            console_connection = get_connection('django.core.mail.backends.console.EmailBackend')
                            email_message = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                            console_connection.send_messages([email_message])
                            logger.info(f'Account update email printed to console for {user.email}')
                        except Exception as fallback_e:
                            logger.exception(f'Fallback console backend also failed: {str(fallback_e)}')
            
            return redirect('user_management')
    else:
        form = AdminUserEditForm(instance=user_to_edit, user_being_edited=user_to_edit, current_user=request.user)
    
    return render(request, 'users/user_edit.html', {'form': form, 'user': user_to_edit})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is None and username:
            user_by_email = User.objects.filter(email__iexact=username).first()
            if user_by_email:
                user = authenticate(request, username=user_by_email.username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            return render(request, 'auth/login.html', {'error': 'Invalid credentials'})
    return render(request, 'auth/login.html')


def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email__iexact=email).first()
            if user:
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_link = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
                )
                subject = 'Reset your Network Project Management password'
                message = (
                    f'Hi {user.get_full_name() or user.username},\n\n'
                    f'Use the link below to reset your password:\n{reset_link}\n\n'
                    'If you did not request this, you can safely ignore this email.'
                )
                email_sent = False
                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                    email_sent = True
                except (smtplib.SMTPException, Exception) as exc:
                    logger = logging.getLogger(__name__)
                    logger.exception('Failed to send password reset email for %s', user.email)
                    # If in DEBUG and SMTP failed, fall back to console backend for local testing.
                    if settings.DEBUG and settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                        try:
                            console_connection = get_connection('django.core.mail.backends.console.EmailBackend')
                            email_message = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                            console_connection.send_messages([email_message])
                            email_sent = True
                        except Exception:
                            email_sent = False
                    else:
                        email_sent = False

            # If email was sent show generic success; if sending failed show a friendly error
            if 'email_sent' in locals() and not email_sent:
                return render(request, 'auth/forgot_password.html', {
                    'form': form,
                    'success': False,
                    'email': email,
                    'error': 'Unable to send reset email right now. Please contact support or try again later.'
                })

            return render(request, 'auth/forgot_password.html', {
                'form': form,
                'success': True,
                'email': email,
            })
    else:
        form = ForgotPasswordForm()

    return render(request, 'auth/forgot_password.html', {'form': form, 'success': False})


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully. Please sign in with your new password.')
                return redirect('login')
        else:
            form = SetPasswordForm(user)

        return render(request, 'auth/password_reset_confirm.html', {'form': form, 'validlink': True})

    return render(request, 'auth/password_reset_confirm.html', {'validlink': False})


def user_logout(request):
    logout(request)
    return redirect('login')


# User Soft Delete Views
@login_required
@user_passes_test(is_admin)
def user_soft_delete(request, user_id):
    """Soft delete a user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Prevent admin from deleting themselves
        if user == request.user:
            return redirect('user_management')
        
        user.profile.soft_delete(deleted_by_user=request.user)
        ProjectLog.objects.create(
            project=None,
            user=request.user,
            action='User Deleted',
            description=f'User {user.username} has been soft deleted'
        )
        return redirect('user_management')
    
    return render(request, 'users/user_confirm_delete.html', {'user': user})


@login_required
@user_passes_test(is_admin)
def deleted_users(request):
    """View deleted users"""
    deleted_users_list = UserProfile.objects.filter(is_deleted=True).select_related('user', 'deleted_by')
    context = {'deleted_users': deleted_users_list}
    return render(request, 'users/deleted_users.html', context)


@login_required
@user_passes_test(is_admin)
def restore_user(request, user_id):
    """Restore a soft deleted user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.profile.restore()
        ProjectLog.objects.create(
            project=None,
            user=request.user,
            action='User Restored',
            description=f'User {user.username} has been restored'
        )
        return redirect('deleted_users')
    
    return render(request, 'users/user_confirm_restore.html', {'user': user})


# Dashboard View
@login_required
def dashboard(request):
    # Ensure a profile exists for the user; fallback to a default role if needed.
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user, defaults={'role': 'viewer'})
    context = {}

    if user_profile.role == 'admin':
        context['total_projects'] = Project.objects.count()
        context['active_projects'] = Project.objects.exclude(status__in=['completed', 'archived']).count()
        context['total_users'] = User.objects.filter(profile__is_deleted=False).count()
        context['deleted_users'] = UserProfile.objects.filter(is_deleted=True).count()
        context['total_resources'] = Resource.objects.count()
        context['overdue_tasks'] = SubTask.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=['not_started', 'in_progress', 'delayed']
        )
        context['completed_tasks'] = SubTask.objects.filter(status='completed').count()
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
        projects_queryset = Project.objects.all()
    elif request.user.profile.role == 'project_manager':
        projects_queryset = Project.objects.filter(project_manager=request.user)
    else:
        # Engineers and other roles: only see projects they have access to
        projects_queryset = Project.objects.filter(
            access_permissions__user=request.user
        ).distinct()

    # Calculate global dashboard metrics for the user's project portfolio
    total_projects_count = projects_queryset.count()
    active_projects_count = projects_queryset.exclude(status__in=['completed', 'archived']).count()
    completed_projects_count = projects_queryset.filter(status='completed').count()
    critical_projects_count = projects_queryset.filter(priority='critical').count()
    
    all_projects_list = list(projects_queryset)
    average_progress = 0
    if all_projects_list:
        average_progress = round(sum(p.progress_percentage for p in all_projects_list) / len(all_projects_list))

    # Filtering for the current search
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    search = request.GET.get('search')

    filtered_projects = projects_queryset
    if status:
        filtered_projects = filtered_projects.filter(status=status)
    if priority:
        filtered_projects = filtered_projects.filter(priority=priority)
    if search:
        filtered_projects = filtered_projects.filter(Q(name__icontains=search) | Q(project_id__icontains=search))

    # Store full list of filtered projects for the Kanban Board view
    board_projects = list(filtered_projects)

    # Paginate for the Grid/List view
    paginator = Paginator(filtered_projects, 9) # 9 fits perfectly in a 3-column grid
    page = request.GET.get('page')
    paginated_projects = paginator.get_page(page)

    context = {
        'projects': paginated_projects,
        'board_projects': board_projects,
        'status_choices': PROJECT_STATUS_CHOICES,
        'priority_choices': PRIORITY_CHOICES,
        'search': search,
        'status': status,
        'priority': priority,
        'metrics': {
            'total': total_projects_count,
            'active': active_projects_count,
            'completed': completed_projects_count,
            'critical': critical_projects_count,
            'average_progress': average_progress,
        }
    }
    return render(request, 'projects/project_list.html', context)


@login_required
@user_passes_test(is_project_manager)
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, current_user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            
            # If current user is a project manager, set them as the project manager
            if request.user.profile.role == 'project_manager':
                project.project_manager = request.user
            
            project.save()
            ProjectLog.objects.create(
                project=project,
                user=request.user,
                action='Project Created',
                description=f'Project {project.name} created'
            )
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(current_user=request.user)

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
def project_access_manage(request, project_id):
    """Manage project access for users"""
    project = get_object_or_404(Project, id=project_id)
    
    # Only admins and project managers can manage access
    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        messages.error(request, 'You do not have permission to manage access for this project.')
        return redirect('project_detail', project_id=project.id)
    
    current_access = project.access_permissions.all()
    
    if request.method == 'POST':
        form = ProjectAccessForm(request.POST, project=project)
        if form.is_valid():
            access = form.save(commit=False)
            access.project = project
            access.granted_by = request.user
            access.save()
            
            # Send notification to user about project access
            user_fullname = access.user.get_full_name() or access.user.username
            Notification.objects.create(
                user=access.user,
                notification_type='project_access_granted',
                title=f'Access Granted: {project.name}',
                message=f'You have been granted {access.get_access_role_display()} access to project "{project.name}"',
                related_project=project
            )
            
            messages.success(request, f'Access granted to {user_fullname} as {access.get_access_role_display()}.')
            return redirect('project_access_manage', project_id=project.id)
    else:
        form = ProjectAccessForm(project=project)
    
    context = {
        'project': project,
        'form': form,
        'current_access': current_access,
    }
    return render(request, 'projects/project_access_manage.html', context)


@login_required
@user_passes_test(is_project_manager)
def project_access_revoke(request, project_id, user_id):
    """Revoke project access for a user"""
    project = get_object_or_404(Project, id=project_id)
    access = get_object_or_404(ProjectAccess, project=project, user_id=user_id)
    
    # Only admins and project managers can revoke access
    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        messages.error(request, 'You do not have permission to revoke access.')
        return redirect('project_detail', project_id=project.id)
    
    user_fullname = access.user.get_full_name() or access.user.username
    access.delete()
    messages.success(request, f'Access revoked for {user_fullname}.')
    return redirect('project_access_manage', project_id=project.id)


@login_required
@user_passes_test(is_project_manager)
def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.user.profile.role not in ['admin'] and project.project_manager != request.user:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project, current_user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            
            # If current user is a project manager, ensure they're set as the manager
            if request.user.profile.role == 'project_manager':
                project.project_manager = request.user
            
            project.save()
            ProjectLog.objects.create(
                project=project,
                user=request.user,
                action='Project Updated',
                description=f'Project {project.name} updated'
            )
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project, current_user=request.user)

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

def error_404(request, exception):
    return render(request, 'error.html', {
        'status_code': 404,
        'title': 'Page Not Found',
        'message': "Sorry, the page you're looking for doesn't exist or has been moved."
    }, status=404)

def error_500(request):
    return render(request, 'error.html', {
        'status_code': 500,
        'title': 'Internal Server Error',
        'message': 'Something went wrong on our end. Our team has been notified.'
    }, status=500)

def error_403(request, exception=None):
    return render(request, 'error.html', {
        'status_code': 403,
        'title': 'Access Denied',
        'message': "You don't have permission to view this resource."
    }, status=403)

def error_400(request, exception=None):
    return render(request, 'error.html', {
        'status_code': 400,
        'title': 'Bad Request',
        'message': 'The server could not understand the request due to invalid syntax.'
    }, status=400)