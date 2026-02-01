"""
Workflow Routes

API endpoints for content workflow management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.workflow import WorkflowType
from app.services.workflow_service import WorkflowService

router = APIRouter(tags=["Workflow"])


# ============== Schemas ==============


class WorkflowStateCreate(BaseModel):
    """Request to create a workflow state."""

    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    workflow_type: str = Field("content")
    is_initial: bool = False
    is_final: bool = False
    color: str = Field("#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    order: int = Field(0, ge=0)


class WorkflowStateResponse(BaseModel):
    """Response for a workflow state."""

    id: int
    name: str
    display_name: str
    description: str | None
    is_initial: bool
    is_final: bool
    color: str
    order: int


class WorkflowTransitionCreate(BaseModel):
    """Request to create a workflow transition."""

    name: str = Field(..., min_length=1, max_length=100)
    from_state_id: int
    to_state_id: int
    required_roles: list[str] | None = None
    requires_approval: bool = False
    approval_count: int = Field(1, ge=1, le=10)
    notify_roles: list[str] | None = None
    notify_author: bool = True


class WorkflowTransitionResponse(BaseModel):
    """Response for a workflow transition."""

    id: int
    name: str
    from_state: dict
    to_state: dict
    requires_approval: bool
    approval_count: int
    required_roles: list[str]


class ExecuteTransitionRequest(BaseModel):
    """Request to execute a transition."""

    transition_id: int
    comment: str | None = None


class ApprovalDecision(BaseModel):
    """Request to approve or reject."""

    approved: bool
    comment: str | None = None


class WorkflowHistoryResponse(BaseModel):
    """Response for workflow history entry."""

    id: int
    from_state: str | None
    to_state: str | None
    transition: str | None
    user: str | None
    comment: str | None
    created_at: str


# ============== State Management ==============


@router.get("/states", response_model=list[WorkflowStateResponse])
async def list_workflow_states(
    workflow_type: str = "content",
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowStateResponse]:
    """
    List all workflow states for a given workflow type.
    """
    try:
        wf_type = WorkflowType(workflow_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow type: {workflow_type}",
        ) from e

    service = WorkflowService(db)
    states = await service.get_states(wf_type)
    return [WorkflowStateResponse(**s) for s in states]


@router.post("/states", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_workflow_state(
    data: WorkflowStateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a new workflow state.

    Requires admin privileges.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    try:
        wf_type = WorkflowType(data.workflow_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow type: {data.workflow_type}",
        ) from e

    service = WorkflowService(db)

    try:
        result = await service.create_state(
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            workflow_type=wf_type,
            is_initial=data.is_initial,
            is_final=data.is_final,
            color=data.color,
            order=data.order,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Transition Management ==============


@router.get("/transitions", response_model=list[WorkflowTransitionResponse])
async def list_workflow_transitions(
    workflow_type: str = "content",
    from_state_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowTransitionResponse]:
    """
    List all workflow transitions.

    Optionally filter by from_state_id.
    """
    try:
        wf_type = WorkflowType(workflow_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow type: {workflow_type}",
        ) from e

    service = WorkflowService(db)
    transitions = await service.get_transitions(from_state_id=from_state_id, workflow_type=wf_type)
    return [WorkflowTransitionResponse(**t) for t in transitions]


@router.post("/transitions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_workflow_transition(
    data: WorkflowTransitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a new workflow transition.

    Requires admin privileges.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    service = WorkflowService(db)

    try:
        result = await service.create_transition(
            name=data.name,
            from_state_id=data.from_state_id,
            to_state_id=data.to_state_id,
            required_roles=data.required_roles,
            requires_approval=data.requires_approval,
            approval_count=data.approval_count,
            notify_roles=data.notify_roles,
            notify_author=data.notify_author,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Content Workflow Operations ==============


@router.get("/content/{content_id}/transitions", response_model=list[WorkflowTransitionResponse])
async def get_available_transitions(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkflowTransitionResponse]:
    """
    Get available transitions for a specific content item.

    Returns transitions based on current state and user permissions.
    """
    service = WorkflowService(db)

    try:
        transitions = await service.get_available_transitions(content_id, current_user)
        return [WorkflowTransitionResponse(**t) for t in transitions]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/content/{content_id}/transition")
async def execute_transition(
    content_id: int,
    data: ExecuteTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Execute a workflow transition for content.

    If the transition requires approval, this may add an approval vote
    instead of immediately transitioning the content.
    """
    service = WorkflowService(db)

    try:
        result = await service.execute_transition(
            content_id=content_id,
            transition_id=data.transition_id,
            user=current_user,
            comment=data.comment,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/content/{content_id}/history", response_model=list[WorkflowHistoryResponse])
async def get_content_workflow_history(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkflowHistoryResponse]:
    """
    Get workflow history for a content item.
    """
    service = WorkflowService(db)
    history = await service.get_content_history(content_id)
    return [WorkflowHistoryResponse(**h) for h in history]


# ============== Approval Management ==============


@router.get("/approvals/pending")
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Get pending approvals for the current user.
    """
    service = WorkflowService(db)
    approvals = await service.get_pending_approvals(user_id=current_user.id)
    return approvals


@router.get("/approvals/all")
async def get_all_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Get all pending approvals (admin only).
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    service = WorkflowService(db)
    approvals = await service.get_pending_approvals()
    return approvals


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: int,
    data: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Approve or reject a pending approval.
    """
    service = WorkflowService(db)

    try:
        result = await service.approve_or_reject(
            approval_id=approval_id,
            user=current_user,
            approved=data.approved,
            comment=data.comment,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
