"""Add workflow and notifications tables

Revision ID: f7g8h9i0j1k2
Revises: e6f7g8h9i0j1
Create Date: 2024-01-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7g8h9i0j1k2"
down_revision: str | None = "e6f7g8h9i0j1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create workflow_states table
    op.create_table(
        "workflow_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "workflow_type",
            sa.Enum("CONTENT", "COMMENT", "USER", "CUSTOM", name="workflowtype"),
            nullable=False,
            server_default="CONTENT",
        ),
        sa.Column("is_initial", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color", sa.String(length=7), nullable=False, server_default="#6B7280"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_states_id", "workflow_states", ["id"], unique=False)
    op.create_index("ix_workflow_states_type_name", "workflow_states", ["workflow_type", "name"], unique=True)
    op.create_index("ix_workflow_states_initial", "workflow_states", ["workflow_type", "is_initial"], unique=False)

    # Create workflow_transitions table
    op.create_table(
        "workflow_transitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("from_state_id", sa.Integer(), nullable=False),
        sa.Column("to_state_id", sa.Integer(), nullable=False),
        sa.Column("required_roles", sa.Text(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("approval_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notify_roles", sa.Text(), nullable=True),
        sa.Column("notify_author", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["from_state_id"], ["workflow_states.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_state_id"], ["workflow_states.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_transitions_id", "workflow_transitions", ["id"], unique=False)
    op.create_index("ix_workflow_transitions_from", "workflow_transitions", ["from_state_id"], unique=False)
    op.create_index("ix_workflow_transitions_to", "workflow_transitions", ["to_state_id"], unique=False)
    op.create_index(
        "ix_workflow_transitions_states", "workflow_transitions", ["from_state_id", "to_state_id"], unique=True
    )

    # Create workflow_approvals table
    op.create_table(
        "workflow_approvals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("transition_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transition_id"], ["workflow_transitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_approvals_id", "workflow_approvals", ["id"], unique=False)
    op.create_index("ix_workflow_approvals_content_id", "workflow_approvals", ["content_id"], unique=False)
    op.create_index("ix_workflow_approvals_transition_id", "workflow_approvals", ["transition_id"], unique=False)
    op.create_index("ix_workflow_approvals_approver_id", "workflow_approvals", ["approver_id"], unique=False)
    op.create_index(
        "ix_workflow_approvals_content_transition",
        "workflow_approvals",
        ["content_id", "transition_id"],
        unique=False,
    )
    op.create_index("ix_workflow_approvals_pending", "workflow_approvals", ["approved"], unique=False)

    # Create workflow_history table
    op.create_table(
        "workflow_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("from_state_id", sa.Integer(), nullable=True),
        sa.Column("to_state_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("transition_name", sa.String(length=100), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_state_id"], ["workflow_states.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_state_id"], ["workflow_states.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_history_id", "workflow_history", ["id"], unique=False)
    op.create_index("ix_workflow_history_content_id", "workflow_history", ["content_id"], unique=False)
    op.create_index("ix_workflow_history_user_id", "workflow_history", ["user_id"], unique=False)
    op.create_index(
        "ix_workflow_history_content_created", "workflow_history", ["content_id", "created_at"], unique=False
    )

    # Create notification_templates table
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "CONTENT",
                "COMMENTS",
                "WORKFLOW",
                "SECURITY",
                "SYSTEM",
                "MENTIONS",
                "DIGEST",
                name="notificationcategory",
            ),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("push_title", sa.String(length=100), nullable=True),
        sa.Column("push_body", sa.String(length=255), nullable=True),
        sa.Column("variables", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_templates_id", "notification_templates", ["id"], unique=False)
    op.create_index("ix_notification_templates_name", "notification_templates", ["name"], unique=True)
    op.create_index("ix_notification_templates_category", "notification_templates", ["category"], unique=False)

    # Create notification_preferences table
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "CONTENT",
                "COMMENTS",
                "WORKFLOW",
                "SECURITY",
                "SYSTEM",
                "MENTIONS",
                "DIGEST",
                name="notificationcategory",
            ),
            nullable=False,
        ),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "digest_frequency",
            sa.Enum("NEVER", "IMMEDIATE", "DAILY", "WEEKLY", name="digestfrequency"),
            nullable=False,
            server_default="IMMEDIATE",
        ),
        sa.Column("quiet_hours", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_preferences_id", "notification_preferences", ["id"], unique=False)
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=False)
    op.create_index(
        "ix_notification_preferences_user_category",
        "notification_preferences",
        ["user_id", "category"],
        unique=True,
    )

    # Create notification_queue table
    op.create_table(
        "notification_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "CONTENT",
                "COMMENTS",
                "WORKFLOW",
                "SECURITY",
                "SYSTEM",
                "MENTIONS",
                "DIGEST",
                name="notificationcategory",
            ),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("variables", sa.Text(), nullable=True),
        sa.Column(
            "channel",
            sa.Enum("EMAIL", "IN_APP", "PUSH", "SMS", "WEBHOOK", name="notificationchannel"),
            nullable=False,
        ),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_digest", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["notification_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_queue_id", "notification_queue", ["id"], unique=False)
    op.create_index("ix_notification_queue_user_id", "notification_queue", ["user_id"], unique=False)
    op.create_index("ix_notification_queue_template_id", "notification_queue", ["template_id"], unique=False)
    op.create_index("ix_notification_queue_category", "notification_queue", ["category"], unique=False)
    op.create_index("ix_notification_queue_is_sent", "notification_queue", ["is_sent"], unique=False)
    op.create_index("ix_notification_queue_pending", "notification_queue", ["is_sent", "scheduled_for"], unique=False)
    op.create_index("ix_notification_queue_user_unread", "notification_queue", ["user_id", "is_read"], unique=False)

    # Create notification_digests table
    op.create_table(
        "notification_digests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "frequency",
            sa.Enum("NEVER", "IMMEDIATE", "DAILY", "WEEKLY", name="digestfrequency"),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("notification_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_digests_id", "notification_digests", ["id"], unique=False)
    op.create_index("ix_notification_digests_user_id", "notification_digests", ["user_id"], unique=False)
    op.create_index(
        "ix_notification_digests_user_period", "notification_digests", ["user_id", "period_start"], unique=False
    )


def downgrade() -> None:
    op.drop_table("notification_digests")
    op.drop_table("notification_queue")
    op.drop_table("notification_preferences")
    op.drop_table("notification_templates")
    op.drop_table("workflow_history")
    op.drop_table("workflow_approvals")
    op.drop_table("workflow_transitions")
    op.drop_table("workflow_states")
    op.execute("DROP TYPE IF EXISTS workflowtype")
    op.execute("DROP TYPE IF EXISTS notificationcategory")
    op.execute("DROP TYPE IF EXISTS notificationchannel")
    op.execute("DROP TYPE IF EXISTS digestfrequency")
