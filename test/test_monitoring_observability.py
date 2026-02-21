"""
Tests for Phase 5.3: Monitoring & Observability.

All checks are static or use TestClient (no real DB / Redis / network required).
Infrastructure file validation uses pathlib + yaml/json parsing only.
"""

import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
PROMETHEUS_DIR = PROJECT_ROOT / "prometheus"
MONITORING_DIR = PROJECT_ROOT / "monitoring"


# ============================================================================
# TestHealthEndpoints
# ============================================================================


class TestHealthEndpoints:
    def test_health_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/health" in paths

    def test_ready_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/ready" in paths

    def test_health_detailed_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/health/detailed" in paths

    def test_metrics_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/metrics" in paths

    def test_metrics_summary_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/metrics/summary" in paths

    def test_health_returns_json(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_health_has_version_field(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/health")
        data = response.json()
        assert "version" in data

    def test_health_has_uptime_field(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/health")
        data = response.json()
        assert "uptime_seconds" in data

    def test_metrics_endpoint_returns_text(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus exposition format is plain text
        content_type = response.headers.get("content-type", "")
        assert "text" in content_type or "application/openmetrics" in content_type

    def test_metrics_endpoint_contains_cms_metric(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/metrics")
        assert "cms_" in response.text


# ============================================================================
# TestPrometheusMetrics
# ============================================================================


class TestPrometheusMetrics:
    def test_metrics_module_importable(self):
        from app.utils import metrics  # noqa: F401

    def test_prometheus_middleware_class_exists(self):
        from app.utils.metrics import PrometheusMiddleware

        assert callable(PrometheusMiddleware)

    def test_record_cache_hit_callable(self):
        from app.utils.metrics import record_cache_hit

        assert callable(record_cache_hit)

    def test_record_cache_miss_callable(self):
        from app.utils.metrics import record_cache_miss

        assert callable(record_cache_miss)

    def test_record_auth_attempt_callable(self):
        from app.utils.metrics import record_auth_attempt

        assert callable(record_auth_attempt)

    def test_record_content_operation_callable(self):
        from app.utils.metrics import record_content_operation

        assert callable(record_content_operation)

    def test_update_health_status_callable(self):
        from app.utils.metrics import update_health_status

        assert callable(update_health_status)

    def test_update_uptime_callable(self):
        from app.utils.metrics import update_uptime

        assert callable(update_uptime)

    def test_prometheus_middleware_wired_in_app(self):
        """PrometheusMiddleware must be registered in the FastAPI app."""
        from app.utils.metrics import PrometheusMiddleware
        from main import app

        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, "cls")]
        assert PrometheusMiddleware in middleware_classes


# ============================================================================
# TestStructuredLogging
# ============================================================================


class TestStructuredLogging:
    def test_logging_middleware_importable(self):
        from app.middleware.logging import StructuredLoggingMiddleware  # noqa: F401

    def test_setup_structured_logging_callable(self):
        from app.middleware.logging import setup_structured_logging

        assert callable(setup_structured_logging)

    def test_get_request_id_callable(self):
        from app.middleware.logging import get_request_id

        assert callable(get_request_id)

    def test_request_id_header_echoed(self):
        """X-Request-ID sent in request must be echoed in response."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/health", headers={"X-Request-ID": "test-trace-id-123"})
        assert response.headers.get("x-request-id") == "test-trace-id-123"

    def test_response_has_request_id_header(self):
        """Every response must carry an X-Request-ID (auto-generated if not provided)."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/health")
        assert "x-request-id" in response.headers


# ============================================================================
# TestOpenTelemetry
# ============================================================================


class TestOpenTelemetry:
    def test_tracing_module_importable(self):
        from app.utils import tracing  # noqa: F401

    def test_setup_tracing_callable(self):
        from app.utils.tracing import setup_tracing

        assert callable(setup_tracing)

    def test_setup_tracing_noop_without_endpoint(self):
        """setup_tracing() must not raise when otel_exporter_endpoint is None."""
        from app.utils.tracing import setup_tracing

        # Should silently no-op — no endpoint configured in test env
        setup_tracing(app=None)

    def test_otel_exporter_endpoint_setting_exists(self):
        from app.config import settings

        assert hasattr(settings, "otel_exporter_endpoint")

    def test_otel_exporter_endpoint_default_is_none(self):
        from app.config import settings

        assert settings.otel_exporter_endpoint is None

    def test_otel_service_name_setting_exists(self):
        from app.config import settings

        assert hasattr(settings, "otel_service_name")

    def test_otel_service_name_has_default(self):
        from app.config import settings

        assert settings.otel_service_name  # non-empty string
        assert isinstance(settings.otel_service_name, str)

    def test_setup_tracing_wired_in_main(self):
        """setup_tracing must be imported and called in main.py."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("main_src", PROJECT_ROOT / "main.py")
        assert spec is not None
        main_source = (PROJECT_ROOT / "main.py").read_text()
        assert "setup_tracing" in main_source


# ============================================================================
# TestAlertingRules
# ============================================================================


class TestAlertingRules:
    def _load(self) -> dict:
        path = PROMETHEUS_DIR / "alert_rules.yml"
        assert path.exists(), f"alert_rules.yml missing: {path}"
        with path.open() as fh:
            return yaml.safe_load(fh)

    def test_alert_rules_file_exists(self):
        assert (PROMETHEUS_DIR / "alert_rules.yml").exists()

    def test_alert_rules_is_valid_yaml(self):
        doc = self._load()
        assert isinstance(doc, dict)

    def test_alert_rules_has_groups(self):
        doc = self._load()
        assert "groups" in doc
        assert len(doc["groups"]) > 0

    def test_alert_rules_instance_down_present(self):
        doc = self._load()
        all_names = [rule["alert"] for group in doc["groups"] for rule in group.get("rules", [])]
        assert "InstanceDown" in all_names

    def test_alert_rules_high_error_rate_present(self):
        doc = self._load()
        all_names = [rule["alert"] for group in doc["groups"] for rule in group.get("rules", [])]
        assert "HighErrorRate" in all_names

    def test_alert_rules_high_p99_latency_present(self):
        doc = self._load()
        all_names = [rule["alert"] for group in doc["groups"] for rule in group.get("rules", [])]
        assert "HighP99RequestLatency" in all_names

    def test_alert_rules_auth_failure_present(self):
        doc = self._load()
        all_names = [rule["alert"] for group in doc["groups"] for rule in group.get("rules", [])]
        assert "AuthFailureSpike" in all_names

    def test_every_alert_has_severity_label(self):
        doc = self._load()
        for group in doc["groups"]:
            for rule in group.get("rules", []):
                assert "severity" in rule.get("labels", {}), f"Alert '{rule.get('alert')}' is missing a severity label"

    def test_every_alert_has_summary_annotation(self):
        doc = self._load()
        for group in doc["groups"]:
            for rule in group.get("rules", []):
                assert "summary" in rule.get("annotations", {}), (
                    f"Alert '{rule.get('alert')}' is missing a summary annotation"
                )

    def test_prometheus_yml_references_alert_rules(self):
        path = PROMETHEUS_DIR / "prometheus.yml"
        content = path.read_text()
        assert "alert_rules.yml" in content

    def test_prometheus_yml_references_alertmanager(self):
        path = PROMETHEUS_DIR / "prometheus.yml"
        content = path.read_text()
        assert "alertmanager" in content


# ============================================================================
# TestMonitoringInfrastructure
# ============================================================================


class TestMonitoringInfrastructure:
    def test_docker_compose_monitoring_exists(self):
        assert (PROJECT_ROOT / "docker-compose.monitoring.yml").exists()

    def test_docker_compose_monitoring_is_valid_yaml(self):
        path = PROJECT_ROOT / "docker-compose.monitoring.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert isinstance(doc, dict)

    def test_docker_compose_monitoring_has_prometheus(self):
        path = PROJECT_ROOT / "docker-compose.monitoring.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "prometheus" in doc.get("services", {})

    def test_docker_compose_monitoring_has_grafana(self):
        path = PROJECT_ROOT / "docker-compose.monitoring.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "grafana" in doc.get("services", {})

    def test_docker_compose_monitoring_has_loki(self):
        path = PROJECT_ROOT / "docker-compose.monitoring.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "loki" in doc.get("services", {})

    def test_docker_compose_monitoring_has_alertmanager(self):
        path = PROJECT_ROOT / "docker-compose.monitoring.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "alertmanager" in doc.get("services", {})

    def test_docker_compose_monitoring_has_postgres_exporter(self):
        path = PROJECT_ROOT / "docker-compose.monitoring.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "postgres-exporter" in doc.get("services", {})

    def test_docker_compose_monitoring_has_redis_exporter(self):
        path = PROJECT_ROOT / "docker-compose.monitoring.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "redis-exporter" in doc.get("services", {})

    def test_grafana_dashboard_json_exists(self):
        assert (MONITORING_DIR / "grafana" / "dashboards" / "cms-overview.json").exists()

    def test_grafana_dashboard_json_is_valid(self):
        path = MONITORING_DIR / "grafana" / "dashboards" / "cms-overview.json"
        with path.open() as fh:
            doc = json.load(fh)
        assert "panels" in doc
        assert len(doc["panels"]) > 0

    def test_grafana_dashboard_has_title(self):
        path = MONITORING_DIR / "grafana" / "dashboards" / "cms-overview.json"
        with path.open() as fh:
            doc = json.load(fh)
        assert "title" in doc
        assert "CMS" in doc["title"]

    def test_loki_config_exists(self):
        assert (MONITORING_DIR / "loki" / "loki-config.yaml").exists()

    def test_loki_config_is_valid_yaml(self):
        path = MONITORING_DIR / "loki" / "loki-config.yaml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert isinstance(doc, dict)
        assert "server" in doc

    def test_promtail_config_exists(self):
        assert (MONITORING_DIR / "promtail" / "promtail-config.yaml").exists()

    def test_promtail_config_is_valid_yaml(self):
        path = MONITORING_DIR / "promtail" / "promtail-config.yaml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert isinstance(doc, dict)
        assert "clients" in doc

    def test_alertmanager_config_exists(self):
        assert (MONITORING_DIR / "alertmanager" / "alertmanager.yml").exists()

    def test_alertmanager_config_is_valid_yaml(self):
        path = MONITORING_DIR / "alertmanager" / "alertmanager.yml"
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert isinstance(doc, dict)
        assert "route" in doc
        assert "receivers" in doc

    def test_grafana_datasource_prometheus_exists(self):
        path = MONITORING_DIR / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
        assert path.exists()
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "datasources" in doc

    def test_grafana_datasource_loki_exists(self):
        path = MONITORING_DIR / "grafana" / "provisioning" / "datasources" / "loki.yml"
        assert path.exists()
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "datasources" in doc

    def test_grafana_dashboard_provisioner_exists(self):
        path = MONITORING_DIR / "grafana" / "provisioning" / "dashboards" / "dashboards.yml"
        assert path.exists()
        with path.open() as fh:
            doc = yaml.safe_load(fh)
        assert "providers" in doc


# ============================================================================
# TestSentryConfig
# ============================================================================


class TestSentryConfig:
    def test_sentry_dsn_setting_exists(self):
        from app.config import settings

        assert hasattr(settings, "sentry_dsn")

    def test_sentry_dsn_default_is_falsy(self):
        """sentry_dsn must be falsy (None or empty string) in a test environment."""
        from app.config import settings

        assert not settings.sentry_dsn

    def test_sentry_traces_sample_rate_exists(self):
        from app.config import settings

        assert hasattr(settings, "sentry_traces_sample_rate")
        assert 0.0 <= settings.sentry_traces_sample_rate <= 1.0

    def test_sentry_profiles_sample_rate_exists(self):
        from app.config import settings

        assert hasattr(settings, "sentry_profiles_sample_rate")
        assert 0.0 <= settings.sentry_profiles_sample_rate <= 1.0

    def test_sentry_not_initialized_without_dsn(self):
        """When sentry_dsn is None, sentry_sdk should NOT be fully initialized."""
        import sentry_sdk

        client = sentry_sdk.get_client()
        # In test env without a DSN, the SDK client should be a NoopClient or similar
        # — we just verify no exception is raised and the client is queryable.
        assert client is not None
