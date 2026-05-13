# Network Project Management Application

A comprehensive web-based application for managing network infrastructure projects with centralized visibility into project progress, resource allocation, and delivery risks.

## Features

### Project Management
- Create, edit, and archive projects
- Track project milestones and deliverables
- Monitor project progress and status
- Manage project timelines and budgets

### Milestone Management
- Define project milestones
- Track baseline and actual delivery dates
- Monitor milestone completion percentage
- Visual milestone timeline

### Sub-Task Management
- Create sub-tasks under milestones
- Assign tasks to resources
- Track task dependencies
- Monitor actual vs estimated effort
- Task status updates and comments

### Resource Management
- Maintain resource/team member details
- Track resource utilization and workload
- Manage resource availability
- Skill-set tracking

### Dashboard & Reporting
- Project status overview
- Upcoming milestones tracking
- Overdue tasks and risks
- Resource utilization reports
- Project completion metrics
- PDF export functionality

### Role-Based Access Control
- **Admin**: Full system access, user management
- **Project Manager**: Create and manage projects, assign resources
- **Resource/Engineer**: View assigned tasks, update status
- **Viewer/Stakeholder**: Read-only dashboard access

### Additional Features
- Email notifications for task assignments
- Audit logging of all activities
- Search and filtering capabilities
- Responsive web UI
- SQLite database

## Technology Stack

- **Backend**: Django 4.2 (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite3
- **Server**: Django Development Server / Gunicorn

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual Environment (recommended)

### Step 1: Clone/Download the Project

```bash
cd network-project-management
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Navigate to Project Directory

```bash
cd project_management
```

### Step 5: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### Step 7: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Step 8: Run Development Server

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## First-Time Setup

### 1. Access Admin Panel
- Navigate to `http://localhost:8000/admin/`
- Login with your superuser credentials
- Create user profiles for all users with appropriate roles

### 2. Create Initial Resources
- Go to Admin panel > Resources
- Add team members with skills and departments

### 3. Create Your First Project
- Navigate to `http://localhost:8000/` and login
- Click on "Projects" > "New Project"
- Fill in project details and save

### 4. Add Milestones
- Open the project
- Click "Add Milestone"
- Define milestone name and delivery dates

### 5. Create Sub-Tasks
- Open a milestone
- Click "Add Task"
- Assign tasks to resources

## Project Structure

```
network-project-management/
│
├── project_management/          # Django project directory
│   ├── manage.py               # Django management script
│   ├── project_management/      # Project settings
│   │   ├── settings.py         # Django configuration
│   │   ├── urls.py             # URL routing
│   │   └── wsgi.py             # WSGI configuration
│   │
│   └── app/                     # Main application
│       ├── migrations/          # Database migrations
│       ├── templates/           # HTML templates
│       │   ├── auth/            # Login/Register pages
│       │   ├── dashboard/       # Dashboard templates
│       │   ├── projects/        # Project management templates
│       │   ├── milestones/      # Milestone templates
│       │   ├── subtasks/        # Task templates
│       │   ├── resources/       # Resource management
│       │   ├── reports/         # Report templates
│       │   ├── notifications/   # Notification pages
│       │   └── profile/         # User profile
│       │
│       ├── static/              # Static files
│       │   ├── css/
│       │   │   └── style.css    # Main stylesheet
│       │   └── js/
│       │       ├── main.js      # Main JavaScript
│       │       └── dashboard.js # Dashboard scripts
│       │
│       ├── models.py            # Database models
│       ├── views.py             # View functions
│       ├── urls.py              # App URL routing
│       ├── forms.py             # Form definitions
│       └── admin.py             # Admin configuration
│
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Database Models

### UserProfile
Extended user profile with role, skills, and department information.

### Project
Main project entity with status, dates, and budget tracking.

### Milestone
Project milestones with delivery dates and completion tracking.

### SubTask
Individual tasks under milestones with assignment and effort tracking.

### Resource
Team member/resource information with skill sets and utilization.

### Notification
System notifications for task assignments and updates.

### ProjectLog
Audit trail for all project activities.

## URL Endpoints

### Authentication
- `GET /login/` - Login page
- `GET /register/` - Registration page
- `GET /logout/` - Logout user

### Dashboard
- `GET /` - Main dashboard

### Projects
- `GET /projects/` - List projects
- `POST /projects/create/` - Create new project
- `GET /projects/<id>/` - Project details
- `POST /projects/<id>/edit/` - Edit project
- `POST /projects/<id>/archive/` - Archive project

### Milestones
- `POST /projects/<id>/milestones/create/` - Create milestone
- `GET /milestones/<id>/` - Milestone details
- `POST /milestones/<id>/edit/` - Edit milestone
- `POST /milestones/<id>/delete/` - Delete milestone

### Tasks
- `POST /milestones/<id>/tasks/create/` - Create task
- `GET /tasks/<id>/` - Task details
- `POST /tasks/<id>/edit/` - Edit task
- `POST /tasks/<id>/delete/` - Delete task

### Resources
- `GET /resources/` - List resources
- `GET /resources/<id>/` - Resource details

### Notifications
- `GET /notifications/` - List notifications
- `POST /notifications/<id>/mark-read/` - Mark as read

### Reports
- `GET /reports/project-status/` - Project status report
- `GET /reports/milestones/` - Milestone report
- `GET /reports/delayed-tasks/` - Delayed tasks report
- `GET /reports/resource-utilization/` - Resource utilization report

### Profile
- `GET /profile/` - User profile
- `POST /profile/` - Update profile

## Configuration

### Email Settings
Edit `project_management/settings.py` to configure email:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # For development
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'
```

### Database
The application uses SQLite by default. To use a different database, edit `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # Change as needed
        'NAME': 'database_name',
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'django'"
**Solution**: Ensure you've activated the virtual environment and installed requirements:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: "sqlite3.OperationalError: no such table"
**Solution**: Run migrations:
```bash
python manage.py migrate
```

### Issue: Static files not loading
**Solution**: Collect static files:
```bash
python manage.py collectstatic --noinput
```

### Issue: Can't login after registration
**Solution**: Check that user profile was created with appropriate role in admin panel.

## Performance Tips

1. **Database Indexing**: Add database indexes for frequently queried fields
2. **Caching**: Implement Django caching for dashboard data
3. **Pagination**: Use pagination for large datasets
4. **Compression**: Enable GZIP compression for responses

## Security Considerations

1. Change `SECRET_KEY` in production
2. Set `DEBUG = False` in production
3. Use HTTPS in production
4. Implement rate limiting for API endpoints
5. Use strong password policies
6. Enable CSRF protection
7. Sanitize user inputs
8. Use environment variables for sensitive data

## Deployment

### Using Gunicorn

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn project_management.wsgi --bind 0.0.0.0:8000
```

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "project_management.wsgi"]
```

Build and run:
```bash
docker build -t npm-app .
docker run -p 8000:8000 npm-app
```

## API Usage

### Get Task Statistics

```bash
curl http://localhost:8000/api/task-stats/
```

Response:
```json
{
    "total": 25,
    "completed": 10,
    "in_progress": 8,
    "overdue": 2
}
```

### Get Project Progress

```bash
curl http://localhost:8000/api/project-progress/1/
```

Response:
```json
{
    "project_name": "SD-WAN Deployment",
    "overall_progress": 60,
    "milestones": [
        {
            "name": "Requirement Gathering",
            "progress": 100,
            "status": "completed"
        }
    ]
}
```

## Future Enhancements

- Gantt chart visualization
- Mobile application (React Native)
- Integration with Jira/ServiceNow
- AI-based delivery risk prediction
- Automated escalation workflows
- Timesheet integration
- SLA tracking
- Two-factor authentication
- Advanced reporting with charts
- Real-time notifications using WebSockets

## Support & Documentation

For detailed documentation on specific features, visit:
- Django Documentation: https://docs.djangoproject.com/
- SQLite Documentation: https://www.sqlite.org/docs.html

## License

This project is provided as-is for educational and business purposes.

## Contact

For support or questions, please contact the development team.

---

**Version**: 1.0.0  
**Last Updated**: May 2026  
**Database**: SQLite3  
**Python Version**: 3.8+  
**Django Version**: 4.2.0
