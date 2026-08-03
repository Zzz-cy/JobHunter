"""initial_schema_with_metrics

Revision ID: 227e8dd3c507
Revises:
Create Date: 2026-07-15 10:18:38.110792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '227e8dd3c507'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create all tables including metrics table."""

    # Core tables
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('requirements', sa.Text),
        sa.Column('salary_range', sa.String(100)),
        sa.Column('location', sa.String(100)),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'skills',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('level', sa.String(50)),
        sa.Column('related_jobs', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'relations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('target_name', sa.String(255), nullable=False),
        sa.Column('relation_type', sa.String(50), nullable=False),
        sa.Column('weight', sa.REAL, server_default='1.0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    # Phase 4 tables
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255)),
        sa.Column('industry', sa.String(50), server_default=''),
        sa.Column('role', sa.String(50), server_default='job_seeker'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'sessions_db',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', sa.Integer),
        sa.Column('title', sa.String(255), server_default=''),
        sa.Column('industry_context', sa.String(50), server_default=''),
        sa.Column('role', sa.String(50), server_default='job_seeker'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(50), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('intent', sa.String(50)),
        sa.Column('agent_tasks', sa.Text),
        sa.Column('latency_ms', sa.REAL, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'agent_executions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('request_id', sa.String(50)),
        sa.Column('session_id', sa.String(50)),
        sa.Column('intent', sa.String(50)),
        sa.Column('task_type', sa.String(50)),
        sa.Column('model_used', sa.String(100)),
        sa.Column('input_tokens', sa.Integer, server_default='0'),
        sa.Column('output_tokens', sa.Integer, server_default='0'),
        sa.Column('cost', sa.REAL, server_default='0'),
        sa.Column('latency_ms', sa.REAL, server_default='0'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('retry_count', sa.Integer, server_default='0'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'skill_taxonomy',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('industry', sa.String(50)),
        sa.Column('level', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('source', sa.String(100), server_default='manual'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'industry_configs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('industry_code', sa.String(50), nullable=False, unique=True),
        sa.Column('industry_name', sa.String(100), nullable=False),
        sa.Column('skill_categories', sa.Text),
        sa.Column('prompt_overrides', sa.Text),
        sa.Column('extraction_keywords', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'evaluations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('message_id', sa.Integer),
        sa.Column('user_id', sa.Integer),
        sa.Column('auto_score', sa.REAL, server_default='0'),
        sa.Column('user_score', sa.REAL, server_default='0'),
        sa.Column('user_feedback', sa.Text),
        sa.Column('intent_accuracy', sa.REAL, server_default='0'),
        sa.Column('task_completion', sa.REAL, server_default='0'),
        sa.Column('response_quality', sa.REAL, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    # Metrics table (NEW)
    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.REAL, nullable=False),
        sa.Column('labels_json', sa.Text),
        sa.Column('timestamp', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    # Create indexes
    op.create_index('idx_jobs_name', 'jobs', ['name'])
    op.create_index('idx_skills_name', 'skills', ['name'])
    op.create_index('idx_relations_source', 'relations', ['source_name'])
    op.create_index('idx_relations_target', 'relations', ['target_name'])
    op.create_index('idx_messages_session', 'messages', ['session_id'])
    op.create_index('idx_agent_exec_request', 'agent_executions', ['request_id'])
    op.create_index('idx_agent_exec_session', 'agent_executions', ['session_id'])
    op.create_index('idx_skill_taxonomy_industry', 'skill_taxonomy', ['industry'])
    op.create_index('idx_metrics_name', 'metrics', ['metric_name'])
    op.create_index('idx_metrics_timestamp', 'metrics', ['timestamp'])


def downgrade() -> None:
    """Downgrade schema: drop all tables."""
    # Drop indexes first (some DBs require explicit drop)
    for idx_name in [
        'idx_metrics_timestamp', 'idx_metrics_name',
        'idx_skill_taxonomy_industry', 'idx_agent_exec_session',
        'idx_agent_exec_request', 'idx_messages_session',
        'idx_relations_target', 'idx_relations_source',
        'idx_skills_name', 'idx_jobs_name',
    ]:
        try:
            op.drop_index(idx_name)
        except Exception:
            pass

    # Drop tables in reverse order
    op.drop_table('metrics')
    op.drop_table('evaluations')
    op.drop_table('industry_configs')
    op.drop_table('skill_taxonomy')
    op.drop_table('agent_executions')
    op.drop_table('messages')
    op.drop_table('sessions_db')
    op.drop_table('users')
    op.drop_table('relations')
    op.drop_table('skills')
    op.drop_table('jobs')
