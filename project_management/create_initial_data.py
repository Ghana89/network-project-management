"""
Initial data setup management command for the application.
Run with: python manage.py shell < create_initial_data.py
"""

from django.contrib.auth.models import User
from app.models import UserProfile, Project, Milestone, SubTask, Resource
from datetime import datetime, timedelta

# Create test users
print("Creating test users...")

# Admin user
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_staff': True,
        'is_superuser': True,
    }
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    UserProfile.objects.create(user=admin_user, role='admin', employee_id='ADM001', department='Management')
    print(f"✓ Admin user created: {admin_user.username}")

# Project Manager
pm_user, created = User.objects.get_or_create(
    username='pm_user',
    defaults={
        'email': 'pm@example.com',
        'first_name': 'Project',
        'last_name': 'Manager',
    }
)
if created:
    pm_user.set_password('pm123')
    pm_user.save()
    UserProfile.objects.create(user=pm_user, role='project_manager', employee_id='PM001', department='IT')
    print(f"✓ Project Manager created: {pm_user.username}")

# Engineer users
engineer_users = []
for i in range(1, 4):
    eng_user, user_created = User.objects.get_or_create(
        username=f'engineer{i}',
        defaults={
            'email': f'engineer{i}@example.com',
            'first_name': f'Engineer',
            'last_name': f'{i}',
        }
    )
    if user_created:
        eng_user.set_password('engineer123')
        eng_user.save()
        
    skills = ['Networking', 'Python', 'Linux', 'Cisco'] if i == 1 else \
             ['Firewall', 'Security', 'Azure'] if i == 2 else \
             ['SD-WAN', 'Routing', 'Network Architecture']
             
    # Ensure UserProfile exists
    UserProfile.objects.get_or_create(
        user=eng_user,
        defaults={
            'role': 'engineer',
            'employee_id': f'ENG00{i}',
            'department': 'Network Operations',
            'skills': ', '.join(skills)
        }
    )
    
    # Ensure Resource record exists for listing in Resources view
    Resource.objects.get_or_create(
        user=eng_user,
        defaults={
            'employee_id': f'ENG00{i}',
            'skill_set': ', '.join(skills),
            'department': 'Network Operations'
        }
    )
    engineer_users.append(eng_user)
    print(f"✓ Engineer checked/created: {eng_user.username}")

print("\n✓ Users setup complete!\n")
