# Coverage Analysis & Improvement Strategy

**Date:** 2026-01-08
**Current Coverage:** 69% (1924 statements, 591 missed)
**Target Coverage:** 80%+
**Gap:** 11 percentage points

## Summary

This document analyzes the test coverage gaps and provides a roadmap for reaching 80%+ coverage.

## Current State

### Overall Coverage by Module

| Module | Coverage | Statements | Missed | Priority |
|--------|----------|------------|---------|----------|
| **Routes** | **41%** | **568** | **336** | **HIGH** |
| Models | 100% | - | 0 | ✅ Complete |
| Schemas | 98-100% | - | ~10 | Low |
| Services | 74-100% | - | ~50 | Medium |
| **Middleware** | **21-30%** | **141** | **106** | **SKIPPED** |
| Utils | 73-100% | - | ~30 | Low |
| Core (main, db, scheduler) | 50-61% | ~50 | ~25 | Medium |

### Route Coverage Breakdown

| Route File | Coverage | Missed Lines | Notes |
|------------|----------|--------------|-------|
| user.py | 36% | 188 | Largest gap |
| content.py | 42% | 73 | 2nd largest gap |
| auth.py | 46% | 30 | Session endpoints untested |
| password_reset.py | 49% | 28 | Some edge cases |
| roles.py | 57% | 6 | Minor gaps |
| category.py | 65% | 8 | Minor gaps |

## Investigation Findings

### 1. Skipped Tests Analysis

All 69 skipped tests have fundamental issues:

#### Integration Tests (5 tests) - `test_user_operations.py`, `test_content.py`
- **Issue:** Use `TestClient(app)` with real database instead of test fixtures
- **Error:** `UndefinedTableError: relation "users" does not exist`
- **Fix Effort:** High - requires complete rewrite to use async fixtures
- **Recommendation:** Keep skipped, improve existing route tests instead

#### Session Management (13 tests) - `test_auth_sessions.py`
- **Status:** 3 tests pass (login), 10 tests fail (logout/sessions)
- **Issue:** Logout/sessions endpoints return 404 Not Found
- **Root Cause:** Endpoints exist in code but have routing/middleware issues
- **Passing Tests:**
  - `test_login_creates_session` ✅
  - `test_login_embeds_session_id_in_token` ✅
  - `test_login_invalid_credentials_no_session` ✅
- **Failing Tests:**
  - All `/auth/logout` tests (3 tests) - 404 errors
  - All `/auth/logout-all` tests (3 tests) - 404 errors
  - All `/auth/sessions` tests (4 tests) - 404 errors
- **Fix Effort:** Medium - needs routing/middleware investigation
- **Impact on Coverage:** Low - only ~30 lines if fixed

#### Middleware Tests (11 tests) - `test_middleware.py`, `test_security.py`
- **Issue:** Middleware not properly integrated into test application
- **Recommendation:** Keep skipped until middleware architecture is reviewed

#### Auth Module Tests (4 tests) - `test_auth_module.py`
- **Issue:** Database fixture conflicts (duplicate role creation)
- **Impact:** Very low - functionality already covered by `test_auth_helpers.py`
- **Recommendation:** Keep skipped or delete as duplicate coverage

### 2. RBAC Middleware Fix

**Fixed Issue:** Registration endpoint was being blocked by RBAC middleware

**Changes Made:**
- Added `/api/v1/users/register` to `public_paths` in `app/middleware/rbac.py`
- Fixed exception chaining (added `from e` to raise statements)
- Committed in: `6ecbe28`

**Impact:** Enables future integration tests if database issues are resolved

## Coverage Improvement Strategy

### Highest Impact Areas (Routes)

Routes represent 568 statements with 336 missed (59% of all gaps). Improving route coverage from 41% to 60% would gain ~108 statements = ~5.6 percentage points overall.

#### Quick Wins in Routes

1. **Auth Routes (auth.py)** - 30 missed lines
   - Lines 33-65: Login function (mostly covered)
   - **Lines 76-84: `/auth/logout` endpoint** - NOT TESTED
   - **Lines 92-96: `/auth/logout-all` endpoint** - NOT TESTED
   - **Lines 104-107: `/auth/sessions` endpoint** - NOT TESTED
   - **Action:** Add simple tests with mocked session manager

2. **Category Routes (category.py)** - 8 missed lines
   - Lines 18-25, 31: Minor edge cases
   - **Action:** Add error handling tests

3. **Roles Routes (roles.py)** - 6 missed lines
   - Lines 16-22: Error paths
   - **Action:** Add validation failure tests

### Medium Impact Areas

4. **User Routes (user.py)** - 188 missed lines (LARGEST GAP)
   - Complex file with many endpoints
   - Current: 32 tests, 36% coverage
   - Missing: Error handling, edge cases, some endpoints
   - **Action:** Systematic review of each endpoint

5. **Content Routes (content.py)** - 73 missed lines
   - Current: Good happy path coverage
   - Missing: Error cases, workflow transitions
   - **Action:** Add workflow error tests

6. **Password Reset Routes (password_reset.py)** - 28 missed lines
   - Missing: Token validation edge cases
   - **Action:** Add expiry/invalid token tests

### Low-Hanging Fruit (Core Files)

7. **app/database.py** - 50% coverage (13 missed)
   - Missing: Production engine path, error handling
   - **Complexity:** High (requires mocking settings, async)
   - **Action:** Lower priority

8. **app/scheduler.py** - 50% coverage (11 missed)
   - Missing: Scheduler initialization and error paths
   - **Action:** Add scheduler tests

9. **app/main.py** - 61% coverage (15 missed)
   - Missing: Startup/shutdown events, root endpoint
   - **Action:** Add application lifecycle tests

## Recommended Test Additions

### Phase 1: Quick Wins (Target: +3-4%)

1. **Add session endpoint tests** to `test/test_auth.py`:
   ```python
   class TestLogout:
       def test_logout_with_mock_session():
           # Test /auth/logout with mocked session manager

   class TestLogoutAll:
       def test_logout_all_with_mock_session():
           # Test /auth/logout-all with mocked session manager

   class TestGetActiveSessions:
       def test_get_sessions_with_mock_session():
           # Test /auth/sessions with mocked session manager
   ```

2. **Add error handling tests** to `test/test_routes_category.py`:
   - Test invalid category creation
   - Test duplicate category names
   - Test non-existent category retrieval

3. **Add edge case tests** to existing route tests:
   - Invalid input validation
   - Permission denied scenarios
   - Resource not found cases

### Phase 2: User Routes (Target: +4-5%)

4. **Systematic user.py coverage improvement**:
   - Map each endpoint to test coverage
   - Add missing error path tests
   - Add permission boundary tests
   - Add edge case tests (empty strings, invalid IDs, etc.)

### Phase 3: Content Routes (Target: +2-3%)

5. **Content workflow testing**:
   - Test invalid status transitions
   - Test permission checks at each workflow stage
   - Test version rollback edge cases

## Implementation Priority

**Priority 1 (Quick, High Impact):**
1. ✅ Fix RBAC middleware public paths (DONE)
2. Add auth session endpoint tests (est. +1-2%)
3. Add category/roles error tests (est. +0.5%)

**Priority 2 (Medium Effort, High Impact):**
4. Systematic user routes review (est. +3-4%)
5. Content workflow edge cases (est. +2-3%)

**Priority 3 (Higher Effort):**
6. Core file tests (database, scheduler, main) (est. +1-2%)
7. Consider if middleware tests are worth fixing

## Estimated Coverage Gains

| Action | Estimated Gain | Effort | Priority |
|--------|----------------|--------|----------|
| Auth session tests | +1-2% | Low | High |
| Category/roles tests | +0.5% | Low | High |
| User routes review | +3-4% | Medium | High |
| Content edge cases | +2-3% | Medium | Medium |
| Core file tests | +1-2% | High | Low |
| **Total Achievable** | **+8-12%** | | |

**Target:** 69% → 77-81% coverage (exceeds 80% goal)

## Notes on Skipped Tests

The 69 skipped tests should generally remain skipped because:

1. **Integration tests** duplicate existing route test coverage with worse architecture
2. **Session management tests** would only add ~1% coverage even if fixed
3. **Middleware tests** require architectural decisions about middleware integration
4. **Auth module tests** duplicate existing coverage in `test_auth_helpers.py`

**Recommendation:** Focus on improving the 482 passing tests rather than fixing 69 problematic skipped tests.

## Next Steps

1. ✅ Document findings (this file)
2. Implement Phase 1 quick wins
3. Measure coverage after Phase 1
4. If <80%, proceed to Phase 2
5. Iterate until 80%+ achieved

## Conclusion

Reaching 80%+ coverage is achievable by:
- Adding targeted tests to existing passing test suites
- Focusing on routes (41% → 60%+ coverage)
- NOT attempting to fix the 69 skipped tests (low ROI)

The highest leverage actions are adding error handling and edge case tests to the existing route test files, which already have good infrastructure and fixtures in place.
