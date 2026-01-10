# Database Migrations Guide

This guide covers database migration management using Alembic for the CMS project.

## Overview

The project uses **Alembic** for database schema migrations with SQLAlchemy 2.0 async support. Migrations are version-controlled and allow you to:
- Track database schema changes over time
- Apply changes incrementally across environments
- Rollback changes if needed
- Collaborate on schema changes with your team

## Current Migration Status

The project has 15 existing migrations covering:
- Initial user and role tables
- Content management (content, categories, tags)
- Content versioning system
- Activity logging
- Notifications
- Password reset tokens

**Latest migration**: `a1f2c3d4e5f6_add_password_reset_tokens_table.py`

## Migration File Structure

```
cms-project/
├── alembic/
│   ├── versions/          # Migration scripts
│   │   ├── a1f2c3d4e5f6_add_password_reset_tokens_table.py
│   │   ├── 3a7b0b241cb5_add_content_versions_table.py
│   │   └── ...
│   ├── env.py            # Alembic environment configuration
│   └── script.py.mako    # Template for new migrations
├── alembic.ini           # Alembic configuration
└── app/
    ├── models/           # SQLAlchemy models (source of truth)
    └── database.py       # Database connection setup
```

## Working with Migrations

### Check Current Migration Status

```bash
# Show current migration version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --verbose
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply migrations to a specific version
alembic upgrade a1f2c3d4e5f6

# Apply next N migrations
alembic upgrade +2

# Show SQL without executing (dry run)
alembic upgrade head --sql
```

### Rollback Migrations

```bash
# Rollback to previous migration
alembic downgrade -1

# Rollback to a specific version
alembic downgrade 3a7b0b241cb5

# Rollback all migrations
alembic downgrade base

# Show SQL without executing (dry run)
alembic downgrade -1 --sql
```

### Create New Migrations

#### Auto-generate Migration from Model Changes

This is the **recommended approach** - Alembic detects changes automatically:

```bash
# 1. Update your SQLAlchemy models in app/models/
# 2. Auto-generate migration script
alembic revision --autogenerate -m "add user profile fields"

# 3. Review the generated migration file in alembic/versions/
# 4. Edit if needed (remove unwanted changes, add data migrations)
# 5. Apply the migration
alembic upgrade head
```

**Important**: Always review auto-generated migrations before applying them. They may include:
- Unwanted changes (temporary test models)
- Missing data migrations
- Index or constraint changes that need manual adjustment

#### Create Empty Migration (Manual)

For data migrations or complex schema changes:

```bash
# Create empty migration file
alembic revision -m "migrate user data to new format"

# Edit the generated file in alembic/versions/
# Add your custom upgrade() and downgrade() logic
```

### Migration Best Practices

#### 1. Model Changes First

Always update your SQLAlchemy models before creating migrations:

```python
# app/models/user.py
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    # NEW FIELD - Add to model first
    bio = Column(String(500), nullable=True)
```

Then generate the migration:

```bash
alembic revision --autogenerate -m "add bio field to users"
```

#### 2. Review Generated Migrations

Always inspect auto-generated migrations:

```python
def upgrade() -> None:
    # Check for:
    # - Correct table and column names
    # - Proper constraints (nullable, unique, foreign keys)
    # - Index creation on frequently queried columns
    # - Default values for new columns
    op.add_column('users', sa.Column('bio', sa.String(length=500), nullable=True))


def downgrade() -> None:
    # Ensure downgrade reverses upgrade correctly
    op.drop_column('users', 'bio')
```

#### 3. Test Migrations Before Committing

```bash
# Apply migration
alembic upgrade head

# Test your application
pytest

# Test rollback
alembic downgrade -1

# Re-apply
alembic upgrade head
```

#### 4. Use Descriptive Migration Messages

```bash
# Good
alembic revision --autogenerate -m "add email verification fields to users"
alembic revision --autogenerate -m "create content_media_attachments table"

# Bad
alembic revision --autogenerate -m "update"
alembic revision --autogenerate -m "changes"
```

#### 5. Keep Migrations Small and Focused

One logical change per migration:
- Adding a table → one migration
- Modifying multiple columns → one migration
- Data transformation → separate migration

#### 6. Handle Data Migrations Carefully

When migrating existing data, use raw SQL or SQLAlchemy Core:

```python
from alembic import op
from sqlalchemy import text

def upgrade() -> None:
    # Add new column
    op.add_column('users', sa.Column('full_name', sa.String(200), nullable=True))

    # Migrate data (use raw SQL for safety)
    connection = op.get_bind()
    connection.execute(
        text("UPDATE users SET full_name = username WHERE full_name IS NULL")
    )

    # Make non-nullable after data migration
    op.alter_column('users', 'full_name', nullable=False)
```

## Docker Environment

### Running Migrations in Docker

The `docker-compose.yml` is configured to run migrations automatically on startup:

```yaml
web:
  command: >
    sh -c "
      alembic upgrade head &&
      uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    "
```

### Manual Migration Commands in Docker

```bash
# Check current migration
docker-compose exec web alembic current

# Apply migrations
docker-compose exec web alembic upgrade head

# Rollback migration
docker-compose exec web alembic downgrade -1

# Create new migration
docker-compose exec web alembic revision --autogenerate -m "add new field"

# View migration history
docker-compose exec web alembic history
```

### Initialize Fresh Database

```bash
# Start database service
docker-compose up -d db redis

# Run migrations
docker-compose run --rm web alembic upgrade head

# Verify
docker-compose exec web alembic current
```

## Common Migration Patterns

### Adding a New Column

```python
def upgrade() -> None:
    op.add_column('users',
        sa.Column('phone_number', sa.String(20), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('users', 'phone_number')
```

### Adding a Column with Default Value

```python
def upgrade() -> None:
    op.add_column('content',
        sa.Column('view_count', sa.Integer(),
                  nullable=False,
                  server_default='0')
    )

def downgrade() -> None:
    op.drop_column('content', 'view_count')
```

### Creating a New Table

```python
def upgrade() -> None:
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(20), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_preferences_id'), 'user_preferences', ['id'])

def downgrade() -> None:
    op.drop_index(op.f('ix_user_preferences_id'), table_name='user_preferences')
    op.drop_table('user_preferences')
```

### Adding an Index

```python
def upgrade() -> None:
    op.create_index(
        'ix_content_created_at',
        'content',
        ['created_at'],
        unique=False
    )

def downgrade() -> None:
    op.drop_index('ix_content_created_at', table_name='content')
```

### Adding a Foreign Key

```python
def upgrade() -> None:
    op.add_column('content', sa.Column('author_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_content_author_id_users',
        'content', 'users',
        ['author_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade() -> None:
    op.drop_constraint('fk_content_author_id_users', 'content', type_='foreignkey')
    op.drop_column('content', 'author_id')
```

### Renaming a Column

```python
def upgrade() -> None:
    op.alter_column('users', 'username', new_column_name='login_name')

def downgrade() -> None:
    op.alter_column('users', 'login_name', new_column_name='username')
```

### Changing Column Type

```python
def upgrade() -> None:
    # PostgreSQL
    op.alter_column('users', 'age',
                    type_=sa.Integer(),
                    existing_type=sa.String())

def downgrade() -> None:
    op.alter_column('users', 'age',
                    type_=sa.String(),
                    existing_type=sa.Integer())
```

## Troubleshooting

### Error: "Can't locate revision identified by"

**Cause**: Migration files out of sync with database state.

**Solution**:
```bash
# Check current state
alembic current

# Check what database thinks current version is
alembic history

# Stamp database to specific version (if you know it's correct)
alembic stamp head
```

### Error: "Target database is not up to date"

**Cause**: Database has newer migrations than your code.

**Solution**:
```bash
# Pull latest code and migrations
git pull

# Apply migrations
alembic upgrade head
```

### Error: "FAILED: Can't locate revision"

**Cause**: Missing migration file or corrupted migration chain.

**Solution**:
```bash
# Check for missing files
ls alembic/versions/

# Verify migration chain
alembic history

# If migration file is truly missing, recreate from git history
git log -- alembic/versions/
```

### Auto-generate Detects No Changes

**Possible causes**:
1. Models not imported in `alembic/env.py`
2. Models not inheriting from `Base`
3. Database already matches models

**Solution**:
```python
# Ensure all models are imported in alembic/env.py
from app.models.content import Content
from app.models.user import User
from app.models.tag import Tag
# ... all your models
```

### Database Connection Issues

```bash
# Test database connection
python -c "from app.database import engine; import asyncio; asyncio.run(engine.dispose())"

# Check DATABASE_URL environment variable
echo $DATABASE_URL

# Verify database is running (Docker)
docker-compose ps db
docker-compose logs db
```

### PostgreSQL vs SQLite Differences

Some migration operations work differently:

```python
# PostgreSQL supports ALTER COLUMN type changes
op.alter_column('users', 'age', type_=sa.Integer())

# SQLite requires recreate table approach
# Need to manually write table recreation logic
```

## Production Deployment

### Pre-deployment Checklist

1. ✅ Test migrations in development
2. ✅ Test rollback in development
3. ✅ Backup production database
4. ✅ Review migration SQL with `--sql` flag
5. ✅ Plan for downtime (if needed)
6. ✅ Prepare rollback plan

### Deployment Steps

```bash
# 1. Backup database
docker-compose exec db pg_dump -U cms_user cms_db > backup_$(date +%Y%m%d).sql

# 2. Review migration SQL (dry run)
docker-compose exec web alembic upgrade head --sql > migration_plan.sql

# 3. Apply migrations
docker-compose exec web alembic upgrade head

# 4. Verify application starts correctly
docker-compose logs -f web

# 5. Test critical functionality
curl http://localhost:8000/health
```

### Rollback Plan

```bash
# If deployment fails, rollback to previous migration
docker-compose exec web alembic downgrade -1

# Restore from backup if needed
cat backup_20260110.sql | docker-compose exec -T db psql -U cms_user -d cms_db
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Database Migrations

on:
  pull_request:
    paths:
      - 'alembic/versions/**'
      - 'app/models/**'

jobs:
  test-migrations:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v3

      - name: Run migrations
        run: |
          alembic upgrade head

      - name: Test rollback
        run: |
          alembic downgrade -1
          alembic upgrade head
```

## Advanced Topics

### Branch Migrations

For feature branches with parallel development:

```bash
# Create branch-specific migration
alembic revision --autogenerate -m "feature branch changes" --branch-label feature_x

# Merge branches
alembic merge -m "merge feature_x and main" <rev1> <rev2>
```

### Offline SQL Generation

Generate SQL files for DBA review:

```bash
# Generate upgrade SQL
alembic upgrade head --sql > upgrade_to_latest.sql

# Generate downgrade SQL
alembic downgrade -1 --sql > rollback_one_step.sql
```

### Multiple Database Support

If you need to support multiple database types:

```python
# In migration file
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Check database type
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # PostgreSQL-specific migration
        op.execute("CREATE INDEX CONCURRENTLY ...")
    elif bind.dialect.name == 'sqlite':
        # SQLite-specific migration
        pass
```

## Migration Checklist

Before creating a pull request with migrations:

- [ ] Models updated in `app/models/`
- [ ] Migration auto-generated and reviewed
- [ ] Migration tested locally (upgrade + downgrade)
- [ ] Tests updated to match schema changes
- [ ] Migration message is descriptive
- [ ] No sensitive data in migration files
- [ ] Foreign keys have proper `ondelete` behavior
- [ ] Indexes added for frequently queried columns
- [ ] Default values provided for new non-nullable columns

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

Last updated: 2026-01-10
