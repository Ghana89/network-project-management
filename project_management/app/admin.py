from django.contrib import admin
from .models import Project, Milestone, SubTask, Resource, UserProfile, Notification, ProjectLog


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_id', 'name', 'customer_name', 'status', 'priority', 'start_date', 'end_date')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('project_id', 'name', 'customer_name')
    readonly_fields = ('created_at', 'updated_at')


class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'baseline_delivery_date', 'completion_percentage')
    list_filter = ('status', 'project')
    search_fields = ('name', 'project__name')
    readonly_fields = ('created_at', 'updated_at')


class SubTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'milestone', 'assigned_to', 'status', 'due_date', 'priority')
    list_filter = ('status', 'priority', 'milestone')
    search_fields = ('name', 'milestone__name')
    readonly_fields = ('created_at', 'updated_at')


class ResourceAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'availability')
    list_filter = ('department', 'availability')
    search_fields = ('employee_id', 'user__first_name', 'user__last_name')


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'employee_id', 'department', 'availability')
    list_filter = ('role', 'department', 'availability')
    search_fields = ('user__username', 'employee_id')


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title')
    readonly_fields = ('created_at',)


class ProjectLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'action', 'timestamp')
    list_filter = ('action', 'timestamp', 'project')
    search_fields = ('project__name', 'action')
    readonly_fields = ('timestamp',)


admin.site.register(Project, ProjectAdmin)
admin.site.register(Milestone, MilestoneAdmin)
admin.site.register(SubTask, SubTaskAdmin)
admin.site.register(Resource, ResourceAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(ProjectLog, ProjectLogAdmin)
