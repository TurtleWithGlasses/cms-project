# Test Utilities Documentation

This directory contains mock utilities and fixtures to improve testability of complex dependencies in the CMS project.

## Overview

The main challenges in testing this application are:
1. **Activity Logging** - Creates separate database sessions, hard to verify
2. **Session Management** - Requires Redis, not available in unit tests
3. **Exception Paths** - Database errors and rollbacks are difficult to trigger
4. **Integration Complexity** - Many interdependent services

This utilities package provides mocks and fixtures to address these challenges.

## Files

### `mocks.py`
Contains mock implementations of complex dependencies:
- `MockActivityLogger` - In-memory activity logging
- `MockSessionManager` - In-memory session management
- `MockDatabaseError` - Simulates database errors
- Helper functions for patching

### `fixtures.py`
Provides pytest fixtures for common testing scenarios:
- `mock_activity_logger` - Activity logger fixture
- `mock_session_manager` - Session manager fixture
- `patch_activity_logging_fixture` - Auto-patches activity logging
- `patch_session_manager_fixture` - Auto-patches session management
- `fully_mocked_dependencies` - Patches all complex dependencies

## Usage Examples

### Testing Activity Logging

```python
from utils.mocks import MockActivityLogger, patch_activity_logging

def test_content_creation_logs_activity(monkeypatch):
    """Test that creating content logs activity"""
    mock_logger = MockActivityLogger()
    patch_activity_logging(monkeypatch, mock_logger)

    # Call your endpoint that creates content
    response = client.post("/api/v1/content", json=data)

    # Verify activity was logged
    assert mock_logger.call_count == 1
    logs = mock_logger.get_logs_for_action("create_draft")
    assert len(logs) == 1
    assert logs[0]["user_id"] == expected_user_id
```

### Testing Session Management

```python
from utils.mocks import MockSessionManager, patch_session_manager

def test_login_creates_session(monkeypatch):
    """Test that login creates a session"""
    mock_manager = MockSessionManager()
    patch_session_manager(monkeypatch, mock_manager)

    # Login
    response = client.post("/auth/token", data=credentials)

    # Verify session was created
    assert len(mock_manager.sessions) == 1
    session = list(mock_manager.sessions.values())[0]
    assert session["user_email"] == credentials["username"]
```

### Testing Error Paths

```python
from utils.mocks import MockActivityLogger

def test_content_creation_handles_logging_failure(monkeypatch):
    """Test that content creation succeeds even if logging fails"""
    mock_logger = MockActivityLogger()

    # Make logging raise an exception
    async def failing_log_activity(*args, **kwargs):
        raise Exception("Logging service unavailable")

    mock_logger.log_activity = failing_log_activity
    patch_activity_logging(monkeypatch, mock_logger)

    # Content should still be created despite logging failure
    response = client.post("/api/v1/content", json=data)
    assert response.status_code == 201
```

### Using Fixtures

```python
def test_with_fixtures(patch_activity_logging_fixture):
    """Test using pytest fixtures"""
    # patch_activity_logging_fixture is already set up
    mock_logger = patch_activity_logging_fixture

    # Your test code here
    response = client.post("/api/v1/content", json=data)

    # Verify logging
    assert mock_logger.call_count > 0
```

## MockActivityLogger API

### Methods

#### `log_activity(action, user_id, content_id, description, **kwargs)`
Records an activity log entry in memory.

#### `get_logs_for_user(user_id)`
Returns all log entries for a specific user.

#### `get_logs_for_action(action)`
Returns all log entries for a specific action.

#### `clear()`
Clears all logged entries.

### Attributes

- `logs` - List of all logged entries
- `call_count` - Number of times log_activity was called

## MockSessionManager API

### Methods

#### `create_session(user_id, user_email, user_role)`
Creates a session and returns session ID.

#### `get_session(session_id)`
Returns session data for given ID.

#### `delete_session(session_id)`
Deletes a session, returns True if successful.

#### `delete_all_user_sessions(user_id)`
Deletes all sessions for a user, returns count deleted.

#### `get_active_sessions(user_id)`
Returns list of active sessions for a user.

#### `clear()`
Clears all sessions.

### Attributes

- `sessions` - Dict mapping session_id to session data
- `session_counter` - Counter for generating session IDs

## Benefits

### 1. Better Test Coverage
- Can now test activity logging code paths
- Can verify logging occurs with correct data
- Can test logging failure scenarios

### 2. Faster Tests
- No database operations for logging
- No Redis dependency for sessions
- Tests run in isolation

### 3. More Reliable Tests
- No flaky tests from timing issues
- No external service dependencies
- Predictable behavior

### 4. Easier Debugging
- Can inspect exact log entries
- Can verify session state
- Clear error messages

## Integration Strategy

To improve coverage on existing routes:

1. **Identify untested code paths**:
   ```bash
   pytest --cov=app.routes.content --cov-report=term-missing
   ```

2. **Add tests using mocks**:
   - Activity logging paths (lines 66-85 in content.py)
   - Exception handling paths (lines 89-91)
   - Session management paths (auth.py)

3. **Verify improved coverage**:
   ```bash
   pytest --cov=app.routes.content --cov-report=term
   ```

## Example: Improving Content Routes Coverage

Current coverage: 43% (72/126 lines uncovered)

Uncovered paths include:
- Activity logging (lines 72-85): Use `MockActivityLogger`
- Exception handling (lines 89-91): Use try-catch testing
- Update logging (lines 146-155): Use `MockActivityLogger`

With mocks, these paths become testable:

```python
def test_create_content_activity_logging_fails(monkeypatch):
    """Test lines 83-85: Activity logging failure path"""
    mock_logger = MockActivityLogger()

    async def failing_log(*args, **kwargs):
        raise Exception("Database error")

    mock_logger.log_activity = failing_log
    patch_activity_logging(monkeypatch, mock_logger)

    response = client.post("/api/v1/content", json=data)
    # Should still succeed despite logging failure
    assert response.status_code == 201
```

This approach can increase coverage from 43% to 60%+ by testing previously unreachable code paths.

## Future Enhancements

- Database error simulation utilities
- Template rendering mocks
- Email service mocks
- Scheduler mocks for delayed tasks

## Contributing

When adding new complex dependencies:
1. Create a mock in `mocks.py`
2. Add fixture in `fixtures.py`
3. Document usage in this README
4. Add example test in docstring
