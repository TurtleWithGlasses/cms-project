"""Fix enum case: rename all uppercase PostgreSQL enum values to lowercase

Revision ID: t1u2v3w4x5y6
Revises: s9t0u1v2w3x4
Create Date: 2026-06-06

Background: When values_callable=lambda x: [e.value for e in x] was added to all
Enum columns, SQLAlchemy started sending the Python enum .value (lowercase) to
PostgreSQL. However, the original migrations created 7 enum types with uppercase
labels. This migration renames those labels in-place using ALTER TYPE ... RENAME VALUE,
which is a metadata-only operation that also transparently updates any existing rows.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "t1u2v3w4x5y6"
down_revision: str | None = "s9t0u1v2w3x4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # contentstatus: DRAFT/PENDING/PUBLISHED → draft/pending/published
    op.execute("ALTER TYPE contentstatus RENAME VALUE 'DRAFT' TO 'draft'")
    op.execute("ALTER TYPE contentstatus RENAME VALUE 'PENDING' TO 'pending'")
    op.execute("ALTER TYPE contentstatus RENAME VALUE 'PUBLISHED' TO 'published'")

    # commentstatus: PENDING/APPROVED/REJECTED/SPAM → pending/approved/rejected/spam
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'PENDING' TO 'pending'")
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'APPROVED' TO 'approved'")
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'REJECTED' TO 'rejected'")
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'SPAM' TO 'spam'")
    op.alter_column("comments", "status", server_default="pending")

    # webhookstatus: ACTIVE/PAUSED/FAILED/DISABLED → active/paused/failed/disabled
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'ACTIVE' TO 'active'")
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'PAUSED' TO 'paused'")
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'FAILED' TO 'failed'")
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'DISABLED' TO 'disabled'")
    op.alter_column("webhooks", "status", server_default="active")

    # workflowtype: CONTENT/COMMENT/USER/CUSTOM → content/comment/user/custom
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'CONTENT' TO 'content'")
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'COMMENT' TO 'comment'")
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'USER' TO 'user'")
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'CUSTOM' TO 'custom'")
    op.alter_column("workflow_states", "workflow_type", server_default="content")

    # notificationcategory: CONTENT/COMMENTS/WORKFLOW/SECURITY/SYSTEM/MENTIONS/DIGEST → lowercase
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'CONTENT' TO 'content'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'COMMENTS' TO 'comments'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'WORKFLOW' TO 'workflow'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'SECURITY' TO 'security'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'SYSTEM' TO 'system'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'MENTIONS' TO 'mentions'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'DIGEST' TO 'digest'")

    # digestfrequency: NEVER/IMMEDIATE/DAILY/WEEKLY → never/immediate/daily/weekly
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'NEVER' TO 'never'")
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'IMMEDIATE' TO 'immediate'")
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'DAILY' TO 'daily'")
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'WEEKLY' TO 'weekly'")
    op.alter_column("notification_preferences", "digest_frequency", server_default="immediate")

    # notificationchannel: EMAIL/IN_APP/PUSH/SMS/WEBHOOK → email/in_app/push/sms/webhook
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'EMAIL' TO 'email'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'IN_APP' TO 'in_app'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'PUSH' TO 'push'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'SMS' TO 'sms'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'WEBHOOK' TO 'webhook'")


def downgrade() -> None:
    # notificationchannel
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'webhook' TO 'WEBHOOK'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'sms' TO 'SMS'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'push' TO 'PUSH'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'in_app' TO 'IN_APP'")
    op.execute("ALTER TYPE notificationchannel RENAME VALUE 'email' TO 'EMAIL'")

    # digestfrequency
    op.alter_column("notification_preferences", "digest_frequency", server_default="IMMEDIATE")
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'weekly' TO 'WEEKLY'")
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'daily' TO 'DAILY'")
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'immediate' TO 'IMMEDIATE'")
    op.execute("ALTER TYPE digestfrequency RENAME VALUE 'never' TO 'NEVER'")

    # notificationcategory
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'digest' TO 'DIGEST'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'mentions' TO 'MENTIONS'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'system' TO 'SYSTEM'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'security' TO 'SECURITY'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'workflow' TO 'WORKFLOW'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'comments' TO 'COMMENTS'")
    op.execute("ALTER TYPE notificationcategory RENAME VALUE 'content' TO 'CONTENT'")

    # workflowtype
    op.alter_column("workflow_states", "workflow_type", server_default="CONTENT")
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'custom' TO 'CUSTOM'")
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'user' TO 'USER'")
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'comment' TO 'COMMENT'")
    op.execute("ALTER TYPE workflowtype RENAME VALUE 'content' TO 'CONTENT'")

    # webhookstatus
    op.alter_column("webhooks", "status", server_default="ACTIVE")
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'disabled' TO 'DISABLED'")
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'failed' TO 'FAILED'")
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'paused' TO 'PAUSED'")
    op.execute("ALTER TYPE webhookstatus RENAME VALUE 'active' TO 'ACTIVE'")

    # commentstatus
    op.alter_column("comments", "status", server_default="PENDING")
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'spam' TO 'SPAM'")
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'rejected' TO 'REJECTED'")
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'approved' TO 'APPROVED'")
    op.execute("ALTER TYPE commentstatus RENAME VALUE 'pending' TO 'PENDING'")

    # contentstatus
    op.execute("ALTER TYPE contentstatus RENAME VALUE 'published' TO 'PUBLISHED'")
    op.execute("ALTER TYPE contentstatus RENAME VALUE 'pending' TO 'PENDING'")
    op.execute("ALTER TYPE contentstatus RENAME VALUE 'draft' TO 'DRAFT'")
