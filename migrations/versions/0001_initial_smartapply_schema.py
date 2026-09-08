"""Create the current SmartApply schema.

Revision ID: 0001_initial_smartapply_schema
Revises:
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_smartapply_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password", sa.Text(), nullable=False),
        sa.Column("mobile_number", sa.Text()),
        sa.Column("auth_provider", sa.Text(), server_default="local"),
        sa.Column("api_token", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.Text()),
        sa.Column("photo_path", sa.Text()),
        sa.Column("gender", sa.Text()),
        sa.Column("dob", sa.Text()),
        sa.Column("age", sa.Text()),
        sa.Column("nationality", sa.Text()),
        sa.Column("marital_status", sa.Text()),
        sa.Column("blood_group", sa.Text()),
        sa.Column("aadhaar_number", sa.Text()),
        sa.Column("pan_number", sa.Text()),
        sa.Column("mobile_number", sa.Text()),
        sa.Column("alt_mobile_number", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("alt_email", sa.Text()),
        sa.Column("perm_house_no", sa.Text()),
        sa.Column("perm_street", sa.Text()),
        sa.Column("perm_area", sa.Text()),
        sa.Column("perm_city", sa.Text()),
        sa.Column("perm_district", sa.Text()),
        sa.Column("perm_state", sa.Text()),
        sa.Column("perm_country", sa.Text()),
        sa.Column("perm_pincode", sa.Text()),
        sa.Column("same_as_permanent", sa.Integer(), server_default="0"),
        sa.Column("curr_house_no", sa.Text()),
        sa.Column("curr_street", sa.Text()),
        sa.Column("curr_area", sa.Text()),
        sa.Column("curr_city", sa.Text()),
        sa.Column("curr_district", sa.Text()),
        sa.Column("curr_state", sa.Text()),
        sa.Column("curr_country", sa.Text()),
        sa.Column("curr_pincode", sa.Text()),
        sa.Column("career_objective", sa.Text()),
        sa.Column("education_json", sa.Text()),
        sa.Column("technical_skills_json", sa.Text()),
        sa.Column("soft_skills_json", sa.Text()),
        sa.Column("experience_type", sa.Text()),
        sa.Column("exp_company_name", sa.Text()),
        sa.Column("exp_job_role", sa.Text()),
        sa.Column("exp_start_date", sa.Text()),
        sa.Column("exp_end_date", sa.Text()),
        sa.Column("exp_total_experience", sa.Text()),
        sa.Column("exp_responsibilities", sa.Text()),
        sa.Column("internship_json", sa.Text()),
        sa.Column("projects_json", sa.Text()),
        sa.Column("certifications_json", sa.Text()),
        sa.Column("achievements_json", sa.Text()),
        sa.Column("languages_json", sa.Text()),
        sa.Column("social_json", sa.Text()),
        sa.Column("job_pref_json", sa.Text()),
        sa.Column("documents_json", sa.Text()),
        sa.Column("hobbies", sa.Text()),
        sa.Column("interests", sa.Text()),
        sa.Column("references_json", sa.Text()),
        sa.Column("declaration", sa.Integer(), server_default="0"),
        sa.Column("security_question", sa.Text()),
        sa.Column("security_answer", sa.Text()),
        sa.Column("profile_completion", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="applied"),
        sa.Column("applied_date", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.Text(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade():
    op.drop_table("applications")
    op.drop_table("profiles")
    op.drop_table("users")
