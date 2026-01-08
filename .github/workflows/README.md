# CI/CD Workflows

This directory contains GitHub Actions workflows for automated testing, linting, and code quality checks.

## Workflows

### Tests (`tests.yml`)
Runs the full test suite with coverage reporting.

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**What it does:**
1. Sets up Python 3.10
2. Starts PostgreSQL 15 service
3. Installs dependencies
4. Runs pytest with coverage
5. Uploads coverage to Codecov

**Environment Variables:**
- `DATABASE_URL`: Main database connection string
- `TEST_DATABASE_URL`: Test database connection string
- `SECRET_KEY`: Application secret key for testing

### Lint (`lint.yml`)
Checks code quality using Ruff linter and formatter.

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**What it does:**
1. Sets up Python 3.10
2. Runs Ruff linter
3. Checks code formatting

## Setup

### Codecov Integration

To enable coverage reporting:

1. Go to [codecov.io](https://codecov.io/) and sign in with GitHub
2. Add your repository
3. Get your upload token
4. Add it as a repository secret:
   - Go to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: Your Codecov upload token

### Pre-commit Hooks

Install pre-commit hooks locally:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Run hooks manually (optional)
pre-commit run --all-files
```

## Current Test Status

- **Pass Rate:** 92.7% (511/551 tests)
- **Failing Tests:** 39 (actual code issues, not infrastructure)
- **Skipped Tests:** 1

### Known Issues

The following test categories currently have failures:
- Integration tests (routing, authentication) - 9 tests
- Function signature mismatches - 6 tests
- CSRF middleware - 6 tests
- Auth sessions - 10 tests
- Security/rate limiting - 5 tests
- User operations - 3 tests

## Local Testing

Run tests locally before pushing:

```bash
# Run all tests
pytest test/ -v

# Run with coverage
pytest test/ --cov=app --cov-report=term-missing

# Run specific test file
pytest test/test_auth_helpers.py -v

# Run tests in quiet mode
pytest test/ -q
```

## Debugging Failed CI

If CI fails:

1. Check the workflow run in GitHub Actions
2. Review the test output and error messages
3. Run the failing tests locally
4. Fix the issues and push again

## Adding New Workflows

To add a new workflow:

1. Create a new `.yml` file in this directory
2. Use the existing workflows as templates
3. Test locally if possible using [act](https://github.com/nektos/act)
4. Commit and push to trigger the workflow
