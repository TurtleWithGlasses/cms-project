"""Add Phase 9 tables: Teams, Sessions, Templates, Imports.

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2024-01-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g8h9i0j1k2l3"
down_revision: str | None = "f7g8h9i0j1k2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Teams table
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("parent_team_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("allow_member_invite", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "default_member_role",
            sa.Enum("owner", "admin", "member", "viewer", name="teamrole"),
            nullable=False,
            server_default="member",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_teams_id"), "teams", ["id"], unique=False)
    op.create_index(op.f("ix_teams_slug"), "teams", ["slug"], unique=True)

    # Team members table
    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "admin", "member", "viewer", name="teamrole"),
            nullable=False,
            server_default="member",
        ),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_team_members_id"), "team_members", ["id"], unique=False)
    op.create_index(op.f("ix_team_members_team_id"), "team_members", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"], unique=False)

    # Team invitations table
    op.create_table(
        "team_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "role",
            sa.Enum("owner", "admin", "member", "viewer", name="teamrole"),
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", "declined", "expired", name="invitationstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("invited_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_team_invitations_id"), "team_invitations", ["id"], unique=False)
    op.create_index(op.f("ix_team_invitations_team_id"), "team_invitations", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_invitations_email"), "team_invitations", ["email"], unique=False)
    op.create_index(op.f("ix_team_invitations_token"), "team_invitations", ["token"], unique=True)

    # User sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(255), nullable=False),
        sa.Column("refresh_token", sa.String(255), nullable=True),
        sa.Column("device_type", sa.String(50), nullable=True),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("browser", sa.String(100), nullable=True),
        sa.Column("browser_version", sa.String(50), nullable=True),
        sa.Column("os", sa.String(100), nullable=True),
        sa.Column("os_version", sa.String(50), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_user_sessions_id"), "user_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_sessions_session_token"), "user_sessions", ["session_token"], unique=True)
    op.create_index(op.f("ix_user_sessions_refresh_token"), "user_sessions", ["refresh_token"], unique=True)

    # Login attempts table
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(255), nullable=True),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_login_attempts_id"), "login_attempts", ["id"], unique=False)
    op.create_index(op.f("ix_login_attempts_user_id"), "login_attempts", ["user_id"], unique=False)
    op.create_index(op.f("ix_login_attempts_email"), "login_attempts", ["email"], unique=False)

    # Content templates table
    op.create_table(
        "content_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="templatestatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("default_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_content_templates_id"), "content_templates", ["id"], unique=False)
    op.create_index(op.f("ix_content_templates_slug"), "content_templates", ["slug"], unique=True)

    # Template fields table
    op.create_table(
        "template_fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "field_type",
            sa.Enum(
                "text",
                "textarea",
                "richtext",
                "number",
                "date",
                "datetime",
                "boolean",
                "select",
                "multiselect",
                "image",
                "file",
                "url",
                "email",
                "json",
                "reference",
                name="fieldtype",
            ),
            nullable=False,
        ),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_unique", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("validation_rules", sa.Text(), nullable=True),
        sa.Column("options", sa.Text(), nullable=True),
        sa.Column("reference_template_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["template_id"], ["content_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reference_template_id"], ["content_templates.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_template_fields_id"), "template_fields", ["id"], unique=False)
    op.create_index(op.f("ix_template_fields_template_id"), "template_fields", ["template_id"], unique=False)

    # Template revisions table
    op.create_table(
        "template_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.String(500), nullable=True),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["template_id"], ["content_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_template_revisions_id"), "template_revisions", ["id"], unique=False)
    op.create_index(op.f("ix_template_revisions_template_id"), "template_revisions", ["template_id"], unique=False)

    # Import jobs table
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "import_type",
            sa.Enum("content", "users", "categories", "tags", "media", "mixed", name="importtype"),
            nullable=False,
        ),
        sa.Column(
            "import_format",
            sa.Enum("json", "csv", "xml", name="importformat"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "validating",
                "processing",
                "completed",
                "failed",
                "cancelled",
                "partial",
                name="importstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "duplicate_handling",
            sa.Enum("skip", "update", "create_new", "fail", name="duplicatehandling"),
            nullable=False,
            server_default="skip",
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("field_mapping", sa.Text(), nullable=True),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("results_summary", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_import_jobs_id"), "import_jobs", ["id"], unique=False)

    # Import records table
    op.create_table(
        "import_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_job_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "validating",
                "processing",
                "completed",
                "failed",
                "cancelled",
                "partial",
                name="importstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_record_id", sa.Integer(), nullable=True),
        sa.Column("created_record_type", sa.String(50), nullable=True),
        sa.Column("source_data", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["import_job_id"], ["import_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_import_records_id"), "import_records", ["id"], unique=False)
    op.create_index(op.f("ix_import_records_import_job_id"), "import_records", ["import_job_id"], unique=False)

    # Export jobs table
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "export_type",
            sa.Enum("content", "users", "categories", "tags", "media", "mixed", name="importtype"),
            nullable=False,
        ),
        sa.Column(
            "export_format",
            sa.Enum("json", "csv", "xml", name="importformat"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "validating",
                "processing",
                "completed",
                "failed",
                "cancelled",
                "partial",
                name="importstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("filters", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exported_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_export_jobs_id"), "export_jobs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("export_jobs")
    op.drop_table("import_records")
    op.drop_table("import_jobs")
    op.drop_table("template_revisions")
    op.drop_table("template_fields")
    op.drop_table("content_templates")
    op.drop_table("login_attempts")
    op.drop_table("user_sessions")
    op.drop_table("team_invitations")
    op.drop_table("team_members")
    op.drop_table("teams")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS teamrole")
    op.execute("DROP TYPE IF EXISTS invitationstatus")
    op.execute("DROP TYPE IF EXISTS templatestatus")
    op.execute("DROP TYPE IF EXISTS fieldtype")
    op.execute("DROP TYPE IF EXISTS importtype")
    op.execute("DROP TYPE IF EXISTS importformat")
    op.execute("DROP TYPE IF EXISTS importstatus")
    op.execute("DROP TYPE IF EXISTS duplicatehandling")
