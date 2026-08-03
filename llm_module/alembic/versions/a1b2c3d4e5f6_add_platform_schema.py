"""add_platform_schema

新增 DATABASE_SCHEMA.md 定义的平台标准表，扩展现有表字段

Revision ID: a1b2c3d4e5f6
Revises: 227e8dd3c507
Create Date: 2026-07-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '227e8dd3c507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增平台标准表 + 扩展现有表字段"""

    # ==================== 字典层 ====================
    op.create_table(
        'industries',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(32), nullable=False, unique=True),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('parent_id', sa.Integer),
        sa.Column('level', sa.SmallInteger, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    # ==================== 主体层 ====================
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('company_code', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('short_name', sa.String(64)),
        sa.Column('industry_code', sa.String(32)),
        sa.Column('size', sa.String(32)),
        sa.Column('stage', sa.String(32)),
        sa.Column('city', sa.String(64)),
        sa.Column('district', sa.String(64)),
        sa.Column('address', sa.String(255)),
        sa.Column('logo_url', sa.String(512)),
        sa.Column('website', sa.String(255)),
        sa.Column('welfare', sa.Text),
        sa.Column('description', sa.Text),
        sa.Column('source', sa.String(32), server_default='boss'),
        sa.Column('source_url', sa.String(512)),
        sa.Column('is_deleted', sa.SmallInteger, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('resume_code', sa.String(64), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('title', sa.String(128)),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('gender', sa.SmallInteger),
        sa.Column('age', sa.Integer),
        sa.Column('city', sa.String(64)),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(128)),
        sa.Column('source_type', sa.String(16), server_default='pdf'),
        sa.Column('file_url', sa.String(512)),
        sa.Column('parse_status', sa.String(16), server_default='pending'),
        sa.Column('parse_error', sa.String(512)),
        sa.Column('work_years', sa.Integer),
        sa.Column('education', sa.String(16)),
        sa.Column('expect_salary_min', sa.Integer),
        sa.Column('expect_salary_max', sa.Integer),
        sa.Column('expect_city', sa.String(64)),
        sa.Column('expect_job', sa.String(128)),
        sa.Column('overall_score', sa.Numeric(5, 2)),
        sa.Column('parsed_raw', sa.Text),
        sa.Column('is_deleted', sa.SmallInteger, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'resume_skills',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('resume_id', sa.Integer, nullable=False),
        sa.Column('skill_id', sa.Integer, nullable=False),
        sa.Column('proficiency', sa.SmallInteger, server_default='3'),
        sa.Column('years', sa.Numeric(4, 1)),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint('resume_id', 'skill_id', name='uk_resume_skill'),
    )

    op.create_table(
        'resume_experiences',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('resume_id', sa.Integer, nullable=False),
        sa.Column('company_name', sa.String(128), nullable=False),
        sa.Column('title', sa.String(128)),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('description', sa.Text),
        sa.Column('is_current', sa.SmallInteger, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'resume_educations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('resume_id', sa.Integer, nullable=False),
        sa.Column('school', sa.String(128), nullable=False),
        sa.Column('major', sa.String(128)),
        sa.Column('degree', sa.String(32)),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'job_skills',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('job_id', sa.Integer, nullable=False),
        sa.Column('skill_id', sa.Integer, nullable=False),
        sa.Column('is_must', sa.SmallInteger, server_default='0'),
        sa.Column('weight', sa.Numeric(4, 2), server_default='1.00'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint('job_id', 'skill_id', name='uk_job_skill'),
    )

    # ==================== 行为层 ====================
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('job_id', sa.Integer, nullable=False),
        sa.Column('resume_id', sa.Integer),
        sa.Column('status', sa.String(16)),
        sa.Column('is_favorited', sa.SmallInteger, server_default='0'),
        sa.Column('match_score', sa.Numeric(5, 2)),
        sa.Column('submitted_at', sa.DateTime),
        sa.Column('feedback_at', sa.DateTime),
        sa.Column('external_source', sa.String(32)),
        sa.Column('note', sa.String(512)),
        sa.Column('is_deleted', sa.SmallInteger, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint('user_id', 'job_id', name='uk_user_job'),
    )

    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('resume_id', sa.Integer),
        sa.Column('job_id', sa.Integer, nullable=False),
        sa.Column('score', sa.Numeric(5, 2), nullable=False),
        sa.Column('reason', sa.Text),
        sa.Column('strategy', sa.String(32), server_default='rag'),
        sa.Column('snapshot', sa.Text),
        sa.Column('clicked', sa.SmallInteger, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'chat_history',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tool_calls', sa.Text),
        sa.Column('tokens', sa.Integer),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    # ==================== 采集层 ====================
    op.create_table(
        'crawl_sources',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('type', sa.String(32), server_default='job'),
        sa.Column('base_url', sa.String(255)),
        sa.Column('enabled', sa.SmallInteger, server_default='1'),
        sa.Column('config', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        'crawl_tasks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('source_id', sa.Integer, nullable=False),
        sa.Column('task_code', sa.String(64), nullable=False, unique=True),
        sa.Column('keyword', sa.String(128)),
        sa.Column('city', sa.String(64)),
        sa.Column('status', sa.String(16), server_default='pending'),
        sa.Column('total', sa.Integer, server_default='0'),
        sa.Column('succeeded', sa.Integer, server_default='0'),
        sa.Column('failed', sa.Integer, server_default='0'),
        sa.Column('error_msg', sa.String(512)),
        sa.Column('start_at', sa.DateTime),
        sa.Column('end_at', sa.DateTime),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )

    # ==================== 扩展现有表字段 ====================

    # skills — 新增 skill_code, alias, is_hot, updated_at
    try:
        op.add_column('skills', sa.Column('skill_code', sa.String(64)))
        op.add_column('skills', sa.Column('alias', sa.String(255)))
        op.add_column('skills', sa.Column('is_hot', sa.SmallInteger, server_default='0'))
        op.add_column('skills', sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()))
        op.create_unique_constraint('uk_skill_code', 'skills', ['skill_code'])
    except Exception:
        pass

    # users — 新增 user_code, phone, nickname, avatar_url, last_login_at, is_deleted
    try:
        op.add_column('users', sa.Column('user_code', sa.String(64)))
        op.add_column('users', sa.Column('phone', sa.String(20)))
        op.add_column('users', sa.Column('nickname', sa.String(64)))
        op.add_column('users', sa.Column('avatar_url', sa.String(512)))
        op.add_column('users', sa.Column('last_login_at', sa.DateTime))
        op.add_column('users', sa.Column('is_deleted', sa.SmallInteger, server_default='0'))
        op.create_unique_constraint('uk_user_code', 'users', ['user_code'])
    except Exception:
        pass

    # jobs — 新增全部扩展字段（对齐 db_service.py _create_tables）
    try:
        op.add_column('jobs', sa.Column('job_code', sa.String(64)))
        op.add_column('jobs', sa.Column('company_id', sa.Integer))
        op.add_column('jobs', sa.Column('department', sa.String(128)))
        op.add_column('jobs', sa.Column('city', sa.String(64)))
        op.add_column('jobs', sa.Column('district', sa.String(64)))
        op.add_column('jobs', sa.Column('experience_req', sa.String(32)))
        op.add_column('jobs', sa.Column('education_req', sa.String(32)))
        op.add_column('jobs', sa.Column('description_text', sa.Text))
        op.add_column('jobs', sa.Column('salary_min', sa.Integer))
        op.add_column('jobs', sa.Column('salary_max', sa.Integer))
        op.add_column('jobs', sa.Column('salary_unit', sa.String(8), server_default='month'))
        op.add_column('jobs', sa.Column('salary_months', sa.SmallInteger))
        op.add_column('jobs', sa.Column('job_type', sa.String(16), server_default='full'))
        op.add_column('jobs', sa.Column('highlights', sa.Text))
        op.add_column('jobs', sa.Column('advantage', sa.Text))
        op.add_column('jobs', sa.Column('work_address', sa.String(255)))
        op.add_column('jobs', sa.Column('longitude', sa.Numeric(10, 7)))
        op.add_column('jobs', sa.Column('latitude', sa.Numeric(10, 7)))
        op.add_column('jobs', sa.Column('source_url', sa.String(512)))
        op.add_column('jobs', sa.Column('source_id', sa.String(64)))
        op.add_column('jobs', sa.Column('crawl_batch', sa.String(32)))
        op.add_column('jobs', sa.Column('status', sa.String(16), server_default='active'))
        op.add_column('jobs', sa.Column('publish_at', sa.DateTime))
        op.add_column('jobs', sa.Column('crawl_at', sa.DateTime))
        op.add_column('jobs', sa.Column('quality_score', sa.Numeric(4, 2)))
        op.add_column('jobs', sa.Column('is_deleted', sa.SmallInteger, server_default='0'))
        op.add_column('jobs', sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()))
        op.create_unique_constraint('uk_job_code', 'jobs', ['job_code'])
    except Exception:
        pass

    # ==================== 新索引 ====================
    for idx_name, table, cols in [
        # 字典层
        ('idx_skills_category', 'skills', ['category']),
        ('idx_industry_parent', 'industries', ['parent_id']),
        # 主体层
        ('idx_resume_user', 'resumes', ['user_id']),
        ('idx_resume_status', 'resumes', ['parse_status']),
        ('idx_resume_city', 'resumes', ['city']),
        ('idx_rs_resume', 'resume_skills', ['resume_id']),
        ('idx_rs_skill', 'resume_skills', ['skill_id']),
        ('idx_rexp_resume', 'resume_experiences', ['resume_id']),
        ('idx_redu_resume', 'resume_educations', ['resume_id']),
        ('idx_company_industry', 'companies', ['industry_code']),
        ('idx_company_city', 'companies', ['city']),
        ('idx_job_company', 'jobs', ['company_id']),
        ('idx_job_city', 'jobs', ['city']),
        ('idx_job_status', 'jobs', ['status']),
        ('idx_job_salary', 'jobs', ['salary_min', 'salary_max']),
        ('idx_js_job', 'job_skills', ['job_id']),
        ('idx_js_skill', 'job_skills', ['skill_id']),
        # 行为层
        ('idx_app_user_status', 'applications', ['user_id', 'status']),
        ('idx_app_favorite', 'applications', ['user_id', 'is_favorited']),
        ('idx_app_job', 'applications', ['job_id']),
        ('idx_rec_user', 'recommendations', ['user_id', 'created_at']),
        ('idx_rec_strategy', 'recommendations', ['strategy']),
        ('idx_chat_session', 'chat_history', ['session_id', 'created_at']),
        ('idx_chat_user', 'chat_history', ['user_id']),
        # 采集层
        ('idx_task_status', 'crawl_tasks', ['status']),
        ('idx_task_source', 'crawl_tasks', ['source_id']),
    ]:
        try:
            op.create_index(idx_name, table, cols)
        except Exception:
            pass


def downgrade() -> None:
    """回滚：删除新增表和字段"""

    # 删除索引
    for idx in [
        'idx_task_source', 'idx_task_status', 'idx_chat_user', 'idx_chat_session',
        'idx_rec_strategy', 'idx_rec_user', 'idx_app_job', 'idx_app_favorite',
        'idx_app_user_status', 'idx_js_skill', 'idx_js_job', 'idx_job_salary',
        'idx_job_status', 'idx_job_city', 'idx_job_company', 'idx_company_city',
        'idx_company_industry', 'idx_redu_resume', 'idx_rexp_resume', 'idx_rs_skill',
        'idx_rs_resume', 'idx_resume_city', 'idx_resume_status', 'idx_resume_user',
        'idx_industry_parent', 'idx_skills_category',
    ]:
        try:
            op.drop_index(idx)
        except Exception:
            pass

    # 删除 jobs 追加的字段
    for col in ['updated_at', 'is_deleted', 'quality_score', 'crawl_at', 'publish_at',
                'status', 'crawl_batch', 'source_id', 'source_url', 'latitude',
                'longitude', 'work_address', 'advantage', 'highlights', 'job_type',
                'salary_months', 'salary_unit', 'salary_max', 'salary_min',
                'description_text', 'education_req', 'experience_req', 'district',
                'city', 'department', 'company_id', 'job_code']:
        try:
            op.drop_column('jobs', col)
        except Exception:
            pass

    # 删除 users 追加的字段
    for col in ['is_deleted', 'last_login_at', 'avatar_url', 'nickname', 'phone', 'user_code']:
        try:
            op.drop_column('users', col)
        except Exception:
            pass

    # 删除 skills 追加的字段
    for col in ['updated_at', 'is_hot', 'alias', 'skill_code']:
        try:
            op.drop_column('skills', col)
        except Exception:
            pass

    # 删除唯一约束
    for uc_name, table in [
        ('uk_user_job', 'applications'),
        ('uk_resume_skill', 'resume_skills'),
        ('uk_job_skill', 'job_skills'),
        ('uk_job_code', 'jobs'),
        ('uk_user_code', 'users'),
        ('uk_skill_code', 'skills'),
    ]:
        try:
            op.drop_constraint(uc_name, table, type_='unique')
        except Exception:
            pass

    # 删除新增表（反向顺序）
    for table in [
        'crawl_tasks', 'crawl_sources', 'chat_history', 'recommendations',
        'applications', 'job_skills', 'resume_educations', 'resume_experiences',
        'resume_skills', 'resumes', 'companies', 'industries',
    ]:
        try:
            op.drop_table(table)
        except Exception:
            pass
