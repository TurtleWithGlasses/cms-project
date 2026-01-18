"""Team management routes for collaborative features."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.team import TeamRole
from app.models.user import User
from app.routes.auth import get_current_user
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["Teams"])


# Pydantic schemas
class TeamCreate(BaseModel):
    """Schema for creating a team."""

    name: str
    description: str | None = None
    parent_team_id: int | None = None


class TeamUpdate(BaseModel):
    """Schema for updating a team."""

    name: str | None = None
    description: str | None = None
    avatar_url: str | None = None
    allow_member_invite: bool | None = None
    default_member_role: TeamRole | None = None


class TeamResponse(BaseModel):
    """Schema for team response."""

    id: int
    name: str
    slug: str
    description: str | None
    avatar_url: str | None
    is_active: bool
    allow_member_invite: bool
    default_member_role: TeamRole
    member_count: int | None = None

    model_config = {"from_attributes": True}


class TeamMemberResponse(BaseModel):
    """Schema for team member response."""

    id: int
    user_id: int
    username: str | None = None
    email: str | None = None
    role: TeamRole
    joined_at: str

    model_config = {"from_attributes": True}


class InvitationCreate(BaseModel):
    """Schema for creating an invitation."""

    email: EmailStr
    role: TeamRole = TeamRole.MEMBER
    message: str | None = None


class InvitationResponse(BaseModel):
    """Schema for invitation response."""

    id: int
    team_id: int
    email: str
    role: TeamRole
    status: str
    token: str
    created_at: str
    expires_at: str

    model_config = {"from_attributes": True}


class MemberRoleUpdate(BaseModel):
    """Schema for updating member role."""

    role: TeamRole


# Routes
@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new team."""
    team = await team_service.create_team(
        db=db,
        name=team_data.name,
        created_by_id=current_user.id,
        description=team_data.description,
        parent_team_id=team_data.parent_team_id,
    )
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        avatar_url=team.avatar_url,
        is_active=team.is_active,
        allow_member_invite=team.allow_member_invite,
        default_member_role=team.default_member_role,
        member_count=1,
    )


@router.get("", response_model=list[TeamResponse])
async def get_my_teams(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all teams the current user belongs to."""
    teams = await team_service.get_user_teams(db, current_user.id, skip, limit)
    return [
        TeamResponse(
            id=t.id,
            name=t.name,
            slug=t.slug,
            description=t.description,
            avatar_url=t.avatar_url,
            is_active=t.is_active,
            allow_member_invite=t.allow_member_invite,
            default_member_role=t.default_member_role,
        )
        for t in teams
    ]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get team details."""
    team = await team_service.get_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check if user is a member
    member = await team_service.get_team_member(db, team_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team",
        )

    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        avatar_url=team.avatar_url,
        is_active=team.is_active,
        allow_member_invite=team.allow_member_invite,
        default_member_role=team.default_member_role,
        member_count=len(team.members),
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update team details. Requires owner or admin role."""
    team = await team_service.update_team(
        db=db,
        team_id=team_id,
        user_id=current_user.id,
        **team_data.model_dump(exclude_unset=True),
    )
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        avatar_url=team.avatar_url,
        is_active=team.is_active,
        allow_member_invite=team.allow_member_invite,
        default_member_role=team.default_member_role,
    )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a team. Only owners can delete."""
    await team_service.delete_team(db, team_id, current_user.id)


# Members
@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def get_team_members(
    team_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all members of a team."""
    # Verify user is a member
    member = await team_service.get_team_member(db, team_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team",
        )

    members = await team_service.get_team_members(db, team_id, skip, limit)
    return [
        TeamMemberResponse(
            id=m.id,
            user_id=m.user_id,
            username=m.user.username if m.user else None,
            email=m.user.email if m.user else None,
            role=m.role,
            joined_at=m.joined_at.isoformat(),
        )
        for m in members
    ]


@router.put("/{team_id}/members/{user_id}/role", response_model=TeamMemberResponse)
async def update_member_role(
    team_id: int,
    user_id: int,
    role_data: MemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's role. Only owners can change roles."""
    member = await team_service.update_member_role(
        db=db,
        team_id=team_id,
        user_id=user_id,
        new_role=role_data.role,
        updated_by_id=current_user.id,
    )
    return TeamMemberResponse(
        id=member.id,
        user_id=member.user_id,
        username=member.user.username if member.user else None,
        email=member.user.email if member.user else None,
        role=member.role,
        joined_at=member.joined_at.isoformat(),
    )


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the team."""
    await team_service.remove_team_member(db, team_id, user_id, current_user.id)


@router.post("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leave a team."""
    await team_service.remove_team_member(db, team_id, current_user.id, current_user.id)


# Invitations
@router.post(
    "/{team_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    team_id: int,
    invitation_data: InvitationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an invitation to join the team."""
    invitation = await team_service.create_invitation(
        db=db,
        team_id=team_id,
        email=invitation_data.email,
        invited_by_id=current_user.id,
        role=invitation_data.role,
        message=invitation_data.message,
    )
    return InvitationResponse(
        id=invitation.id,
        team_id=invitation.team_id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status.value,
        token=invitation.token,
        created_at=invitation.created_at.isoformat(),
        expires_at=invitation.expires_at.isoformat(),
    )


@router.get("/{team_id}/invitations", response_model=list[InvitationResponse])
async def get_pending_invitations(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all pending invitations for a team."""
    # Verify user is an admin or owner
    member = await team_service.get_team_member(db, team_id, current_user.id)
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view invitations",
        )

    invitations = await team_service.get_pending_invitations(db, team_id)
    return [
        InvitationResponse(
            id=inv.id,
            team_id=inv.team_id,
            email=inv.email,
            role=inv.role,
            status=inv.status.value,
            token=inv.token,
            created_at=inv.created_at.isoformat(),
            expires_at=inv.expires_at.isoformat(),
        )
        for inv in invitations
    ]


@router.delete("/{team_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    team_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending invitation."""
    await team_service.cancel_invitation(db, invitation_id, current_user.id)


# Public invitation endpoints
@router.post("/invitations/{token}/accept", response_model=TeamMemberResponse)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a team invitation."""
    member = await team_service.accept_invitation(db, token, current_user.id)
    return TeamMemberResponse(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at.isoformat(),
    )


@router.post("/invitations/{token}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Decline a team invitation."""
    await team_service.decline_invitation(db, token, current_user.id)
