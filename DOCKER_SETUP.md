# Docker Setup Guide

This guide explains how to run the CMS application using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (to clone the repository)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cms-project
```

### 2. Configure Environment Variables

Copy the Docker environment template:

```bash
cp .env.docker .env
```

Edit `.env` and update the following critical values:
- `SECRET_KEY`: Use a strong random string (generate with `openssl rand -hex 32`)
- `DATABASE_PASSWORD`: Change from default
- `REDIS_PASSWORD`: Change from default

### 3. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f web
```

The application will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PgAdmin** (optional): http://localhost:5050

### 4. Initialize Database

The database migrations run automatically on startup. If you need to run them manually:

```bash
docker-compose exec web alembic upgrade head
```

### 5. Create Initial Admin User

```bash
docker-compose exec web python -c "
from app.auth import hash_password
from app.models import User, Role
from app.database import AsyncSessionLocal
import asyncio

async def create_admin():
    async with AsyncSessionLocal() as session:
        # Check if admin role exists
        from sqlalchemy.future import select
        result = await session.execute(select(Role).where(Role.name == 'superadmin'))
        admin_role = result.scalars().first()

        if not admin_role:
            print('Admin role not found. Please run migrations first.')
            return

        # Create admin user
        admin = User(
            username='admin',
            email='admin@cms.local',
            hashed_password=hash_password('admin123'),
            role_id=admin_role.id
        )
        session.add(admin)
        await session.commit()
        print('Admin user created: admin / admin123')

asyncio.run(create_admin())
"
```

## Docker Commands

### Service Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose stop

# Restart services
docker-compose restart

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (WARNING: deletes data)
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f redis
```

### Access Container Shell

```bash
# Web application
docker-compose exec web sh

# Database
docker-compose exec db psql -U cms_user -d cms_db

# Redis
docker-compose exec redis redis-cli -a redis_password
```

### Database Operations

> **Note**: For comprehensive migration documentation including patterns, troubleshooting, and best practices, see [MIGRATIONS.md](MIGRATIONS.md).

```bash
# Run migrations
docker-compose exec web alembic upgrade head

# Rollback migration
docker-compose exec web alembic downgrade -1

# Create new migration
docker-compose exec web alembic revision --autogenerate -m "description"

# Database backup
docker-compose exec db pg_dump -U cms_user cms_db > backup.sql

# Database restore
cat backup.sql | docker-compose exec -T db psql -U cms_user -d cms_db
```

## Development Workflow

### Hot Reload

The docker-compose setup includes volume mounts for code hot-reloading:
- Changes to `app/` directory are reflected immediately
- Changes to `templates/` are reflected immediately
- No need to rebuild the container for code changes

### Running Tests

```bash
# Run all tests
docker-compose exec web pytest

# Run specific test file
docker-compose exec web pytest test/test_routes_auth.py

# Run with coverage
docker-compose exec web pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Linting
docker-compose exec web ruff check app/

# Type checking
docker-compose exec web mypy app/

# Format code
docker-compose exec web ruff format app/
```

## Optional Services

### PgAdmin (Database Management UI)

To start PgAdmin for database management:

```bash
# Start with PgAdmin
docker-compose --profile tools up -d

# Access at http://localhost:5050
# Default credentials: admin@cms.local / admin
```

Add server connection in PgAdmin:
- **Host**: db
- **Port**: 5432
- **Username**: cms_user
- **Password**: cms_password (from .env)
- **Database**: cms_db

## Production Deployment

> **Note**: For comprehensive production deployment instructions including cloud providers (AWS, Azure, GCP), CI/CD pipelines, monitoring, and scaling strategies, see [DEPLOYMENT.md](DEPLOYMENT.md).

This section covers basic Docker-based production deployment. For advanced production scenarios, refer to the detailed deployment guide.

### Security Checklist

Before deploying to production:

1. ✅ Change `SECRET_KEY` to a strong random value
2. ✅ Use strong passwords for `DATABASE_PASSWORD` and `REDIS_PASSWORD`
3. ✅ Set `ENVIRONMENT=production` and `DEBUG=False`
4. ✅ Configure proper `ALLOWED_HOSTS` and `ALLOWED_ORIGINS`
5. ✅ Use SSL/TLS certificates (configure reverse proxy)
6. ✅ Set up proper backup strategy
7. ✅ Configure monitoring and logging
8. ✅ Review and update firewall rules

### Production Build

```bash
# Build optimized production image
docker build -t cms-app:latest .

# Run with production settings
docker run -d \
  --name cms-app \
  -p 8000:8000 \
  --env-file .env.production \
  cms-app:latest
```

### Using External Databases

To use managed PostgreSQL and Redis services (AWS RDS, Azure Database, etc.):

1. Comment out `db` and `redis` services in `docker-compose.yml`
2. Update `DATABASE_URL` and `REDIS_URL` in `.env` with external endpoints
3. Run only the `web` service:

```bash
docker-compose up -d web
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test database connection
docker-compose exec db pg_isready -U cms_user
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli -a redis_password ping
```

### Application Not Starting

```bash
# Check application logs
docker-compose logs web

# Check health status
docker-compose ps

# Restart services
docker-compose restart web
```

### Permission Issues

If you encounter permission errors:

```bash
# Fix ownership (Linux/Mac)
sudo chown -R $USER:$USER .

# On Windows, ensure Docker has access to the project directory
```

## Performance Tuning

### Worker Processes

Adjust the number of Uvicorn workers in `docker-compose.yml`:

```yaml
command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Rule of thumb: `(2 * CPU cores) + 1`

### Database Connection Pool

Update `app/database.py` for production:

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,  # Connection pool size
    max_overflow=10,  # Max overflow connections
    pool_pre_ping=True,  # Verify connections
)
```

### Redis Memory

Adjust Redis max memory in `docker-compose.yml`:

```yaml
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

## Monitoring

### Health Check Endpoint

The application exposes a health check endpoint:

```bash
curl http://localhost:8000/health
```

### Resource Usage

```bash
# Monitor container resources
docker stats

# Specific container
docker stats cms_web
```

## Backup and Restore

### Automated Backups

Create a backup script (`scripts/backup.sh`):

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U cms_user cms_db > "backups/db_backup_$DATE.sql"
echo "Backup created: db_backup_$DATE.sql"
```

### Restore from Backup

```bash
cat backups/db_backup_20240110.sql | docker-compose exec -T db psql -U cms_user -d cms_db
```

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Review [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- Open an issue on GitHub

---

Last updated: 2026-01-10
