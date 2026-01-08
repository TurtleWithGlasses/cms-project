# Contributing to CMS Project

Thank you for your interest in contributing! This guide will help you set up your development environment and understand the workflow.

## Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cms-project
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

This will automatically run linting and formatting checks before each commit.

### 5. Configure Database

Create a PostgreSQL database for development and testing:

```sql
CREATE DATABASE cms_project;
CREATE DATABASE cms_project_test;
```

Set environment variables (create a `.env` file):

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/cms_project
TEST_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/cms_project_test
SECRET_KEY=your-secret-key-here
```

## Running Tests

### Run All Tests

```bash
pytest test/ -v
```

### Run with Coverage

```bash
pytest test/ --cov=app --cov-report=term-missing
```

### Run Specific Tests

```bash
# Single file
pytest test/test_auth_helpers.py -v

# Single test
pytest test/test_auth_helpers.py::TestGetCurrentUser::test_get_current_user_with_valid_token -v

# Tests matching a pattern
pytest test/ -k "auth" -v
```

### Run Tests in Quiet Mode

```bash
pytest test/ -q
```

## Code Quality

### Linting

```bash
# Check for issues
ruff check app/ test/

# Auto-fix issues
ruff check app/ test/ --fix
```

### Formatting

```bash
# Check formatting
ruff format app/ test/ --check

# Format code
ruff format app/ test/
```

### Type Checking

```bash
mypy app/
```

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `style`: Code style changes (formatting, etc.)
- `chore`: Maintenance tasks

**Example:**

```
feat(auth): add JWT token refresh endpoint

Implement token refresh functionality to allow users to obtain
new access tokens without re-authenticating.

Closes #123
```

### Pre-commit Checks

Before committing, the following checks will run automatically:

1. **Ruff Linter**: Checks for code quality issues
2. **Ruff Formatter**: Ensures consistent code formatting
3. **Mypy**: Static type checking (excludes test files)
4. **Bandit**: Security vulnerability scanning
5. **General Checks**: YAML/JSON/TOML syntax, trailing whitespace, etc.

To run checks manually:

```bash
pre-commit run --all-files
```

## Pull Request Process

1. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write code
   - Add/update tests
   - Update documentation if needed

3. **Run Tests Locally**

   ```bash
   pytest test/ -v
   ```

4. **Commit Your Changes**

   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push to GitHub**

   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Fill in the PR template
   - Link related issues

7. **Wait for CI/CD**
   - GitHub Actions will automatically run tests
   - Ensure all checks pass
   - Address any failures

8. **Code Review**
   - Wait for reviewer feedback
   - Make requested changes
   - Push updates

9. **Merge**
   - Once approved and all checks pass, PR will be merged

## CI/CD

### Automated Workflows

The project uses GitHub Actions for CI/CD:

- **Tests** (`tests.yml`): Runs on push/PR to main/develop
- **Lint** (`lint.yml`): Code quality checks on push/PR

### Coverage Reporting

Test coverage is automatically uploaded to Codecov. You can view coverage reports:

1. On your PR (Codecov bot will comment)
2. On [codecov.io](https://codecov.io/) dashboard

### Current Test Status

- **Pass Rate:** 92.7% (511/551 tests)
- **Target:** 95%+ pass rate
- **Coverage:** ~67%

## Development Workflow

### Adding a New Feature

1. Create issue describing the feature
2. Create feature branch from `develop`
3. Implement feature with tests
4. Update documentation
5. Submit PR
6. Address review feedback
7. Merge to `develop`

### Fixing a Bug

1. Create issue describing the bug
2. Create bugfix branch from `main` or `develop`
3. Write failing test that reproduces bug
4. Fix the bug
5. Ensure test passes
6. Submit PR
7. Address review feedback
8. Merge

### Adding Tests

When adding tests:

- Place them in the `test/` directory
- Name test files with `test_` prefix
- Use descriptive test names
- Follow existing test patterns
- Aim for high coverage of new code

## Getting Help

- Open an issue for bugs or feature requests
- Ask questions in pull request comments
- Check existing issues and PRs

## License

By contributing, you agree that your contributions will be licensed under the project's license.
