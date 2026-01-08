# Codecov Setup Instructions

Follow these steps to enable coverage reporting with Codecov.

## Step 1: Sign Up for Codecov

1. Go to [codecov.io](https://codecov.io/)
2. Click "Sign in with GitHub"
3. Authorize Codecov to access your GitHub account

## Step 2: Add Your Repository

1. Once signed in, you'll see your repositories
2. Find `cms-project` in the list
3. Click "Setup repo" or toggle it to enable coverage

## Step 3: Get Your Upload Token

1. Click on your repository in Codecov dashboard
2. Go to Settings → General
3. Copy your "Repository Upload Token"
   - It will look like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

## Step 4: Add Token to GitHub Secrets

1. Go to your GitHub repository:
   ```
   https://github.com/TurtleWithGlasses/cms-project/settings/secrets/actions
   ```

2. Click "New repository secret"

3. Name: `CODECOV_TOKEN`
   Value: [paste your token from Step 3]

4. Click "Add secret"

## Step 5: Verify It Works

1. Go to Actions tab in GitHub
2. Re-run the "Tests" workflow (or push a new commit)
3. Check the "Upload coverage to Codecov" step
4. It should now succeed and upload coverage data

## Step 6: View Coverage Reports

1. Go to [codecov.io/gh/TurtleWithGlasses/cms-project](https://codecov.io/gh/TurtleWithGlasses/cms-project)
2. You'll see:
   - Overall coverage percentage
   - Coverage by file
   - Coverage trends over time
   - Pull request coverage comparisons

## Configuration

The coverage configuration is already set up in `codecov.yml`:
- Project target: 70% coverage
- Patch target: 80% coverage for new code
- Ignores test files, migrations, and __pycache__

## Badges

Once Codecov is set up, you can add these badges to your README:

```markdown
[![codecov](https://codecov.io/gh/TurtleWithGlasses/cms-project/branch/main/graph/badge.svg)](https://codecov.io/gh/TurtleWithGlasses/cms-project)
```

## Troubleshooting

### Token Not Working
- Make sure the token is exactly as shown in Codecov (no extra spaces)
- Secret name must be exactly `CODECOV_TOKEN` (case-sensitive)

### Coverage Not Uploading
- Check workflow logs in GitHub Actions
- Verify `pytest-cov` is installed (it is, in requirements.txt)
- Ensure `coverage.xml` is being generated

### Coverage Seems Low
- Coverage only measures `app/` directory (configured in workflow)
- Test files are excluded from coverage (configured in codecov.yml)
- Current coverage is around 67% - this is the starting point

## Next Steps

After setup is complete:
1. Monitor coverage on pull requests
2. Work towards 80% coverage goal
3. Use coverage reports to identify untested code
4. Add tests for critical business logic first
