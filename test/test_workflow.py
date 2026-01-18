"""
Tests for Workflow functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.workflow import WorkflowState, WorkflowTransition, WorkflowType
from main import app


class TestWorkflowType:
    """Tests for workflow types."""

    def test_workflow_type_values(self):
        """Test workflow type enum values."""
        assert WorkflowType.CONTENT.value == "content"
        assert WorkflowType.COMMENT.value == "comment"
        assert WorkflowType.USER.value == "user"
        assert WorkflowType.CUSTOM.value == "custom"


class TestWorkflowState:
    """Tests for WorkflowState model."""

    def test_state_creation(self):
        """Test state model defaults."""
        state = WorkflowState(
            name="draft",
            display_name="Draft",
            workflow_type=WorkflowType.CONTENT,
        )

        assert state.name == "draft"
        assert state.display_name == "Draft"
        assert state.is_initial is False
        assert state.is_final is False
        assert state.is_active is True
        assert state.color == "#6B7280"

    def test_initial_state(self):
        """Test initial state flag."""
        state = WorkflowState(
            name="draft",
            display_name="Draft",
            is_initial=True,
        )

        assert state.is_initial is True

    def test_final_state(self):
        """Test final state flag."""
        state = WorkflowState(
            name="published",
            display_name="Published",
            is_final=True,
        )

        assert state.is_final is True


class TestWorkflowTransition:
    """Tests for WorkflowTransition model."""

    def test_get_required_roles_empty(self):
        """Test parsing empty required roles."""
        transition = WorkflowTransition(
            name="Test",
            from_state_id=1,
            to_state_id=2,
            required_roles=None,
        )

        assert transition.get_required_roles() == []

    def test_get_required_roles(self):
        """Test parsing required roles."""
        transition = WorkflowTransition(
            name="Approve",
            from_state_id=1,
            to_state_id=2,
            required_roles="admin,editor",
        )

        roles = transition.get_required_roles()
        assert roles == ["admin", "editor"]

    def test_get_notify_roles(self):
        """Test parsing notify roles."""
        transition = WorkflowTransition(
            name="Submit",
            from_state_id=1,
            to_state_id=2,
            notify_roles="admin,manager",
        )

        roles = transition.get_notify_roles()
        assert roles == ["admin", "manager"]


class TestWorkflowRoutes:
    """Tests for workflow endpoints."""

    @pytest.mark.asyncio
    async def test_list_states(self):
        """Test listing workflow states."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/workflow/states")

        assert response.status_code == 200
        # Empty list is valid - no states exist initially
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_states_invalid_type(self):
        """Test listing with invalid workflow type."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/workflow/states?workflow_type=invalid")

        assert response.status_code == 400
        assert "Invalid workflow type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_transitions(self):
        """Test listing workflow transitions."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/workflow/transitions")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_create_state_requires_auth(self):
        """Test that creating states requires authentication."""
        state_data = {
            "name": "test",
            "display_name": "Test State",
            "workflow_type": "content",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/workflow/states", json=state_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_available_transitions_requires_auth(self):
        """Test that getting available transitions requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/workflow/content/1/transitions")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_pending_approvals_requires_auth(self):
        """Test that getting pending approvals requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/workflow/approvals/pending")

        assert response.status_code == 401
