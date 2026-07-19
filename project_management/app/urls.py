from django.urls import path
from . import views

urlpatterns = [
    # Home Page
    path('', views.home, name='home'),

    # Authentication & User Management
    path('login/', views.user_login, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('users/', views.user_management, name='user_management'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_soft_delete, name='user_soft_delete'),
    path('users/deleted/', views.deleted_users, name='deleted_users'),
    path('users/<int:user_id>/restore/', views.restore_user, name='restore_user'),
    path('logout/', views.user_logout, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:project_id>/archive/', views.project_archive, name='project_archive'),

    # Milestones
    path('projects/<int:project_id>/milestones/create/', views.milestone_create, name='milestone_create'),
    path('milestones/<int:milestone_id>/', views.milestone_detail, name='milestone_detail'),
    path('milestones/<int:milestone_id>/edit/', views.milestone_edit, name='milestone_edit'),
    path('milestones/<int:milestone_id>/delete/', views.milestone_delete, name='milestone_delete'),

    # Sub-Tasks
    path('milestones/<int:milestone_id>/tasks/create/', views.subtask_create, name='subtask_create'),
    path('tasks/<int:task_id>/', views.subtask_detail, name='subtask_detail'),
    path('tasks/<int:task_id>/edit/', views.subtask_edit, name='subtask_edit'),
    path('tasks/<int:task_id>/delete/', views.subtask_delete, name='subtask_delete'),

    # Resources
    path('resources/', views.resource_list, name='resource_list'),
    path('resources/<int:resource_id>/', views.resource_detail, name='resource_detail'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),

    # Reports
    path('reports/project-status/', views.project_status_report, name='project_status_report'),
    path('reports/milestones/', views.milestone_report, name='milestone_report'),
    path('reports/delayed-tasks/', views.delayed_tasks_report, name='delayed_tasks_report'),
    path('reports/resource-utilization/', views.resource_utilization_report, name='resource_utilization_report'),

    # PDF Export
    path('projects/<int:project_id>/export-pdf/', views.export_project_pdf, name='export_project_pdf'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # API Endpoints
    path('api/task-stats/', views.api_get_task_stats, name='api_task_stats'),
    path('api/project-progress/<int:project_id>/', views.api_project_progress, name='api_project_progress'),
]