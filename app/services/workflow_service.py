"""
Workflow Service

Provides content workflow management with state machine functionality.
Supports custom states, transitions, and approval chains.
"""

import contextlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Content
from app.models.user import User
from app.models.workflow import (
    WorkflowApproval,
    WorkflowHistory,
    WorkflowState,
    WorkflowTransition,
    WorkflowType,
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing content workflows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============== State Management ==============

    async def get_states(self, workflow_type: WorkflowType = WorkflowType.CONTENT) -> list[dict]:
        """Get all states for a workflow type."""
        result = await self.db.execute(
            select(WorkflowState)
            .where(WorkflowState.workflow_type == workflow_type, WorkflowState.is_active.is_(True))
            .order_by(WorkflowState.order)
        )
        states = result.scalars().all()

        return [
            {
                "id": state.id,
                "name": state.name,
                "display_name": state.display_name,
                "description": state.description,
                "is_initial": state.is_initial,
                "is_final": state.is_final,
                "color": state.color,
                "order": state.order,
            }
            for state in states
        ]

    async def get_state_by_name(
        self,
        name: str,
        workflow_type: WorkflowType = WorkflowType.CONTENT,
    ) -> WorkflowState | None:
        """Get a state by name."""
        result = await self.db.execute(
            select(WorkflowState).where(
                WorkflowState.name == name,
                WorkflowState.workflow_type == workflow_type,
            )
        )
        return result.scalar_one_or_none()

    async def get_initial_state(self, workflow_type: WorkflowType = WorkflowType.CONTENT) -> WorkflowState | None:
        """Get the initial state for a workflow."""
        result = await self.db.execute(
            select(WorkflowState).where(
                WorkflowState.workflow_type == workflow_type,
                WorkflowState.is_initial.is_(True),
                WorkflowState.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create_state(
        self,
        name: str,
        display_name: str,
        workflow_type: WorkflowType = WorkflowType.CONTENT,
        description: str | None = None,
        is_initial: bool = False,
        is_final: bool = False,
        color: str = "#6B7280",
        order: int = 0,
    ) -> dict:
        """Create a new workflow state."""
        # Check if name already exists
        existing = await self.get_state_by_name(name, workflow_type)
        if existing:
            raise ValueError(f"State '{name}' already exists for {workflow_type.value} workflow")

        # If setting as initial, clear other initial states
        if is_initial:
            await self._clear_initial_states(workflow_type)

        state = WorkflowState(
            name=name,
            display_name=display_name,
            description=description,
            workflow_type=workflow_type,
            is_initial=is_initial,
            is_final=is_final,
            color=color,
            order=order,
        )

        self.db.add(state)
        await self.db.commit()
        await self.db.refresh(state)

        logger.info(f"Created workflow state: {name}")

        return {
            "id": state.id,
            "name": state.name,
            "display_name": state.display_name,
            "workflow_type": state.workflow_type.value,
        }

    async def _clear_initial_states(self, workflow_type: WorkflowType) -> None:
        """Clear initial flag from all states of a workflow type."""
        result = await self.db.execute(
            select(WorkflowState).where(
                WorkflowState.workflow_type == workflow_type,
                WorkflowState.is_initial.is_(True),
            )
        )
        states = result.scalars().all()
        for state in states:
            state.is_initial = False
        await self.db.commit()

    # ============== Transition Management ==============

    async def get_transitions(
        self,
        from_state_id: int | None = None,
        workflow_type: WorkflowType = WorkflowType.CONTENT,
    ) -> list[dict]:
        """Get transitions, optionally filtered by from_state."""
        query = (
            select(WorkflowTransition)
            .options(selectinload(WorkflowTransition.from_state), selectinload(WorkflowTransition.to_state))
            .where(WorkflowTransition.is_active.is_(True))
        )

        if from_state_id:
            query = query.where(WorkflowTransition.from_state_id == from_state_id)
        else:
            query = query.join(WorkflowState, WorkflowTransition.from_state_id == WorkflowState.id).where(
                WorkflowState.workflow_type == workflow_type
            )

        result = await self.db.execute(query)
        transitions = result.scalars().all()

        return [
            {
                "id": t.id,
                "name": t.name,
                "from_state": {"id": t.from_state.id, "name": t.from_state.name},
                "to_state": {"id": t.to_state.id, "name": t.to_state.name},
                "requires_approval": t.requires_approval,
                "approval_count": t.approval_count,
                "required_roles": t.get_required_roles(),
            }
            for t in transitions
        ]

    async def create_transition(
        self,
        name: str,
        from_state_id: int,
        to_state_id: int,
        required_roles: list[str] | None = None,
        requires_approval: bool = False,
        approval_count: int = 1,
        notify_roles: list[str] | None = None,
        notify_author: bool = True,
    ) -> dict:
        """Create a new workflow transition."""
        # Verify states exist
        from_state = await self.db.get(WorkflowState, from_state_id)
        to_state = await self.db.get(WorkflowState, to_state_id)

        if not from_state or not to_state:
            raise ValueError("Invalid state IDs")

        # Check for existing transition
        existing = await self.db.execute(
            select(WorkflowTransition).where(
                WorkflowTransition.from_state_id == from_state_id,
                WorkflowTransition.to_state_id == to_state_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Transition between these states already exists")

        transition = WorkflowTransition(
            name=name,
            from_state_id=from_state_id,
            to_state_id=to_state_id,
            required_roles=",".join(required_roles) if required_roles else None,
            requires_approval=requires_approval,
            approval_count=approval_count,
            notify_roles=",".join(notify_roles) if notify_roles else None,
            notify_author=notify_author,
        )

        self.db.add(transition)
        await self.db.commit()
        await self.db.refresh(transition)

        logger.info(f"Created workflow transition: {name}")

        return {
            "id": transition.id,
            "name": transition.name,
            "from_state_id": from_state_id,
            "to_state_id": to_state_id,
        }

    # ============== Content Workflow Operations ==============

    async def get_available_transitions(
        self,
        content_id: int,
        user: User,
    ) -> list[dict]:
        """Get available transitions for content based on current state and user role."""
        content = await self.db.get(Content, content_id)
        if not content:
            raise ValueError("Content not found")

        # Get current state
        current_state = await self._get_content_state(content)
        if not current_state:
            return []

        # Get transitions from current state
        transitions = await self.get_transitions(from_state_id=current_state.id)

        # Filter by user role
        user_role = user.role.name if user.role else "user"
        available = []

        for t in transitions:
            required_roles = t.get("required_roles", [])
            if not required_roles or user_role in required_roles or user_role == "superadmin":
                # Check if approval is pending
                if t.get("requires_approval"):
                    approval_status = await self._get_approval_status(content_id, t["id"])
                    t["approval_status"] = approval_status
                available.append(t)

        return available

    async def execute_transition(
        self,
        content_id: int,
        transition_id: int,
        user: User,
        comment: str | None = None,
    ) -> dict:
        """Execute a workflow transition for content."""
        content = await self.db.get(Content, content_id)
        if not content:
            raise ValueError("Content not found")

        transition = await self.db.get(WorkflowTransition, transition_id)
        if not transition:
            raise ValueError("Transition not found")

        # Verify current state matches transition's from_state
        current_state = await self._get_content_state(content)
        if not current_state or current_state.id != transition.from_state_id:
            raise ValueError("Content is not in the correct state for this transition")

        # Check user permission
        user_role = user.role.name if user.role else "user"
        required_roles = transition.get_required_roles()
        if required_roles and user_role not in required_roles and user_role != "superadmin":
            raise ValueError("You don't have permission for this transition")

        # Handle approval workflow
        if transition.requires_approval:
            return await self._handle_approval_transition(content, transition, user, comment)

        # Execute immediate transition
        return await self._execute_immediate_transition(content, transition, user, comment)

    async def _handle_approval_transition(
        self,
        content: Content,
        transition: WorkflowTransition,
        user: User,
        comment: str | None,
    ) -> dict:
        """Handle a transition that requires approval."""
        # Check existing approvals
        result = await self.db.execute(
            select(WorkflowApproval).where(
                WorkflowApproval.content_id == content.id,
                WorkflowApproval.transition_id == transition.id,
                WorkflowApproval.approved.is_(True),
            )
        )
        approvals = result.scalars().all()

        # Check if user already approved
        user_approval = next((a for a in approvals if a.approver_id == user.id), None)
        if user_approval:
            raise ValueError("You have already approved this transition")

        # Add approval
        approval = WorkflowApproval(
            content_id=content.id,
            transition_id=transition.id,
            approver_id=user.id,
            approved=True,
            comment=comment,
            decided_at=datetime.now(timezone.utc),
        )
        self.db.add(approval)
        await self.db.commit()

        # Check if we have enough approvals
        total_approvals = len(approvals) + 1
        if total_approvals >= transition.approval_count:
            # Execute the transition
            return await self._execute_immediate_transition(content, transition, user, comment)

        return {
            "status": "pending_approval",
            "approvals_received": total_approvals,
            "approvals_required": transition.approval_count,
            "message": f"Approval recorded. {transition.approval_count - total_approvals} more approval(s) needed.",
        }

    async def _execute_immediate_transition(
        self,
        content: Content,
        transition: WorkflowTransition,
        user: User,
        comment: str | None,
    ) -> dict:
        """Execute a transition immediately."""
        from_state = await self.db.get(WorkflowState, transition.from_state_id)
        to_state = await self.db.get(WorkflowState, transition.to_state_id)

        # Update content status based on state
        content.status = to_state.name

        # If final state is "published", update published_at
        if to_state.is_final and to_state.name == "published":
            content.published_at = datetime.now(timezone.utc)

        # Record history
        history = WorkflowHistory(
            content_id=content.id,
            from_state_id=from_state.id if from_state else None,
            to_state_id=to_state.id,
            user_id=user.id,
            transition_name=transition.name,
            comment=comment,
        )
        self.db.add(history)

        # Clear any pending approvals for this content/transition
        await self.db.execute(
            select(WorkflowApproval).where(
                WorkflowApproval.content_id == content.id,
                WorkflowApproval.transition_id == transition.id,
                WorkflowApproval.approved.is_(None),
            )
        )

        await self.db.commit()

        logger.info(f"Executed transition '{transition.name}' for content {content.id}")

        return {
            "status": "completed",
            "from_state": from_state.name if from_state else None,
            "to_state": to_state.name,
            "transition": transition.name,
            "message": f"Content transitioned to '{to_state.display_name}'",
        }

    async def get_content_history(self, content_id: int) -> list[dict]:
        """Get workflow history for content."""
        result = await self.db.execute(
            select(WorkflowHistory)
            .options(
                selectinload(WorkflowHistory.from_state),
                selectinload(WorkflowHistory.to_state),
                selectinload(WorkflowHistory.user),
            )
            .where(WorkflowHistory.content_id == content_id)
            .order_by(WorkflowHistory.created_at.desc())
        )
        history = result.scalars().all()

        return [
            {
                "id": h.id,
                "from_state": h.from_state.display_name if h.from_state else None,
                "to_state": h.to_state.display_name if h.to_state else None,
                "transition": h.transition_name,
                "user": h.user.username if h.user else None,
                "comment": h.comment,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ]

    async def get_pending_approvals(self, user_id: int | None = None) -> list[dict]:
        """Get pending approvals, optionally filtered by approver."""
        query = (
            select(WorkflowApproval)
            .options(
                selectinload(WorkflowApproval.content),
                selectinload(WorkflowApproval.transition),
            )
            .where(WorkflowApproval.approved.is_(None))
        )

        if user_id:
            query = query.where(WorkflowApproval.approver_id == user_id)

        result = await self.db.execute(query.order_by(WorkflowApproval.created_at.desc()))
        approvals = result.scalars().all()

        return [
            {
                "id": a.id,
                "content_id": a.content_id,
                "content_title": a.content.title if a.content else None,
                "transition": a.transition.name if a.transition else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in approvals
        ]

    async def approve_or_reject(
        self,
        approval_id: int,
        user: User,
        approved: bool,
        comment: str | None = None,
    ) -> dict:
        """Approve or reject a pending approval."""
        approval = await self.db.get(WorkflowApproval, approval_id)
        if not approval:
            raise ValueError("Approval not found")

        if approval.approved is not None:
            raise ValueError("This approval has already been decided")

        if approval.approver_id != user.id:
            raise ValueError("You are not the designated approver")

        approval.approved = approved
        approval.comment = comment
        approval.decided_at = datetime.now(timezone.utc)

        await self.db.commit()

        if approved:
            # Check if this was the last required approval
            transition = await self.db.get(WorkflowTransition, approval.transition_id)
            content = await self.db.get(Content, approval.content_id)

            if transition and content:
                result = await self.db.execute(
                    select(WorkflowApproval).where(
                        WorkflowApproval.content_id == approval.content_id,
                        WorkflowApproval.transition_id == approval.transition_id,
                        WorkflowApproval.approved.is_(True),
                    )
                )
                total_approvals = len(result.scalars().all())

                if total_approvals >= transition.approval_count:
                    return await self._execute_immediate_transition(content, transition, user, comment)

        return {
            "status": "approved" if approved else "rejected",
            "message": f"Approval {'accepted' if approved else 'rejected'}",
        }

    # ============== Private Methods ==============

    async def _get_content_state(self, content: Content) -> WorkflowState | None:
        """Get the workflow state for content."""
        return await self.get_state_by_name(content.status, WorkflowType.CONTENT)

    async def _get_approval_status(self, content_id: int, transition_id: int) -> dict:
        """Get approval status for a content/transition."""
        result = await self.db.execute(
            select(WorkflowApproval).where(
                WorkflowApproval.content_id == content_id,
                WorkflowApproval.transition_id == transition_id,
            )
        )
        approvals = result.scalars().all()

        return {
            "approved": len([a for a in approvals if a.approved is True]),
            "rejected": len([a for a in approvals if a.approved is False]),
            "pending": len([a for a in approvals if a.approved is None]),
        }


async def get_workflow_service(db: AsyncSession) -> WorkflowService:
    """FastAPI dependency for WorkflowService."""
    return WorkflowService(db)


# ============== Default Workflow Setup ==============


async def setup_default_content_workflow(db: AsyncSession) -> None:
    """Set up default content workflow states and transitions."""
    service = WorkflowService(db)

    # Default states
    states_config = [
        {"name": "draft", "display_name": "Draft", "is_initial": True, "color": "#6B7280", "order": 1},
        {"name": "review", "display_name": "Under Review", "color": "#F59E0B", "order": 2},
        {"name": "approved", "display_name": "Approved", "color": "#10B981", "order": 3},
        {"name": "published", "display_name": "Published", "is_final": True, "color": "#3B82F6", "order": 4},
        {"name": "archived", "display_name": "Archived", "is_final": True, "color": "#9CA3AF", "order": 5},
    ]

    created_states = {}
    for config in states_config:
        try:
            state = await service.create_state(**config)
            created_states[config["name"]] = state["id"]
        except ValueError:
            # State already exists
            existing = await service.get_state_by_name(config["name"])
            if existing:
                created_states[config["name"]] = existing.id

    # Default transitions
    transitions_config = [
        {"name": "Submit for Review", "from": "draft", "to": "review"},
        {"name": "Approve", "from": "review", "to": "approved", "required_roles": ["admin", "editor"]},
        {"name": "Request Changes", "from": "review", "to": "draft"},
        {"name": "Publish", "from": "approved", "to": "published", "required_roles": ["admin"]},
        {"name": "Unpublish", "from": "published", "to": "draft"},
        {"name": "Archive", "from": "published", "to": "archived"},
    ]

    for config in transitions_config:
        with contextlib.suppress(ValueError):
            await service.create_transition(
                name=config["name"],
                from_state_id=created_states.get(config["from"]),
                to_state_id=created_states.get(config["to"]),
                required_roles=config.get("required_roles"),
            )

    logger.info("Default content workflow setup complete")
