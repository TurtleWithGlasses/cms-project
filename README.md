# CMS Project

A powerful and flexible Content Management System built with FastAPI, SQLAlchemy, and PostgreSQL.

## Features

- 🔐 **Authentication & Authorization**: JWT-based authentication with role-based access control (RBAC)
- 📝 **Content Management**: Create, update, and publish content with versioning support
- 👥 **User Management**: Comprehensive user management with multiple role types
- 🏷️ **Tagging System**: Organize content with tags and categories
- 📊 **Activity Logging**: Track all user actions and content changes
- 🔔 **Notifications**: User notification system for content updates and actions
- ⏰ **Content Scheduling**: Schedule content publication for future dates
- 🔄 **Content Versioning**: Track and rollback content changes

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL with async support (asyncpg)
- **ORM**: SQLAlchemy 2.0.36 with async support
- **Authentication**: JWT tokens with python-jose
- **Password Hashing**: bcrypt via passlib
- **Migrations**: Alembic 1.14.0
- **Scheduler**: APScheduler 3.10.4
- **Templates**: Jinja2 3.1.4

## Project Structure

```
cms-project/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # API routes
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── middleware/      # Custom middleware (RBAC)
│   ├── permissions_config/  # Permission configurations
│   └── utils/           # Utility functions
├── alembic/             # Database migrations
├── templates/           # HTML templates
├── test/                # Test files
├── main.py             # Application entry point
└── requirements.txt    # Project dependencies
```

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 12+

### Setup

1. Clone the repository:
```bash
git clone https://github.com/TurtleWithGlasses/cms-project.git
cd cms-project
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```env
# Application
APP_NAME=CMS Project
APP_VERSION=1.0.0
DEBUG=True
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost/cms_db

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (comma-separated list)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the application:
```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`

## API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## User Roles

The system supports the following roles:

- **User**: Basic content creation and management
- **Editor**: Enhanced content management capabilities
- **Manager**: Content approval and user management
- **Admin**: Full system administration
- **Superadmin**: Complete system control

## Key Endpoints

### Authentication
- `POST /auth/token` - Get access token
- `POST /register` - Register new user
- `GET /login` - Login page
- `GET /logout` - Logout

### Users
- `GET /users/me` - Get current user profile
- `GET /users` - List all users (admin only)
- `PUT /users/{user_id}/role` - Update user role (admin only)
- `DELETE /users/delete/{user_id}` - Delete user

### Content
- `POST /api/v1/content` - Create new content
- `GET /api/v1/content` - List all content
- `PATCH /api/v1/content/{content_id}` - Update content
- `PATCH /api/v1/content/{content_id}/submit` - Submit for approval
- `PATCH /api/v1/content/{content_id}/approve` - Approve content (admin only)
- `GET /api/v1/content/{content_id}/versions` - Get content versions
- `POST /api/v1/content/{content_id}/rollback/{version_id}` - Rollback to version

### Notifications
- `GET /users/notifications` - Get user notifications
- `PUT /users/notifications/{id}` - Mark notification as read
- `PUT /users/notifications/read_all` - Mark all as read

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## Security Considerations

1. Always use strong `SECRET_KEY` in production
2. Configure `ALLOWED_ORIGINS` to restrict CORS
3. Use HTTPS in production
4. Regularly update dependencies
5. Implement rate limiting for production
6. Use environment-specific configurations

## Content Workflow

1. **Draft**: Content is created in draft status
2. **Pending**: Editor submits content for approval
3. **Published**: Admin approves and publishes content

Content can also be scheduled for future publication using the scheduler.

## Activity Logging

All important actions are logged to the `activity_logs` table:
- User registration and login
- Content creation, updates, and deletion
- Role changes
- Password updates

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue on GitHub
- Check existing documentation in `.README` file

## Changelog

### Version 1.0.0
- Initial release
- User authentication and authorization
- Content management with versioning
- Role-based access control
- Notification system
- Activity logging
- Content scheduling

