"""
Workflow Models

Provides content workflow management with custom states and transitions.
Supports approval chains and conditional workflows.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class WorkflowType(str, enum.Enum):
    """Types of workflows."""

    CONTENT = "content"  # Content publishing workflow
    COMMENT = "comment"  # Comment moderation workflow
    USER = "user"  # User approval workflow
    CUSTOM = "custom"  # Custom workflow


class WorkflowState(Base):
    """
    Workflow state model.

    Defines the possible states in a workflow.
    """

    __tablename__ = "workflow_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # State identification
    name = Column(String(50), nullable=False)  # e.g., "draft", "review", "approved"
    display_name = Column(String(100), nullable=False)  # e.g., "Draft", "Under Review"
    description = Column(Text, nullable=True)

    # Workflow association
    workflow_type = Column(Enum(WorkflowType), default=WorkflowType.CONTENT, nullable=False)

    # State properties
    is_initial = Column(Boolean, default=False, nullable=False)  # Starting state
    is_final = Column(Boolean, default=False, nullable=False)  # Terminal state (e.g., published)
    is_active = Column(Boolean, default=True, nullable=False)

    # Display order
    order = Column(Integer, default=0, nullable=False)

    # Color for UI (hex code)
    color = Column(String(7), default="#6B7280", nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    outgoing_transitions = relationship(
        "WorkflowTransition",
        foreign_keys="WorkflowTransition.from_state_id",
        back_populates="from_state",
        cascade="all, delete-orphan",
    )
    incoming_transitions = relationship(
        "WorkflowTransition",
        foreign_keys="WorkflowTransition.to_state_id",
        back_populates="to_state",
    )

    # Indexes
    __table_args__ = (
        Index("ix_workflow_states_type_name", "workflow_type", "name", unique=True),
        Index("ix_workflow_states_initial", "workflow_type", "is_initial"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowState(id={self.id}, name={self.name}, type={self.workflow_type})>"


class WorkflowTransition(Base):
    """
    Workflow transition model.

    Defines allowed transitions between states.
    """

    __tablename__ = "workflow_transitions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Transition name
    name = Column(String(100), nullable=False)  # e.g., "Submit for Review"

    # State connections
    from_state_id = Column(
        Integer,
        ForeignKey("workflow_states.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_state_id = Column(
        Integer,
        ForeignKey("workflow_states.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Permission requirements (comma-separated roles)
    required_roles = Column(Text, nullable=True)  # e.g., "admin,editor"

    # Approval requirements
    requires_approval = Column(Boolean, default=False, nullable=False)
    approval_count = Column(Integer, default=1, nullable=False)  # How many approvals needed

    # Notification settings
    notify_roles = Column(Text, nullable=True)  # Roles to notify on transition
    notify_author = Column(Boolean, default=True, nullable=False)

    # Conditions (JSON string for complex conditions)
    conditions = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    from_state = relationship("WorkflowState", foreign_keys=[from_state_id], back_populates="outgoing_transitions")
    to_state = relationship("WorkflowState", foreign_keys=[to_state_id], back_populates="incoming_transitions")

    # Indexes
    __table_args__ = (Index("ix_workflow_transitions_states", "from_state_id", "to_state_id", unique=True),)

    def __repr__(self) -> str:
        return f"<WorkflowTransition(id={self.id}, name={self.name})>"

    def get_required_roles(self) -> list[str]:
        """Get list of required roles."""
        if not self.required_roles:
            return []
        return [r.strip() for r in self.required_roles.split(",")]

    def get_notify_roles(self) -> list[str]:
        """Get list of roles to notify."""
        if not self.notify_roles:
            return []
        return [r.strip() for r in self.notify_roles.split(",")]


class WorkflowApproval(Base):
    """
    Workflow approval tracking.

    Tracks approvals for transitions that require multiple approvers.
    """

    __tablename__ = "workflow_approvals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Content reference
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transition being approved
    transition_id = Column(
        Integer,
        ForeignKey("workflow_transitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Approver
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Approval status
    approved = Column(Boolean, nullable=True)  # None = pending, True = approved, False = rejected
    comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at = Column(DateTime, nullable=True)

    # Relationships
    content = relationship("Content", backref="workflow_approvals")
    transition = relationship("WorkflowTransition")
    approver = relationship("User")

    # Indexes
    __table_args__ = (
        Index("ix_workflow_approvals_content_transition", "content_id", "transition_id"),
        Index("ix_workflow_approvals_pending", "approved"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowApproval(id={self.id}, content={self.content_id}, approved={self.approved})>"


class WorkflowHistory(Base):
    """
    Workflow history tracking.

    Logs all state transitions for audit purposes.
    """

    __tablename__ = "workflow_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Content reference
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transition details
    from_state_id = Column(Integer, ForeignKey("workflow_states.id", ondelete="SET NULL"), nullable=True)
    to_state_id = Column(Integer, ForeignKey("workflow_states.id", ondelete="SET NULL"), nullable=False)

    # Who made the transition
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Transition info
    transition_name = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    content = relationship("Content", backref="workflow_history")
    from_state = relationship("WorkflowState", foreign_keys=[from_state_id])
    to_state = relationship("WorkflowState", foreign_keys=[to_state_id])
    user = relationship("User")

    # Indexes
    __table_args__ = (Index("ix_workflow_history_content_created", "content_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<WorkflowHistory(id={self.id}, content={self.content_id})>"
