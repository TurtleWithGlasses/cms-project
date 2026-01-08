# Pull Request

## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🎨 Code style/refactoring (no functional changes)
- [ ] ✅ Test improvements
- [ ] 🔧 Configuration/build changes

## Related Issues

<!-- Link to related issues using #issue_number -->

Closes #
Relates to #

## Changes Made

<!-- List the specific changes made in this PR -->

-
-
-

## Testing

### Test Coverage

- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Tests cover edge cases
- [ ] Coverage maintained or improved

### Test Commands Run

```bash
# List the test commands you ran
pytest test/ -v
pytest test/ --cov=app --cov-report=term-missing
```

### Manual Testing

<!-- Describe any manual testing you performed -->

## Checklist

<!-- Mark completed items with an "x" -->

### Code Quality

- [ ] Code follows project style guidelines (Ruff)
- [ ] Type hints added where appropriate
- [ ] Docstrings added/updated for new functions/classes
- [ ] No commented-out code or debug statements
- [ ] Pre-commit hooks pass

### Tests

- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Test coverage is maintained (67%+)
- [ ] Tests follow existing patterns

### Documentation

- [ ] README updated if needed
- [ ] KNOWN_ISSUES.md updated if relevant
- [ ] API documentation updated (if endpoints changed)
- [ ] Code comments added for complex logic

### Security

- [ ] No sensitive data (passwords, keys, tokens) committed
- [ ] Input validation added for new endpoints
- [ ] Authentication/authorization checks in place
- [ ] SQL injection prevention (using ORM)
- [ ] XSS prevention (sanitizing inputs)

### Database

- [ ] Migration created if schema changed
- [ ] Migration tested (upgrade and downgrade)
- [ ] No data loss in migration
- [ ] Backwards compatible (if possible)

## Breaking Changes

<!-- If this is a breaking change, describe what breaks and how to migrate -->

## Performance Impact

<!-- Describe any performance implications -->

## Screenshots

<!-- If applicable, add screenshots to help explain your changes -->

## Additional Notes

<!-- Any additional information that reviewers should know -->

## Reviewer Notes

<!-- Specific areas you'd like reviewers to focus on -->

---

## Post-Merge Checklist

<!-- For maintainers - to be completed after merge -->

- [ ] Update CHANGELOG.md
- [ ] Tag release if applicable
- [ ] Update documentation site
- [ ] Announce changes if significant
