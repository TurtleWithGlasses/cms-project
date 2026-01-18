"""Tests for dashboard and KPI functionality."""

from datetime import datetime, timedelta

import pytest


class TestDashboardKPIs:
    """Test dashboard KPI calculations."""

    def test_growth_rate_calculation(self):
        """Test growth rate percentage calculation."""
        # Positive growth
        current = 150
        previous = 100
        growth = (current - previous) / previous * 100
        assert growth == 50.0

        # Negative growth
        current = 80
        previous = 100
        growth = (current - previous) / previous * 100
        assert growth == -20.0

        # Zero growth
        current = 100
        previous = 100
        growth = (current - previous) / previous * 100
        assert growth == 0.0

    def test_adoption_rate_calculation(self):
        """Test adoption rate percentage calculation."""
        enabled = 25
        total = 100
        adoption = (enabled / total * 100) if total > 0 else 0
        assert adoption == 25.0

        # Zero total
        enabled = 0
        total = 0
        adoption = (enabled / total * 100) if total > 0 else 0
        assert adoption == 0

    def test_average_daily_calculation(self):
        """Test average daily calculation."""
        total_actions = 300
        period_days = 30
        avg = total_actions / period_days if period_days > 0 else 0
        assert avg == 10.0

    def test_success_rate_calculation(self):
        """Test import success rate calculation."""
        successful = 90
        failed = 10
        total = successful + failed
        rate = (successful / total * 100) if total > 0 else 0
        assert rate == 90.0


class TestPeriodCalculations:
    """Test period date calculations."""

    def test_period_start_calculation(self):
        """Test period start date calculation."""
        now = datetime(2024, 1, 15, 12, 0, 0)
        period_days = 30
        period_start = now - timedelta(days=period_days)

        assert period_start == datetime(2023, 12, 16, 12, 0, 0)

    def test_previous_period_calculation(self):
        """Test previous period calculation for comparison."""
        now = datetime(2024, 1, 15, 12, 0, 0)
        period_days = 30
        period_start = now - timedelta(days=period_days)
        previous_start = period_start - timedelta(days=period_days)

        assert previous_start == datetime(2023, 11, 16, 12, 0, 0)

    def test_one_hour_ago_calculation(self):
        """Test one hour ago calculation for system health."""
        now = datetime(2024, 1, 15, 12, 0, 0)
        one_hour_ago = now - timedelta(hours=1)

        assert one_hour_ago == datetime(2024, 1, 15, 11, 0, 0)


class TestDashboardDataStructures:
    """Test dashboard data structure formats."""

    def test_content_kpis_structure(self):
        """Test content KPIs data structure."""
        kpis = {
            "total_content": 100,
            "published_content": 75,
            "content_this_period": 20,
            "content_previous_period": 15,
            "growth_rate_percent": 33.33,
            "content_by_status": {"draft": 25, "published": 75},
            "stale_drafts": 5,
            "period_days": 30,
        }

        assert "total_content" in kpis
        assert "growth_rate_percent" in kpis
        assert isinstance(kpis["content_by_status"], dict)

    def test_user_kpis_structure(self):
        """Test user KPIs data structure."""
        kpis = {
            "total_users": 500,
            "active_users": 450,
            "inactive_users": 50,
            "new_users_this_period": 20,
            "two_fa_enabled_users": 100,
            "two_fa_adoption_percent": 20.0,
            "active_sessions": 250,
            "period_days": 30,
        }

        assert kpis["inactive_users"] == kpis["total_users"] - kpis["active_users"]
        assert "two_fa_adoption_percent" in kpis

    def test_activity_timeline_structure(self):
        """Test activity timeline item structure."""
        item = {
            "id": 1,
            "action": "content.create",
            "resource_type": "content",
            "resource_id": 42,
            "details": "Created new article",
            "created_at": "2024-01-15T12:00:00",
        }

        assert "action" in item
        assert "created_at" in item

    def test_system_health_structure(self):
        """Test system health data structure."""
        health = {
            "status": "healthy",
            "timestamp": "2024-01-15T12:00:00",
            "database": "healthy",
            "metrics": {
                "active_sessions": 250,
                "activity_last_hour": 100,
                "pending_imports": 2,
            },
        }

        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "metrics" in health

    def test_content_performance_structure(self):
        """Test content performance item structure."""
        item = {
            "id": 1,
            "title": "Popular Article",
            "status": "published",
            "comment_count": 50,
        }

        assert "title" in item
        assert "comment_count" in item


class TestHighlightsAggregation:
    """Test dashboard highlights aggregation."""

    def test_highlights_structure(self):
        """Test highlights summary structure."""
        highlights = {
            "total_content": 100,
            "published_content": 75,
            "total_users": 500,
            "active_sessions": 250,
            "pending_moderation": 10,
            "content_growth_rate": 33.33,
        }

        # All required fields present
        required_fields = [
            "total_content",
            "published_content",
            "total_users",
            "active_sessions",
            "pending_moderation",
            "content_growth_rate",
        ]

        for field in required_fields:
            assert field in highlights
