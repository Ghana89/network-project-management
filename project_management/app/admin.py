from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Project, Milestone, SubTask, Resource, UserProfile, Notification, ProjectLog


class CustomUserForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='Email Address')

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_superuser')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Email is required.')
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


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
    list_display = ('user', 'role', 'employee_id', 'phone_number', 'department', 'availability')
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

# 1. Add an inline so UserProfile appears directly inside the User edit page
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Details'
    fk_name = 'user'
    fields = ('role', 'employee_id', 'phone_number', 'skills', 'department', 'availability', 'profile_photo', 'is_deleted', 'deleted_at', 'deleted_by')


# 2. Add a custom UserAdmin to automatically grant access if they are set to 'admin'
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'profile_role', 'profile_phone')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    inlines = (UserProfileInline, )

    def profile_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except Exception:
            return ''
    profile_role.short_description = 'Role'

    def profile_phone(self, obj):
        try:
            return obj.profile.phone_number
        except Exception:
            return ''
    profile_phone.short_description = 'Mobile'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # If the superadmin sets their profile role to 'admin', make sure they are granted staff access
        if hasattr(obj, 'profile') and obj.profile.role == 'admin':
            if not obj.is_staff:
                obj.is_staff = True
                obj.save()

admin.site.register(Project, ProjectAdmin)
admin.site.register(Milestone, MilestoneAdmin)
admin.site.register(SubTask, SubTaskAdmin)
admin.site.register(Resource, ResourceAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(ProjectLog, ProjectLogAdmin)
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
