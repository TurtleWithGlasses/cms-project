"""Team management service for collaborative features."""

import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import (
    InvitationStatus,
    Team,
    TeamInvitation,
    TeamMember,
    TeamRole,
)
from app.models.user import User


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from name."""
    import re

    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


async def create_team(
    db: AsyncSession,
    name: str,
    created_by_id: int,
    description: str | None = None,
    parent_team_id: int | None = None,
) -> Team:
    """Create a new team and add creator as owner."""
    # Generate unique slug
    base_slug = generate_slug(name)
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(Team).where(Team.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    team = Team(
        name=name,
        slug=slug,
        description=description,
        parent_team_id=parent_team_id,
        created_by_id=created_by_id,
    )
    db.add(team)
    await db.flush()

    # Add creator as owner
    member = TeamMember(
        team_id=team.id,
        user_id=created_by_id,
        role=TeamRole.OWNER,
    )
    db.add(member)
    await db.commit()
    await db.refresh(team)

    return team


async def get_team(db: AsyncSession, team_id: int) -> Team | None:
    """Get team by ID with members loaded."""
    result = await db.execute(
        select(Team).options(selectinload(Team.members).selectinload(TeamMember.user)).where(Team.id == team_id)
    )
    return result.scalar_one_or_none()


async def get_team_by_slug(db: AsyncSession, slug: str) -> Team | None:
    """Get team by slug."""
    result = await db.execute(
        select(Team).options(selectinload(Team.members).selectinload(TeamMember.user)).where(Team.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_user_teams(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[Team]:
    """Get all teams a user belongs to."""
    result = await db.execute(
        select(Team)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user_id)
        .where(Team.is_active.is_(True))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_team(
    db: AsyncSession,
    team_id: int,
    user_id: int,
    **kwargs,
) -> Team:
    """Update team details. Only owners/admins can update."""
    team = await get_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check permission
    member = await get_team_member(db, team_id, user_id)
    if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update team",
        )

    for key, value in kwargs.items():
        if hasattr(team, key) and value is not None:
            setattr(team, key, value)

    await db.commit()
    await db.refresh(team)
    return team


async def delete_team(db: AsyncSession, team_id: int, user_id: int) -> bool:
    """Delete a team. Only owners can delete."""
    team = await get_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    member = await get_team_member(db, team_id, user_id)
    if not member or member.role != TeamRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners can delete the team",
        )

    await db.delete(team)
    await db.commit()
    return True


async def get_team_member(db: AsyncSession, team_id: int, user_id: int) -> TeamMember | None:
    """Get a specific team member."""
    result = await db.execute(
        select(TeamMember)
        .options(selectinload(TeamMember.user))
        .where(TeamMember.team_id == team_id)
        .where(TeamMember.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_team_members(
    db: AsyncSession,
    team_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[TeamMember]:
    """Get all members of a team."""
    result = await db.execute(
        select(TeamMember)
        .options(selectinload(TeamMember.user))
        .where(TeamMember.team_id == team_id)
        .order_by(TeamMember.joined_at)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def add_team_member(
    db: AsyncSession,
    team_id: int,
    user_id: int,
    role: TeamRole = TeamRole.MEMBER,
    added_by_id: int | None = None,
) -> TeamMember:
    """Add a user to a team."""
    # Check if already a member
    existing = await get_team_member(db, team_id, user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a team member",
        )

    # Check permission if added_by_id provided
    if added_by_id:
        adder = await get_team_member(db, team_id, added_by_id)
        if not adder or adder.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to add members",
            )

    member = TeamMember(
        team_id=team_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_member_role(
    db: AsyncSession,
    team_id: int,
    user_id: int,
    new_role: TeamRole,
    updated_by_id: int,
) -> TeamMember:
    """Update a team member's role."""
    # Check updater permission
    updater = await get_team_member(db, team_id, updated_by_id)
    if not updater or updater.role != TeamRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners can change member roles",
        )

    member = await get_team_member(db, team_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found",
        )

    # Cannot demote the last owner
    if member.role == TeamRole.OWNER and new_role != TeamRole.OWNER:
        owner_count = await db.execute(
            select(func.count(TeamMember.id))
            .where(TeamMember.team_id == team_id)
            .where(TeamMember.role == TeamRole.OWNER)
        )
        if owner_count.scalar() <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last owner",
            )

    member.role = new_role
    await db.commit()
    await db.refresh(member)
    return member


async def remove_team_member(
    db: AsyncSession,
    team_id: int,
    user_id: int,
    removed_by_id: int,
) -> bool:
    """Remove a user from a team."""
    # Check permission (owners/admins can remove, or self-removal)
    if user_id != removed_by_id:
        remover = await get_team_member(db, team_id, removed_by_id)
        if not remover or remover.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to remove members",
            )

    member = await get_team_member(db, team_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found",
        )

    # Cannot remove last owner
    if member.role == TeamRole.OWNER:
        owner_count = await db.execute(
            select(func.count(TeamMember.id))
            .where(TeamMember.team_id == team_id)
            .where(TeamMember.role == TeamRole.OWNER)
        )
        if owner_count.scalar() <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner",
            )

    await db.delete(member)
    await db.commit()
    return True


async def create_invitation(
    db: AsyncSession,
    team_id: int,
    email: str,
    invited_by_id: int,
    role: TeamRole = TeamRole.MEMBER,
    message: str | None = None,
    expires_in_days: int = 7,
) -> TeamInvitation:
    """Create a team invitation."""
    # Check inviter permission
    team = await get_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    inviter = await get_team_member(db, team_id, invited_by_id)
    can_invite = inviter and inviter.role in [TeamRole.OWNER, TeamRole.ADMIN] or (team.allow_member_invite and inviter)

    if not can_invite:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to invite members",
        )

    # Check for existing pending invitation
    result = await db.execute(
        select(TeamInvitation)
        .where(TeamInvitation.team_id == team_id)
        .where(TeamInvitation.email == email)
        .where(TeamInvitation.status == InvitationStatus.PENDING)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending invitation already exists for this email",
        )

    # Check if user exists and is already a member
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        existing_member = await get_team_member(db, team_id, user.id)
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a team member",
            )

    invitation = TeamInvitation(
        team_id=team_id,
        email=email,
        user_id=user.id if user else None,
        role=role,
        token=secrets.token_urlsafe(32),
        message=message,
        invited_by_id=invited_by_id,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def get_invitation_by_token(db: AsyncSession, token: str) -> TeamInvitation | None:
    """Get an invitation by its token."""
    result = await db.execute(
        select(TeamInvitation).options(selectinload(TeamInvitation.team)).where(TeamInvitation.token == token)
    )
    return result.scalar_one_or_none()


async def accept_invitation(
    db: AsyncSession,
    token: str,
    user_id: int,
) -> TeamMember:
    """Accept a team invitation."""
    invitation = await get_invitation_by_token(db, token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation already {invitation.status.value}",
        )

    if invitation.expires_at < datetime.utcnow():
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Verify email matches
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.email.lower() != invitation.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation email does not match your account",
        )

    # Add to team
    member = await add_team_member(db, invitation.team_id, user_id, invitation.role)

    # Update invitation status
    invitation.status = InvitationStatus.ACCEPTED
    invitation.responded_at = datetime.utcnow()
    await db.commit()

    return member


async def decline_invitation(db: AsyncSession, token: str, user_id: int) -> bool:
    """Decline a team invitation."""
    invitation = await get_invitation_by_token(db, token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation already {invitation.status.value}",
        )

    invitation.status = InvitationStatus.DECLINED
    invitation.responded_at = datetime.utcnow()
    await db.commit()
    return True


async def get_pending_invitations(
    db: AsyncSession,
    team_id: int,
) -> list[TeamInvitation]:
    """Get all pending invitations for a team."""
    result = await db.execute(
        select(TeamInvitation)
        .where(TeamInvitation.team_id == team_id)
        .where(TeamInvitation.status == InvitationStatus.PENDING)
        .order_by(TeamInvitation.created_at.desc())
    )
    return list(result.scalars().all())


async def cancel_invitation(
    db: AsyncSession,
    invitation_id: int,
    cancelled_by_id: int,
) -> bool:
    """Cancel a pending invitation."""
    result = await db.execute(
        select(TeamInvitation).options(selectinload(TeamInvitation.team)).where(TeamInvitation.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check permission
    canceller = await get_team_member(db, invitation.team_id, cancelled_by_id)
    if not canceller or canceller.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to cancel invitation",
        )

    await db.delete(invitation)
    await db.commit()
    return True
