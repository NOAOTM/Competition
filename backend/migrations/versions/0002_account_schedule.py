"""add account and schedule fields"""
from alembic import op
import sqlalchemy as sa

revision = "0002_account_schedule"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.add_column("users", sa.Column("quota", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("users", sa.Column("auth_status", sa.String(20), nullable=False, server_default="未认证"))
    op.add_column("users", sa.Column("quota_expires_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "calendar_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("kind", sa.String(30), nullable=False, server_default="reminder"),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
    )
    op.create_index("ix_calendar_entries_user_id", "calendar_entries", ["user_id"])
    op.create_index("ix_calendar_entries_starts_at", "calendar_entries", ["starts_at"])


def downgrade():
    op.drop_index("ix_calendar_entries_starts_at", table_name="calendar_entries")
    op.drop_index("ix_calendar_entries_user_id", table_name="calendar_entries")
    op.drop_table("calendar_entries")
    op.drop_column("users", "is_admin")
    op.drop_column("users", "quota_expires_at")
    op.drop_column("users", "auth_status")
    op.drop_column("users", "quota")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "phone")
