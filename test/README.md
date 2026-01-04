# Test Configuration

This project uses PostgreSQL for testing to match the production environment exactly.

## Quick Setup

### 1. Create Test Database

Create a separate PostgreSQL database for tests:

```sql
CREATE DATABASE cms_test;
```

Or use your preferred database name and set it in `.env`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost/your_test_db
```

### 2. Run Tests

```bash
pytest test/ -v
```

## Configuration Options

### Option 1: Auto-derived Test Database (Recommended)
If you don't set `TEST_DATABASE_URL`, the test configuration will automatically:
- Take your production `DATABASE_URL` from `.env`
- Append `_test` to the database name
- Use that for tests

Example:
- Production: `postgresql+asyncpg://user:pass@localhost/cms`
- Tests will use: `postgresql+asyncpg://user:pass@localhost/cms_test`

### Option 2: Custom Test Database URL
Add to your `.env` file:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost/cms_test
```

### Option 3: Use Different PostgreSQL Instance
You can point tests to a completely different PostgreSQL server:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://testuser:testpass@testserver:5432/cms_test
```

## What Happens During Tests

1. **Before each test**:
   - Connects to test database
   - Creates all tables
   - Inserts default roles (user, editor, manager, admin, superadmin)

2. **After each test**:
   - Drops all tables
   - Cleans up completely

This ensures:
- ✅ Each test starts with a fresh database
- ✅ Tests don't interfere with each other
- ✅ No test data pollution
- ✅ Tests match production behavior exactly

## Troubleshooting

### Database Connection Error
If you get connection errors:
1. Make sure PostgreSQL is running
2. Verify the test database exists: `psql -l`
3. Check credentials in your `.env` file

### Permission Errors
Make sure your PostgreSQL user has permissions to:
- Create/drop tables in the test database
- Insert/delete data

Grant permissions if needed:
```sql
GRANT ALL PRIVILEGES ON DATABASE cms_test TO your_user;
```

### Slow Tests
If tests are slow:
- PostgreSQL tests are slower than SQLite but more accurate
- Consider using fewer test fixtures
- Run specific test files: `pytest test/test_security.py -v`

## Why PostgreSQL for Tests?

Using the same database for tests and production ensures:
- JSON column behavior matches
- Transaction handling is identical
- SQL queries work the same way
- Foreign key constraints behave consistently
- No surprises when deploying to production

## Switching Back to SQLite (Not Recommended)

If you absolutely need SQLite for quick local tests, you can override:

```bash
TEST_DATABASE_URL=sqlite+aiosqlite:///:memory:
```

**Note**: This may cause tests to pass locally but fail in production due to database differences.
