"""
Phase 5.4 Scalability Tests

Covers:
- Read replica config and get_read_db dependency
- Connection pool metrics gauges
- Redis Sentinel config and host parsing
- Cache Manager failover and auto-retry behaviour
- Health check extensions (read_replica, connection_pool)
- Nginx and docker-compose.prod.yml configuration
"""

import pathlib
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
NGINX_CONF = PROJECT_ROOT / "nginx" / "nginx.conf"
COMPOSE_PROD = PROJECT_ROOT / "docker-compose.prod.yml"
SENTINEL_CONF = PROJECT_ROOT / "redis" / "sentinel.conf"
PG_CONF = PROJECT_ROOT / "postgres" / "postgresql.conf"
PG_HBA = PROJECT_ROOT / "postgres" / "pg_hba.conf"


# =============================================================================
# TestReadReplicaConfig
# =============================================================================


class TestReadReplicaConfig:
    def test_database_read_replica_url_default_is_none(self):
        from app.config import settings

        assert settings.database_read_replica_url is None

    def test_database_read_replica_url_can_be_set_via_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_READ_REPLICA_URL", "postgresql+asyncpg://u:p@replica:5432/db")
        from importlib import reload

        import app.config as cfg_module

        reload(cfg_module)
        assert cfg_module.settings.database_read_replica_url == "postgresql+asyncpg://u:p@replica:5432/db"
        # Restore
        monkeypatch.delenv("DATABASE_READ_REPLICA_URL", raising=False)
        reload(cfg_module)

    def test_get_read_db_is_async_generator(self):
        from inspect import isasyncgenfunction

        from app.database import get_read_db

        assert isasyncgenfunction(get_read_db)

    def test_get_pool_stats_returns_dict(self):
        from app.database import get_pool_stats

        stats = get_pool_stats()
        assert isinstance(stats, dict)

    def test_get_pool_stats_has_primary_and_replica_keys(self):
        from app.database import get_pool_stats

        stats = get_pool_stats()
        assert "primary" in stats
        assert "replica" in stats

    def test_get_pool_stats_primary_has_expected_fields(self):
        from app.database import get_pool_stats

        stats = get_pool_stats()
        primary = stats["primary"]
        for key in ("size", "checkedin", "checkedout", "overflow"):
            assert key in primary, f"Missing key '{key}' in primary pool stats"

    def test_get_pool_stats_replica_has_expected_fields(self):
        from app.database import get_pool_stats

        stats = get_pool_stats()
        replica = stats["replica"]
        for key in ("size", "checkedin", "checkedout", "overflow"):
            assert key in replica, f"Missing key '{key}' in replica pool stats"

    def test_read_async_session_local_exists(self):
        from app.database import ReadAsyncSessionLocal

        assert ReadAsyncSessionLocal is not None

    def test_pool_monitor_interval_setting_default(self):
        from app.config import settings

        assert settings.pool_monitor_interval_seconds == 15

    def test_instance_id_setting_default(self):
        from app.config import settings

        assert settings.instance_id == "web"


# =============================================================================
# TestPoolMetrics
# =============================================================================


class TestPoolMetrics:
    def test_db_pool_checked_out_gauge_exists(self):
        from app.utils.metrics import DB_POOL_CHECKED_OUT

        assert DB_POOL_CHECKED_OUT is not None

    def test_db_pool_available_gauge_exists(self):
        from app.utils.metrics import DB_POOL_AVAILABLE

        assert DB_POOL_AVAILABLE is not None

    def test_db_pool_overflow_gauge_exists(self):
        from app.utils.metrics import DB_POOL_OVERFLOW

        assert DB_POOL_OVERFLOW is not None

    def test_db_pool_checked_out_has_engine_label(self):
        from app.utils.metrics import DB_POOL_CHECKED_OUT

        assert "engine" in DB_POOL_CHECKED_OUT._labelnames

    def test_db_pool_available_has_engine_label(self):
        from app.utils.metrics import DB_POOL_AVAILABLE

        assert "engine" in DB_POOL_AVAILABLE._labelnames

    def test_redis_connected_gauge_exists(self):
        from app.utils.metrics import REDIS_CONNECTED

        assert REDIS_CONNECTED is not None

    def test_redis_connected_has_role_label(self):
        from app.utils.metrics import REDIS_CONNECTED

        assert "role" in REDIS_CONNECTED._labelnames

    def test_redis_sentinel_failovers_counter_exists(self):
        from app.utils.metrics import REDIS_SENTINEL_FAILOVERS

        assert REDIS_SENTINEL_FAILOVERS is not None

    def test_update_pool_metrics_callable(self):
        from app.utils.metrics import update_pool_metrics

        # Should not raise
        update_pool_metrics("primary", {"checkedout": 5, "checkedin": 15, "overflow": 0, "size": 20})

    def test_update_pool_metrics_sets_gauges(self):
        from app.utils.metrics import DB_POOL_CHECKED_OUT, update_pool_metrics

        update_pool_metrics("primary", {"checkedout": 7, "checkedin": 13, "overflow": 2, "size": 20})
        value = DB_POOL_CHECKED_OUT.labels(engine="primary")._value.get()
        assert value == 7.0

    def test_pool_monitor_install_function_exists(self):
        from app.utils.pool_monitor import install_pool_monitor

        assert callable(install_pool_monitor)

    def test_pool_monitor_registers_job_with_scheduler(self):
        from app.utils.pool_monitor import install_pool_monitor

        mock_scheduler = MagicMock()
        install_pool_monitor(mock_scheduler, interval_seconds=30)
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs.get("id") == "pool_monitor"


# =============================================================================
# TestRedisSentinelConfig
# =============================================================================


class TestRedisSentinelConfig:
    def test_redis_sentinel_hosts_default_is_none(self):
        from app.config import settings

        assert settings.redis_sentinel_hosts is None

    def test_redis_sentinel_master_name_default(self):
        from app.config import settings

        assert settings.redis_sentinel_master_name == "mymaster"

    def test_redis_sentinel_password_default_is_none(self):
        from app.config import settings

        assert settings.redis_sentinel_password is None

    def test_cache_manager_parse_sentinel_hosts_two_entries(self):
        from app.utils.cache import CacheManager

        result = CacheManager._parse_sentinel_hosts("host1:26379,host2:26379")
        assert result == [("host1", 26379), ("host2", 26379)]

    def test_cache_manager_parse_sentinel_hosts_default_port(self):
        from app.utils.cache import CacheManager

        result = CacheManager._parse_sentinel_hosts("mysentinel")
        assert result == [("mysentinel", 26379)]

    def test_cache_manager_parse_sentinel_hosts_single_entry(self):
        from app.utils.cache import CacheManager

        result = CacheManager._parse_sentinel_hosts("sentinel1:26380")
        assert result == [("sentinel1", 26380)]

    def test_session_manager_parse_sentinel_hosts(self):
        from app.utils.session import RedisSessionManager

        result = RedisSessionManager._parse_sentinel_hosts("s1:26379,s2:26379,s3:26379")
        assert len(result) == 3
        assert result[0] == ("s1", 26379)

    def test_cache_manager_uses_sentinel_when_configured(self):
        from app.utils.cache import CacheManager

        cm = CacheManager()
        mock_sentinel = MagicMock()
        mock_master = AsyncMock()
        mock_master.ping = AsyncMock(return_value=True)
        mock_sentinel.master_for.return_value = mock_master

        with (
            patch("app.utils.cache.settings") as mock_settings,
            patch("redis.asyncio.Sentinel", return_value=mock_sentinel) as mock_sentinel_cls,
            patch("app.utils.metrics.REDIS_CONNECTED"),
        ):
            mock_settings.redis_sentinel_hosts = "sentinel1:26379"
            mock_settings.redis_sentinel_password = None
            mock_settings.redis_sentinel_master_name = "mymaster"

            import asyncio

            asyncio.run(cm.connect())
            mock_sentinel_cls.assert_called_once()
            mock_sentinel.master_for.assert_called_once_with("mymaster", decode_responses=True)

    def test_cache_manager_has_last_connect_attempt_attribute(self):
        from app.utils.cache import CacheManager

        cm = CacheManager()
        assert hasattr(cm, "_last_connect_attempt")
        assert cm._last_connect_attempt == 0

    def test_session_manager_has_sentinel_attribute(self):
        from app.utils.session import RedisSessionManager

        sm = RedisSessionManager()
        assert hasattr(sm, "_sentinel")


# =============================================================================
# TestCacheFailover
# =============================================================================


class TestCacheFailover:
    def test_cache_get_returns_none_when_disabled(self):
        from app.utils.cache import CacheManager

        cm = CacheManager()
        cm._enabled = False
        import asyncio

        result = asyncio.run(cm.get("somekey"))
        assert result is None

    def test_cache_set_returns_false_when_disabled(self):
        from app.utils.cache import CacheManager

        cm = CacheManager()
        cm._enabled = False
        import asyncio

        result = asyncio.run(cm.set("somekey", {"data": 1}))
        assert result is False

    def test_delete_returns_false_when_disabled(self):
        from app.utils.cache import CacheManager

        cm = CacheManager()
        cm._enabled = False
        import asyncio

        result = asyncio.run(cm.delete("somekey"))
        assert result is False

    def test_delete_pattern_returns_zero_when_disabled(self):
        from app.utils.cache import CacheManager

        cm = CacheManager()
        cm._enabled = False
        import asyncio

        result = asyncio.run(cm.delete_pattern("cache:*"))
        assert result == 0

    def test_cache_does_not_retry_before_30_seconds(self):
        """If less than 30s have elapsed, _maybe_retry_connect should not reconnect."""
        import asyncio
        import time

        from app.utils.cache import CacheManager

        cm = CacheManager()
        cm._enabled = False
        cm._last_connect_attempt = time.time() - 10  # 10s ago (< 30s threshold)

        connect_calls = []

        async def fake_connect():
            connect_calls.append(1)
            cm._enabled = True

        cm.connect = fake_connect

        asyncio.run(cm._maybe_retry_connect())
        assert len(connect_calls) == 0, "Should not retry before 30s cooldown"

    def test_cache_retries_after_30_seconds(self):
        """After 30s cooldown, _maybe_retry_connect should re-attempt."""
        import asyncio
        import time

        from app.utils.cache import CacheManager

        cm = CacheManager()
        cm._enabled = False
        cm._last_connect_attempt = time.time() - 31  # 31s ago (> 30s threshold)

        connect_calls = []

        async def fake_connect():
            connect_calls.append(1)
            cm._enabled = True

        cm.connect = fake_connect

        asyncio.run(cm._maybe_retry_connect())
        assert len(connect_calls) == 1, "Should retry after 30s cooldown"
        assert cm._enabled is True

    def test_cache_re_enables_after_successful_retry(self):
        """After successful reconnect, _enabled should be True and cache functional."""
        import asyncio
        import time

        from app.utils.cache import CacheManager

        cm = CacheManager()
        cm._enabled = False
        cm._last_connect_attempt = time.time() - 35

        async def fake_connect():
            cm._enabled = True
            cm._redis = AsyncMock()

        cm.connect = fake_connect
        asyncio.run(cm._maybe_retry_connect())
        assert cm._enabled is True


# =============================================================================
# TestHealthCheckExtensions
# =============================================================================


class TestHealthCheckExtensions:
    def setup_method(self):
        from main import app

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_detailed_health_endpoint_responds(self):
        response = self.client.get("/health/detailed", follow_redirects=True)
        assert response.status_code == 200

    def test_detailed_health_includes_read_replica_key(self):
        response = self.client.get("/health/detailed", follow_redirects=True)
        data = response.json()
        assert "read_replica" in data["checks"]

    def test_read_replica_not_configured_status(self):
        """Without DATABASE_READ_REPLICA_URL, status should be 'not_configured'."""
        from app.config import settings

        if settings.database_read_replica_url:
            pytest.skip("Replica URL is configured — skipping not_configured check")
        response = self.client.get("/health/detailed", follow_redirects=True)
        data = response.json()
        assert data["checks"]["read_replica"]["status"] == "not_configured"

    def test_detailed_health_includes_connection_pool_key(self):
        response = self.client.get("/health/detailed", follow_redirects=True)
        data = response.json()
        assert "connection_pool" in data["checks"]

    def test_connection_pool_check_has_status(self):
        response = self.client.get("/health/detailed", follow_redirects=True)
        data = response.json()
        pool_check = data["checks"]["connection_pool"]
        assert "status" in pool_check
        assert pool_check["status"] in ("healthy", "warning", "critical")

    def test_pool_health_utilisation_threshold_warning(self):
        from app.routes.monitoring import _check_pool_health

        with patch("app.routes.monitoring.get_pool_stats") as mock_stats:
            # 18 checked-out / (20 pool_size + 5 overflow) = 72% → warning
            mock_stats.return_value = {
                "primary": {"size": 20, "checkedout": 18, "checkedin": 2, "overflow": 5},
                "replica": {"size": 0, "checkedout": 0, "checkedin": 0, "overflow": 0},
            }
            result = _check_pool_health()
        assert result["status"] == "warning"

    def test_pool_health_utilisation_threshold_critical(self):
        from app.routes.monitoring import _check_pool_health

        with patch("app.routes.monitoring.get_pool_stats") as mock_stats:
            mock_stats.return_value = {
                "primary": {"size": 20, "checkedout": 23, "checkedin": 2, "overflow": 5},
                "replica": {"size": 0, "checkedout": 0, "checkedin": 0, "overflow": 0},
            }
            result = _check_pool_health()
        assert result["status"] == "critical"

    def test_pool_health_utilisation_threshold_healthy(self):
        from app.routes.monitoring import _check_pool_health

        with patch("app.routes.monitoring.get_pool_stats") as mock_stats:
            mock_stats.return_value = {
                "primary": {"size": 20, "checkedout": 5, "checkedin": 15, "overflow": 0},
                "replica": {"size": 0, "checkedout": 0, "checkedin": 0, "overflow": 0},
            }
            result = _check_pool_health()
        assert result["status"] == "healthy"

    def test_metrics_summary_includes_connection_pool(self):
        response = self.client.get("/metrics/summary", follow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert "connection_pool" in data

    def test_metrics_summary_connection_pool_has_primary(self):
        response = self.client.get("/metrics/summary", follow_redirects=True)
        data = response.json()
        pool = data["connection_pool"]
        assert "primary" in pool

    def test_metrics_summary_connection_pool_has_replica_configured_flag(self):
        response = self.client.get("/metrics/summary", follow_redirects=True)
        data = response.json()
        pool = data["connection_pool"]
        assert "read_replica_configured" in pool


# =============================================================================
# TestNginxAndDockerConfig
# =============================================================================


class TestNginxAndDockerConfig:
    def test_nginx_conf_exists(self):
        assert NGINX_CONF.exists(), "nginx/nginx.conf not found"

    def test_nginx_conf_has_proxy_next_upstream(self):
        content = NGINX_CONF.read_text()
        assert "proxy_next_upstream" in content

    def test_nginx_conf_proxy_next_upstream_covers_502_503_504(self):
        content = NGINX_CONF.read_text()
        line = next((ln for ln in content.splitlines() if "proxy_next_upstream" in ln and "http_502" in ln), None)
        assert line is not None, "proxy_next_upstream should include http_502"
        assert "http_503" in line
        assert "http_504" in line

    def test_nginx_conf_no_ip_hash(self):
        content = NGINX_CONF.read_text()
        assert "ip_hash" not in content, "ip_hash should NOT be set — JWT sessions are stateless"

    def test_nginx_conf_has_keepalive(self):
        content = NGINX_CONF.read_text()
        assert "keepalive" in content

    def test_nginx_conf_has_least_conn(self):
        content = NGINX_CONF.read_text()
        assert "least_conn" in content

    def test_nginx_conf_has_max_fails_on_server_lines(self):
        content = NGINX_CONF.read_text()
        assert re.search(r"server\s+web\d+:8000.*max_fails=\d+", content)

    def test_docker_compose_prod_has_db_replica_service(self):
        assert COMPOSE_PROD.exists()
        raw = yaml.safe_load(COMPOSE_PROD.read_text())
        assert "db_replica" in raw.get("services", {})

    def test_docker_compose_prod_has_redis_sentinel_service(self):
        raw = yaml.safe_load(COMPOSE_PROD.read_text())
        assert "redis_sentinel" in raw.get("services", {})

    def test_docker_compose_prod_web1_has_replica_env(self):
        raw = yaml.safe_load(COMPOSE_PROD.read_text())
        web1_env = raw["services"]["web1"].get("environment", [])
        env_str = " ".join(str(e) for e in web1_env)
        assert "DATABASE_READ_REPLICA_URL" in env_str

    def test_docker_compose_prod_web1_has_sentinel_env(self):
        raw = yaml.safe_load(COMPOSE_PROD.read_text())
        web1_env = raw["services"]["web1"].get("environment", [])
        env_str = " ".join(str(e) for e in web1_env)
        assert "REDIS_SENTINEL_HOSTS" in env_str

    def test_sentinel_conf_exists(self):
        assert SENTINEL_CONF.exists(), "redis/sentinel.conf not found"

    def test_sentinel_conf_has_monitor_directive(self):
        content = SENTINEL_CONF.read_text()
        assert "sentinel monitor mymaster" in content

    def test_postgres_conf_exists(self):
        assert PG_CONF.exists(), "postgres/postgresql.conf not found"

    def test_postgres_conf_has_wal_level_replica(self):
        content = PG_CONF.read_text()
        assert "wal_level = replica" in content

    def test_postgres_pg_hba_exists(self):
        assert PG_HBA.exists(), "postgres/pg_hba.conf not found"

    def test_postgres_pg_hba_allows_replication(self):
        content = PG_HBA.read_text()
        assert "replication" in content
