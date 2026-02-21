"""
Tests for Phase 5.2: CI/CD Pipeline & Deployment Automation.

Validates that workflow files exist and contain the expected structure,
the Dockerfile uses Python 3.12, and required jobs / steps are present.
All checks are static (file parsing only — no network or Docker calls).
"""

import re
from pathlib import Path

import yaml

WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"
DOCKERFILE_PATH = Path(__file__).parent.parent / "Dockerfile"


def _load_workflow(filename: str) -> dict:
    """Load a GitHub Actions workflow YAML, normalising the `on:` key.

    PyYAML (YAML 1.1) parses bare `on` as boolean True.  We remap it to the
    string "on" so tests can use ``wf["on"]`` uniformly.
    """
    path = WORKFLOWS_DIR / filename
    assert path.exists(), f"Workflow file missing: {path}"
    with path.open() as fh:
        raw = yaml.safe_load(fh)
    # Remap True → "on" at the top level only (GitHub Actions keyword)
    return {"on" if k is True else k: v for k, v in raw.items()}


def _dockerfile_lines() -> list[str]:
    with DOCKERFILE_PATH.open() as fh:
        return fh.readlines()


# ============================================================================
# TestWorkflowFilesExist
# ============================================================================


class TestWorkflowFilesExist:
    def test_cicd_yml_exists(self):
        assert (WORKFLOWS_DIR / "ci-cd.yml").exists()

    def test_db_migrate_yml_exists(self):
        assert (WORKFLOWS_DIR / "db-migrate.yml").exists()

    def test_rollback_yml_exists(self):
        assert (WORKFLOWS_DIR / "rollback.yml").exists()

    def test_release_yml_exists(self):
        assert (WORKFLOWS_DIR / "release.yml").exists()

    def test_redundant_tests_yml_removed(self):
        """tests.yml was redundant and should be removed."""
        assert not (WORKFLOWS_DIR / "tests.yml").exists()

    def test_redundant_lint_yml_removed(self):
        """lint.yml was redundant and should be removed."""
        assert not (WORKFLOWS_DIR / "lint.yml").exists()


# ============================================================================
# TestCiCdWorkflow
# ============================================================================


class TestCiCdWorkflow:
    def _wf(self):
        return _load_workflow("ci-cd.yml")

    def test_triggers_on_push_to_main(self):
        wf = self._wf()
        branches = wf["on"]["push"]["branches"]
        assert "main" in branches

    def test_triggers_on_push_to_develop(self):
        wf = self._wf()
        branches = wf["on"]["push"]["branches"]
        assert "develop" in branches

    def test_triggers_on_version_tags(self):
        wf = self._wf()
        tags = wf["on"]["push"].get("tags", [])
        assert any(t.startswith("v") for t in tags)

    def test_triggers_on_pull_request(self):
        wf = self._wf()
        assert "pull_request" in wf["on"]

    def test_has_quality_job(self):
        wf = self._wf()
        assert "quality" in wf["jobs"]

    def test_has_test_job(self):
        wf = self._wf()
        assert "test" in wf["jobs"]

    def test_has_build_job(self):
        wf = self._wf()
        assert "build" in wf["jobs"]

    def test_has_security_scan_job(self):
        wf = self._wf()
        assert "security-scan" in wf["jobs"]

    def test_has_deploy_staging_job(self):
        wf = self._wf()
        assert "deploy-staging" in wf["jobs"]

    def test_has_deploy_production_job(self):
        wf = self._wf()
        assert "deploy-production" in wf["jobs"]

    def test_quality_runs_ruff(self):
        wf = self._wf()
        steps = wf["jobs"]["quality"]["steps"]
        step_names = [s.get("name", "") for s in steps]
        assert any("ruff" in n.lower() for n in step_names)

    def test_quality_runs_bandit(self):
        wf = self._wf()
        steps = wf["jobs"]["quality"]["steps"]
        step_names = [s.get("name", "") for s in steps]
        assert any("bandit" in n.lower() for n in step_names)

    def test_quality_runs_mypy(self):
        wf = self._wf()
        steps = wf["jobs"]["quality"]["steps"]
        step_names = [s.get("name", "") for s in steps]
        assert any("mypy" in n.lower() for n in step_names)

    def test_quality_runs_safety(self):
        wf = self._wf()
        steps = wf["jobs"]["quality"]["steps"]
        step_names = [s.get("name", "") for s in steps]
        assert any("safety" in n.lower() for n in step_names)

    def test_test_job_has_postgres_service(self):
        wf = self._wf()
        services = wf["jobs"]["test"].get("services", {})
        assert "postgres" in services

    def test_test_job_has_redis_service(self):
        wf = self._wf()
        services = wf["jobs"]["test"].get("services", {})
        assert "redis" in services

    def test_test_job_sets_database_url(self):
        wf = self._wf()
        test_steps = wf["jobs"]["test"]["steps"]
        # Find the pytest step env
        pytest_step = next(
            (s for s in test_steps if "run" in s and "pytest" in s.get("run", "")),
            None,
        )
        assert pytest_step is not None, "pytest step not found"
        env = pytest_step.get("env", {})
        assert "DATABASE_URL" in env

    def test_test_job_sets_redis_url(self):
        wf = self._wf()
        test_steps = wf["jobs"]["test"]["steps"]
        pytest_step = next(
            (s for s in test_steps if "run" in s and "pytest" in s.get("run", "")),
            None,
        )
        assert pytest_step is not None
        env = pytest_step.get("env", {})
        assert "REDIS_URL" in env

    def test_test_job_uses_coverage(self):
        wf = self._wf()
        test_steps = wf["jobs"]["test"]["steps"]
        pytest_step = next(
            (s for s in test_steps if "run" in s and "pytest" in s.get("run", "")),
            None,
        )
        assert pytest_step is not None
        assert "--cov" in pytest_step["run"]

    def test_build_job_needs_test(self):
        wf = self._wf()
        needs = wf["jobs"]["build"].get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "test" in needs

    def test_deploy_staging_targets_develop(self):
        wf = self._wf()
        condition = wf["jobs"]["deploy-staging"].get("if", "")
        assert "develop" in condition

    def test_deploy_production_targets_version_tags(self):
        wf = self._wf()
        condition = wf["jobs"]["deploy-production"].get("if", "")
        assert "tags" in condition or "v" in condition

    def test_uses_python_312(self):
        wf = self._wf()
        env = wf.get("env", {})
        python_version = str(env.get("PYTHON_VERSION", ""))
        assert "3.12" in python_version

    def test_uses_ghcr_registry(self):
        wf = self._wf()
        env = wf.get("env", {})
        assert env.get("REGISTRY", "") == "ghcr.io"


# ============================================================================
# TestDbMigrateWorkflow
# ============================================================================


class TestDbMigrateWorkflow:
    def _wf(self):
        return _load_workflow("db-migrate.yml")

    def test_triggers_on_workflow_dispatch(self):
        wf = self._wf()
        assert "workflow_dispatch" in wf["on"]

    def test_has_environment_input(self):
        wf = self._wf()
        inputs = wf["on"]["workflow_dispatch"]["inputs"]
        assert "environment" in inputs

    def test_environment_choices_include_staging_and_production(self):
        wf = self._wf()
        choices = wf["on"]["workflow_dispatch"]["inputs"]["environment"]["options"]
        assert "staging" in choices
        assert "production" in choices

    def test_has_revision_input(self):
        wf = self._wf()
        inputs = wf["on"]["workflow_dispatch"]["inputs"]
        assert "revision" in inputs

    def test_revision_defaults_to_head(self):
        wf = self._wf()
        default = wf["on"]["workflow_dispatch"]["inputs"]["revision"]["default"]
        assert default == "head"

    def test_has_dry_run_input(self):
        wf = self._wf()
        inputs = wf["on"]["workflow_dispatch"]["inputs"]
        assert "dry_run" in inputs

    def test_has_migrate_job(self):
        wf = self._wf()
        assert "migrate" in wf["jobs"]

    def test_migrate_job_uses_environment_gate(self):
        wf = self._wf()
        env = wf["jobs"]["migrate"].get("environment", {})
        assert env is not None


# ============================================================================
# TestRollbackWorkflow
# ============================================================================


class TestRollbackWorkflow:
    def _wf(self):
        return _load_workflow("rollback.yml")

    def test_triggers_on_workflow_dispatch(self):
        wf = self._wf()
        assert "workflow_dispatch" in wf["on"]

    def test_has_environment_input(self):
        wf = self._wf()
        inputs = wf["on"]["workflow_dispatch"]["inputs"]
        assert "environment" in inputs

    def test_has_image_tag_input(self):
        wf = self._wf()
        inputs = wf["on"]["workflow_dispatch"]["inputs"]
        assert "image_tag" in inputs

    def test_has_rollback_migrations_input(self):
        wf = self._wf()
        inputs = wf["on"]["workflow_dispatch"]["inputs"]
        assert "rollback_migrations" in inputs

    def test_has_rollback_job(self):
        wf = self._wf()
        assert "rollback" in wf["jobs"]

    def test_rollback_job_uses_environment_gate(self):
        wf = self._wf()
        env = wf["jobs"]["rollback"].get("environment", {})
        assert env is not None

    def test_rollback_staging_step_present(self):
        wf = self._wf()
        steps = wf["jobs"]["rollback"]["steps"]
        staging_steps = [
            s
            for s in steps
            if "staging" in s.get("name", "").lower() or s.get("if", "") == "inputs.environment == 'staging'"
        ]
        assert len(staging_steps) > 0

    def test_rollback_production_step_present(self):
        wf = self._wf()
        steps = wf["jobs"]["rollback"]["steps"]
        prod_steps = [
            s
            for s in steps
            if "production" in s.get("name", "").lower() or s.get("if", "") == "inputs.environment == 'production'"
        ]
        assert len(prod_steps) > 0


# ============================================================================
# TestReleaseWorkflow
# ============================================================================


class TestReleaseWorkflow:
    def _wf(self):
        return _load_workflow("release.yml")

    def test_triggers_on_version_tags(self):
        wf = self._wf()
        tags = wf["on"]["push"].get("tags", [])
        assert any(t.startswith("v") for t in tags)

    def test_has_release_job(self):
        wf = self._wf()
        assert "release" in wf["jobs"]

    def test_release_job_has_contents_write_permission(self):
        wf = self._wf()
        permissions = wf["jobs"]["release"].get("permissions", {})
        assert permissions.get("contents") == "write"

    def test_extracts_version_from_tag(self):
        wf = self._wf()
        steps = wf["jobs"]["release"]["steps"]
        version_step = next(
            (s for s in steps if "version" in s.get("id", "") or "version" in s.get("name", "").lower()),
            None,
        )
        assert version_step is not None

    def test_extracts_changelog_notes(self):
        wf = self._wf()
        steps = wf["jobs"]["release"]["steps"]
        notes_step = next(
            (s for s in steps if "changelog" in s.get("name", "").lower() or "notes" in s.get("id", "")),
            None,
        )
        assert notes_step is not None

    def test_uses_softprops_release_action(self):
        wf = self._wf()
        steps = wf["jobs"]["release"]["steps"]
        release_step = next(
            (s for s in steps if "softprops" in s.get("uses", "")),
            None,
        )
        assert release_step is not None

    def test_release_attaches_changelog(self):
        wf = self._wf()
        steps = wf["jobs"]["release"]["steps"]
        release_step = next(
            (s for s in steps if "softprops" in s.get("uses", "")),
            None,
        )
        assert release_step is not None
        files = release_step.get("with", {}).get("files", "")
        assert "CHANGELOG.md" in str(files)


# ============================================================================
# TestDockerfile
# ============================================================================


class TestDockerfile:
    def test_uses_python_312_builder(self):
        lines = _dockerfile_lines()
        builder_line = next((ln for ln in lines if "FROM python" in ln and "builder" in ln), None)
        assert builder_line is not None
        assert "3.12" in builder_line

    def test_uses_python_312_runtime(self):
        lines = _dockerfile_lines()
        runtime_lines = [ln for ln in lines if "FROM python" in ln and "builder" not in ln]
        assert len(runtime_lines) > 0
        assert all("3.12" in ln for ln in runtime_lines)

    def test_no_python_310_references(self):
        content = "".join(_dockerfile_lines())
        assert "python3.10" not in content
        assert "python:3.10" not in content

    def test_site_packages_path_uses_312(self):
        lines = _dockerfile_lines()
        site_packages_line = next((ln for ln in lines if "site-packages" in ln), None)
        assert site_packages_line is not None
        assert "3.12" in site_packages_line

    def test_exposes_port_8000(self):
        lines = _dockerfile_lines()
        expose_line = next((ln for ln in lines if ln.strip().startswith("EXPOSE")), None)
        assert expose_line is not None
        assert "8000" in expose_line

    def test_has_healthcheck(self):
        content = "".join(_dockerfile_lines())
        assert "HEALTHCHECK" in content

    def test_runs_as_non_root(self):
        content = "".join(_dockerfile_lines())
        assert "appuser" in content
        assert "USER appuser" in content

    def test_uses_slim_base(self):
        lines = _dockerfile_lines()
        from_lines = [ln for ln in lines if ln.strip().startswith("FROM")]
        assert all("slim" in ln for ln in from_lines)


# ============================================================================
# TestCiCdIntegration — cross-workflow sanity checks
# ============================================================================


class TestCiCdIntegration:
    def test_all_workflow_files_are_valid_yaml(self):
        """Every .yml in .github/workflows must be valid YAML."""
        for wf_path in WORKFLOWS_DIR.iterdir():
            if wf_path.suffix in {".yml", ".yaml"}:
                with wf_path.open() as fh:
                    doc = yaml.safe_load(fh)
                assert isinstance(doc, dict), f"{wf_path.name} is not a valid YAML mapping"

    def test_all_workflows_have_name(self):
        for wf_path in WORKFLOWS_DIR.iterdir():
            if wf_path.suffix in {".yml", ".yaml"}:
                wf = _load_workflow(wf_path.name)
                assert "name" in wf, f"{wf_path.name} is missing 'name' field"

    def test_all_workflows_have_on_trigger(self):
        for wf_path in WORKFLOWS_DIR.iterdir():
            if wf_path.suffix in {".yml", ".yaml"}:
                wf = _load_workflow(wf_path.name)
                assert "on" in wf, f"{wf_path.name} is missing 'on' trigger"

    def test_all_workflows_have_jobs(self):
        for wf_path in WORKFLOWS_DIR.iterdir():
            if wf_path.suffix in {".yml", ".yaml"}:
                wf = _load_workflow(wf_path.name)
                assert "jobs" in wf, f"{wf_path.name} is missing 'jobs'"

    def test_python_version_consistent_between_dockerfile_and_cicd(self):
        """Dockerfile and ci-cd.yml must agree on Python version."""
        cicd = _load_workflow("ci-cd.yml")
        cicd_version = str(cicd.get("env", {}).get("PYTHON_VERSION", ""))

        lines = _dockerfile_lines()
        builder_line = next((ln for ln in lines if "FROM python" in ln and "builder" in ln), "")
        # Extract version from "FROM python:3.12-slim as builder"
        match = re.search(r"python:(\d+\.\d+)", builder_line)
        dockerfile_version = match.group(1) if match else ""

        assert cicd_version == dockerfile_version, (
            f"ci-cd.yml PYTHON_VERSION={cicd_version!r} doesn't match Dockerfile {dockerfile_version!r}"
        )
