# Code Quality & Linting

This project uses automated code quality tools to maintain consistent, clean, and secure code.

## Tools

### Ruff

[Ruff](https://github.com/astral-sh/ruff) is an extremely fast Python linter and formatter that combines the functionality of multiple tools (Flake8, isort, pyupgrade, etc.) into one.

**Features:**
- Code linting (finds bugs and style issues)
- Code formatting (auto-formats code to consistent style)
- Import sorting
- Automatic fixes for many issues
- 10-100x faster than traditional tools

### Mypy

[Mypy](https://mypy-lang.org/) is a static type checker for Python that helps catch type-related bugs before runtime.

**Features:**
- Type checking with Python type hints
- Catches type mismatches and errors
- Improves code documentation
- Integrates with Pydantic for validation

### Pre-commit

[Pre-commit](https://pre-commit.com/) automatically runs code quality checks before each git commit, ensuring problematic code never reaches the repository.

**Features:**
- Runs linters automatically on commit
- Prevents committing code with issues
- Includes security checks (bandit)
- Validates file formats (JSON, YAML, TOML)

## Usage

### Running Linters Manually

**Check for issues:**
```bash
# Check all files
ruff check app

# Check with auto-fix
ruff check app --fix

# Check specific file
ruff check app/main.py
```

**Format code:**
```bash
# Format all Python files
ruff format app

# Check if files need formatting (dry-run)
ruff format app --check
```

**Type checking:**
```bash
# Run mypy on the app directory
mypy app

# Run with verbose output
mypy app --verbose
```

### Pre-commit Hooks

Pre-commit hooks run automatically when you commit, but you can also run them manually:

```bash
# Run on staged files
pre-commit run

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff

# Update hook versions
pre-commit autoupdate
```

### IDE Integration

#### VSCode

Install the Ruff extension:
1. Open Extensions (Ctrl+Shift+X)
2. Search for "Ruff"
3. Install the official Ruff extension by Astral

Add to `.vscode/settings.json`:
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "ruff.lint.args": ["--config=pyproject.toml"]
}
```

## Configuration

All configuration is centralized in `pyproject.toml`.

### Ruff Configuration

**Enabled Rules:**
- `E` - pycodestyle errors (PEP 8 violations)
- `W` - pycodestyle warnings
- `F` - pyflakes (unused imports, undefined names)
- `I` - isort (import sorting)
- `N` - pep8-naming (naming conventions)
- `UP` - pyupgrade (modern Python syntax)
- `B` - flake8-bugbear (common bugs)
- `C4` - flake8-comprehensions (list/dict comprehensions)
- `SIM` - flake8-simplify (code simplification)
- `TCH` - flake8-type-checking (type hint optimization)
- `PTH` - flake8-use-pathlib (modern path handling)

**Line Length:** 120 characters

**Ignored Rules:**
- `E501` - Line too long (handled by formatter)
- `B008` - Function call in argument defaults (FastAPI pattern)
- `UP007` - Use `|` for type unions (we prefer `Optional` for clarity)

### Mypy Configuration

**Settings:**
- Python version: 3.10
- Check untyped definitions: Yes
- Warn about redundant casts: Yes
- Strict equality: Yes
- Pydantic plugin: Enabled

### Pre-commit Hooks

The following checks run on every commit:

1. **Ruff** - Linting and formatting
2. **Mypy** - Type checking
3. **File checks:**
   - End-of-file fixer
   - Trailing whitespace removal
   - YAML/JSON/TOML syntax validation
   - Large file detection (max 1MB)
   - Merge conflict detection
   - Private key detection
4. **Bandit** - Security vulnerability scanning

## Current Status

After initial setup:
- **38 files reformatted** to consistent style
- **221 issues auto-fixed** by Ruff
- **30 remaining issues** (mostly style warnings):
  - 27 exception chaining suggestions (B904)
  - 1 unused variable (F841)
  - 1 exception naming (N818)
  - 1 code simplification (SIM110)

## Best Practices

### Writing Clean Code

1. **Run formatter before committing:**
   ```bash
   ruff format app
   ```

2. **Fix linting issues:**
   ```bash
   ruff check app --fix
   ```

3. **Check types periodically:**
   ```bash
   mypy app
   ```

4. **Let pre-commit handle checks:**
   - Pre-commit runs automatically
   - If it fails, fix the issues and commit again
   - Bypass only in emergencies: `git commit --no-verify`

### Adding Type Hints

```python
# Good - with type hints
def create_user(name: str, age: int) -> User:
    return User(name=name, age=age)

# Better - with Optional
from typing import Optional

def get_user(user_id: int) -> Optional[User]:
    return db.query(User).get(user_id)
```

### Exception Handling

```python
# Current (acceptable)
try:
    do_something()
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid value")

# Better (recommended)
try:
    do_something()
except ValueError as e:
    raise HTTPException(status_code=400, detail="Invalid value") from e
```

## Troubleshooting

### Pre-commit fails

If pre-commit hooks fail:

1. **Read the error message** - It shows what failed
2. **Fix the issues** - Often auto-fixable with `ruff check --fix`
3. **Stage changes** - `git add .`
4. **Commit again** - Pre-commit will run again

### False positives

To ignore specific warnings:

**In code (use sparingly):**
```python
# Ignore single line
result = dangerous_operation()  # noqa: B101

# Ignore specific rule
def my_function():  # type: ignore[no-untyped-def]
    pass
```

**In configuration (pyproject.toml):**
```toml
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F401"]  # Allow unused imports in tests
```

### Performance issues

If linting is slow:

1. **Use Ruff instead of multiple tools** - Already configured
2. **Limit mypy scope** - Only run on changed files
3. **Cache results** - Mypy caches by default
4. **Exclude directories** - Already excluded: venv, migrations, __pycache__

## CI/CD Integration

Add to GitHub Actions workflow:

```yaml
- name: Run Ruff
  run: |
    pip install ruff
    ruff check app
    ruff format app --check

- name: Run Mypy
  run: |
    pip install mypy
    mypy app
```

## Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
