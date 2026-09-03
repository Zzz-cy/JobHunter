"""
MySQL数据库服务 - 存储结构化数据
支持岗位、技能、能力等实体及关系
"""
import json
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from utils.config import MYSQL_CONFIG, SQLITE_PATH
from utils.logger import get_logger
logger = get_logger("services.db_service")

# 尝试导入MySQL驱动
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logger.warning("pymysql未安装，将使用SQLite")


@dataclass
class JobEntity:
    """岗位实体（对齐 DATABASE_SCHEMA.md jobs 表）"""
    id: Optional[int] = None
    job_code: str = ""
    company_id: Optional[int] = None
    name: str = ""
    category: str = ""
    department: str = ""
    city: str = ""
    district: str = ""
    experience_req: str = ""
    education_req: str = ""
    description: str = ""
    description_text: str = ""
    requirements: str = ""
    salary_range: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_unit: str = "month"
    salary_months: Optional[int] = None
    job_type: str = "full"
    location: str = ""
    source: str = "boss"
    source_url: str = ""
    source_id: str = ""
    status: str = "active"
    is_deleted: int = 0
    created_at: Optional[str] = None


@dataclass
class SkillEntity:
    """技能实体（对齐 DATABASE_SCHEMA.md skills 表）"""
    id: Optional[int] = None
    skill_code: str = ""
    name: str = ""
    alias: str = ""
    category: str = ""
    is_hot: int = 0
    description: str = ""
    level: str = ""  # beginner, intermediate, advanced
    related_jobs: str = ""  # JSON数组
    created_at: Optional[str] = None


@dataclass
class CompetencyRelation:
    """能力关系"""
    id: Optional[int] = None
    source_type: str = ""  # job, skill
    source_name: str = ""
    target_type: str = ""  # job, skill
    target_name: str = ""
    relation_type: str = ""  # requires, prerequisite, related
    weight: float = 1.0
    created_at: Optional[str] = None


@dataclass
class IndustryEntity:
    """行业实体（字典层）"""
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    parent_id: Optional[int] = None
    level: int = 1


@dataclass
class CompanyEntity:
    """公司实体（主体层）"""
    id: Optional[int] = None
    company_code: str = ""
    name: str = ""
    short_name: str = ""
    industry_code: str = ""
    size: str = ""
    stage: str = ""
    city: str = ""
    district: str = ""
    address: str = ""
    logo_url: str = ""
    website: str = ""
    welfare: str = ""  # JSON
    description: str = ""
    source: str = "boss"
    source_url: str = ""
    is_deleted: int = 0


@dataclass
class ResumeEntity:
    """简历实体（主体层）"""
    id: Optional[int] = None
    resume_code: str = ""
    user_id: int = 0
    title: str = ""
    name: str = ""
    gender: Optional[int] = None
    age: Optional[int] = None
    city: str = ""
    phone: str = ""
    email: str = ""
    source_type: str = "pdf"
    file_url: str = ""
    parse_status: str = "pending"
    parse_error: str = ""
    work_years: Optional[int] = None
    education: str = ""
    expect_salary_min: Optional[int] = None
    expect_salary_max: Optional[int] = None
    expect_city: str = ""
    expect_job: str = ""
    overall_score: Optional[float] = None
    parsed_raw: str = ""  # JSON
    is_deleted: int = 0


@dataclass
class ResumeSkillEntity:
    """简历-技能关联"""
    id: Optional[int] = None
    resume_id: int = 0
    skill_id: int = 0
    proficiency: int = 3
    years: Optional[float] = None


@dataclass
class ResumeExperienceEntity:
    """工作经历"""
    id: Optional[int] = None
    resume_id: int = 0
    company_name: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    is_current: int = 0


@dataclass
class ResumeEducationEntity:
    """教育经历"""
    id: Optional[int] = None
    resume_id: int = 0
    school: str = ""
    major: str = ""
    degree: str = ""
    start_date: str = ""
    end_date: str = ""


@dataclass
class JobSkillEntity:
    """职位-技能关联"""
    id: Optional[int] = None
    job_id: int = 0
    skill_id: int = 0
    is_must: int = 0
    weight: float = 1.0


@dataclass
class ApplicationEntity:
    """用户-职位关系（行为层）"""
    id: Optional[int] = None
    user_id: int = 0
    job_id: int = 0
    resume_id: Optional[int] = None
    status: str = ""  # NULL/submitted/interviewed/offer/rejected
    is_favorited: int = 0
    match_score: Optional[float] = None
    submitted_at: str = ""
    feedback_at: str = ""
    external_source: str = ""
    note: str = ""
    is_deleted: int = 0


@dataclass
class RecommendationEntity:
    """推荐流水（行为层）"""
    id: Optional[int] = None
    user_id: int = 0
    resume_id: Optional[int] = None
    job_id: int = 0
    score: float = 0.0
    reason: str = ""
    strategy: str = "rag"
    snapshot: str = ""  # JSON
    clicked: int = 0


@dataclass
class ChatHistoryEntity:
    """AI对话历史（行为层）"""
    id: Optional[int] = None
    user_id: int = 0
    session_id: str = ""
    role: str = ""
    content: str = ""
    tool_calls: str = ""  # JSON
    tokens: Optional[int] = None


@dataclass
class CrawlSourceEntity:
    """数据源配置（采集层）"""
    id: Optional[int] = None
    name: str = ""
    type: str = "job"
    base_url: str = ""
    enabled: int = 1
    config: str = ""  # JSON


@dataclass
class CrawlTaskEntity:
    """爬虫任务（采集层）"""
    id: Optional[int] = None
    source_id: int = 0
    task_code: str = ""
    keyword: str = ""
    city: str = ""
    status: str = "pending"
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    error_msg: str = ""
    start_at: str = ""
    end_at: str = ""


class DatabaseService:
    """数据库服务 - 支持MySQL和SQLite"""

    def __init__(self):
        self.use_mysql = MYSQL_AVAILABLE and self._test_mysql_connection()
        self.conn = None
        self.cursor = None

        # MySQL使用%s占位符，SQLite使用?占位符
        self._placeholder = "%s" if self.use_mysql else "?"

        if self.use_mysql:
            self._init_mysql()
        else:
            self._init_sqlite()

        self._create_tables()

    def _q(self, sql: str) -> str:
        """将SQL中的?占位符转换为当前数据库的占位符"""
        if self._placeholder == "?":
            return sql
        return sql.replace("?", "%s")

    def _test_mysql_connection(self) -> bool:
        """测试MySQL连接"""
        try:
            conn = pymysql.connect(
                host=MYSQL_CONFIG["host"],
                port=MYSQL_CONFIG["port"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"],
                connect_timeout=3,  # 3秒超时，避免启动卡住
            )
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"MySQL连接失败: {e}")
            return False

    def _init_mysql(self):
        """初始化MySQL连接"""
        try:
            self.conn = pymysql.connect(
                host=MYSQL_CONFIG["host"],
                port=MYSQL_CONFIG["port"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
            )
            self.cursor = self.conn.cursor()
            logger.info(f"MySQL连接成功: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
        except Exception as e:
            logger.error(f"MySQL初始化失败: {e}")
            self.use_mysql = False
            self._init_sqlite()

    def _init_sqlite(self):
        """初始化SQLite连接"""
        import os
        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
        self.conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        logger.info(f"SQLite连接成功: {SQLITE_PATH}")

    def _add_column_if_missing(self, table: str, column: str, ddl: str):
        """安全地为现有表追加字段（MySQL用INFORMATION_SCHEMA检查，SQLite用PRAGMA table_info）"""
        try:
            if self.use_mysql:
                self.cursor.execute(self._q(
                    "SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?"
                ), (MYSQL_CONFIG["database"], table, column))
                exists = self.cursor.fetchone()["cnt"] > 0
            else:
                self.cursor.execute(f"PRAGMA table_info({table})")
                cols = [row[1] for row in self.cursor.fetchall()]
                exists = column in cols
            if not exists:
                self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        except Exception as e:
            logger.debug(f"追加字段 {table}.{column} 跳过: {e}")

    def _create_llm_runtime_tables(self):
        """合并部署(与主后端共库 jobhunter)时, llm 只自建自己的运行时支撑表。

        主业务表(skills/jobs/users/resumes/companies/...)一律由主后端负责创建维护,
        llm 不再对其做 CREATE / 补列 / 加索引(避免启动顺序错乱或 schema 漂移改到主表)。
        下方 SQLite/独立库路径里保留了同一批运行时表的建表逻辑(单机演示用), 两处保持一致。
        """
        # 与 db/mysql/04_llm_module.sql 的 9 张 llm 私表 DDL 对齐
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                source_type VARCHAR(50) NOT NULL,
                source_name VARCHAR(255) NOT NULL,
                target_type VARCHAR(50) NOT NULL,
                target_name VARCHAR(255) NOT NULL,
                relation_type VARCHAR(50) NOT NULL,
                weight DOUBLE DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_relations_source (source_name(191)),
                KEY idx_relations_target (target_name(191))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions_db (
                id VARCHAR(50) NOT NULL,
                user_id INT DEFAULT NULL,
                title VARCHAR(255) NOT NULL DEFAULT '',
                industry_context VARCHAR(50) NOT NULL DEFAULT '',
                role VARCHAR(50) NOT NULL DEFAULT 'job_seeker',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_sessions_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                session_id VARCHAR(50) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                intent VARCHAR(50) DEFAULT NULL,
                agent_tasks TEXT,
                recommended_jobs TEXT,
                latency_ms DOUBLE NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_messages_session (session_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # 老库 messages 表缺 recommended_jobs 列(2026-09-03 新增: 历史回放岗位卡片用), 已存在则忽略
        try:
            self.cursor.execute("ALTER TABLE messages ADD COLUMN recommended_jobs TEXT")
            self.conn.commit()
        except Exception:
            pass
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_executions (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                request_id VARCHAR(50) DEFAULT NULL,
                session_id VARCHAR(50) DEFAULT NULL,
                intent VARCHAR(50) DEFAULT NULL,
                task_type VARCHAR(50) DEFAULT NULL,
                model_used VARCHAR(100) DEFAULT NULL,
                input_tokens INT NOT NULL DEFAULT 0,
                output_tokens INT NOT NULL DEFAULT 0,
                cost DOUBLE NOT NULL DEFAULT 0,
                latency_ms DOUBLE NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                retry_count INT NOT NULL DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_agent_exec_request (request_id),
                KEY idx_agent_exec_session (session_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_taxonomy (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) DEFAULT NULL,
                industry VARCHAR(50) DEFAULT NULL,
                level VARCHAR(50) DEFAULT NULL,
                description TEXT,
                source VARCHAR(100) NOT NULL DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_skill_taxonomy_industry (industry)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_configs (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                industry_code VARCHAR(50) NOT NULL,
                industry_name VARCHAR(100) NOT NULL,
                skill_categories TEXT,
                prompt_overrides TEXT,
                extraction_keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uk_industry_code (industry_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                message_id INT DEFAULT NULL,
                user_id INT DEFAULT NULL,
                auto_score DOUBLE NOT NULL DEFAULT 0,
                user_score DOUBLE NOT NULL DEFAULT 0,
                user_feedback TEXT,
                intent_accuracy DOUBLE NOT NULL DEFAULT 0,
                task_completion DOUBLE NOT NULL DEFAULT 0,
                response_quality DOUBLE NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DOUBLE NOT NULL,
                labels_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_metrics_name (metric_name),
                KEY idx_metrics_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_quotas (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                user_id INT NOT NULL,
                daily_calls INT NOT NULL DEFAULT 0,
                daily_tokens INT NOT NULL DEFAULT 0,
                quota_date VARCHAR(10) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_user_quotas_user_date (user_id, quota_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # llm 运行时配置项(如 admin_default_model: 管理员后台设的平台默认模型)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_config (
                config_key VARCHAR(64) NOT NULL,
                value VARCHAR(255) NOT NULL DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (config_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.conn.commit()

    def _create_tables(self):
        """创建数据表"""
        # 合并部署(与主后端共库 jobhunter): 主业务表由主后端负责建/维护,
        # llm 启动只自建自己的运行时表后即返回, 不再对主表做任何 CREATE/补列/加索引。
        if self.use_mysql and str(MYSQL_CONFIG.get("database", "")).lower() in ("jobhunter",):
            self._create_llm_runtime_tables()
            return
        # MySQL和SQLite的DDL差异：AUTO_INCREMENT vs AUTOINCREMENT
        auto_inc = "AUTO_INCREMENT" if self.use_mysql else "AUTOINCREMENT"
        # SQLite不支持JSON类型，用TEXT代替；MySQL支持JSON
        json_type = "JSON" if self.use_mysql else "TEXT"

        # ==================== 第一层：字典层（标准表，对应 DATABASE_SCHEMA.md）====================
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY {auto_inc},
                skill_code VARCHAR(64) NOT NULL UNIQUE,
                name VARCHAR(128) NOT NULL UNIQUE,
                alias VARCHAR(255),
                category VARCHAR(64),
                is_hot TINYINT(1) DEFAULT 0,
                description TEXT,
                level VARCHAR(50),
                related_jobs TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS industries (
                id INTEGER PRIMARY KEY {auto_inc},
                code VARCHAR(32) NOT NULL UNIQUE,
                name VARCHAR(64) NOT NULL,
                parent_id INT UNSIGNED,
                level TINYINT DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================== 第二层：主体层（标准表）====================

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY {auto_inc},
                user_code VARCHAR(64) NOT NULL UNIQUE,
                username VARCHAR(100) NOT NULL UNIQUE,
                phone VARCHAR(20),
                email VARCHAR(128),
                password_hash VARCHAR(128) NOT NULL,
                nickname VARCHAR(64),
                avatar_url VARCHAR(512),
                industry VARCHAR(50) DEFAULT '',
                role VARCHAR(16) DEFAULT 'user',
                last_login_at DATETIME,
                is_active INTEGER DEFAULT 1,
                is_deleted TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY {auto_inc},
                resume_code VARCHAR(64) NOT NULL UNIQUE,
                user_id BIGINT UNSIGNED NOT NULL,
                title VARCHAR(128),
                name VARCHAR(64) NOT NULL,
                gender TINYINT,
                age INT,
                city VARCHAR(64),
                phone VARCHAR(20),
                email VARCHAR(128),
                source_type VARCHAR(16) DEFAULT 'pdf',
                file_url VARCHAR(512),
                parse_status VARCHAR(16) DEFAULT 'pending',
                parse_error VARCHAR(512),
                work_years INT,
                education VARCHAR(16),
                expect_salary_min INT,
                expect_salary_max INT,
                expect_city VARCHAR(64),
                expect_job VARCHAR(128),
                overall_score DECIMAL(5,2),
                parsed_raw {json_type},
                is_deleted TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS resume_skills (
                id INTEGER PRIMARY KEY {auto_inc},
                resume_id BIGINT UNSIGNED NOT NULL,
                skill_id BIGINT UNSIGNED NOT NULL,
                proficiency TINYINT DEFAULT 3,
                years DECIMAL(4,1),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS resume_experiences (
                id INTEGER PRIMARY KEY {auto_inc},
                resume_id BIGINT UNSIGNED NOT NULL,
                company_name VARCHAR(128) NOT NULL,
                title VARCHAR(128),
                start_date DATE,
                end_date DATE,
                description TEXT,
                is_current TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS resume_educations (
                id INTEGER PRIMARY KEY {auto_inc},
                resume_id BIGINT UNSIGNED NOT NULL,
                school VARCHAR(128) NOT NULL,
                major VARCHAR(128),
                degree VARCHAR(32),
                start_date DATE,
                end_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY {auto_inc},
                company_code VARCHAR(64) NOT NULL UNIQUE,
                name VARCHAR(128) NOT NULL,
                short_name VARCHAR(64),
                industry_code VARCHAR(32),
                size VARCHAR(32),
                stage VARCHAR(32),
                city VARCHAR(64),
                district VARCHAR(64),
                address VARCHAR(255),
                logo_url VARCHAR(512),
                website VARCHAR(255),
                welfare {json_type},
                description TEXT,
                source VARCHAR(32) DEFAULT 'boss',
                source_url VARCHAR(512),
                is_deleted TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY {auto_inc},
                job_code VARCHAR(64) NOT NULL UNIQUE,
                company_id BIGINT UNSIGNED,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                department VARCHAR(128),
                city VARCHAR(64),
                district VARCHAR(64),
                experience_req VARCHAR(32),
                education_req VARCHAR(32),
                description TEXT,
                description_text TEXT,
                requirements TEXT,
                salary_range VARCHAR(100),
                salary_min INT,
                salary_max INT,
                salary_unit VARCHAR(8) DEFAULT 'month',
                salary_months TINYINT,
                job_type VARCHAR(16) DEFAULT 'full',
                highlights {json_type},
                advantage TEXT,
                location VARCHAR(100),
                work_address VARCHAR(255),
                longitude DECIMAL(10,7),
                latitude DECIMAL(10,7),
                source VARCHAR(32) DEFAULT 'boss',
                source_url VARCHAR(512),
                source_id VARCHAR(64),
                crawl_batch VARCHAR(32),
                status VARCHAR(16) DEFAULT 'active',
                publish_at DATETIME,
                crawl_at DATETIME,
                quality_score DECIMAL(4,2),
                is_deleted TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS job_skills (
                id INTEGER PRIMARY KEY {auto_inc},
                job_id BIGINT UNSIGNED NOT NULL,
                skill_id BIGINT UNSIGNED NOT NULL,
                is_must TINYINT(1) DEFAULT 0,
                weight DECIMAL(4,2) DEFAULT 1.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================== 第三层：行为层（标准表）====================

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY {auto_inc},
                user_id BIGINT UNSIGNED NOT NULL,
                job_id BIGINT UNSIGNED NOT NULL,
                resume_id BIGINT UNSIGNED,
                status VARCHAR(16),
                is_favorited TINYINT(1) DEFAULT 0,
                match_score DECIMAL(5,2),
                submitted_at DATETIME,
                feedback_at DATETIME,
                external_source VARCHAR(32),
                note VARCHAR(512),
                is_deleted TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY {auto_inc},
                user_id BIGINT UNSIGNED NOT NULL,
                resume_id BIGINT UNSIGNED,
                job_id BIGINT UNSIGNED NOT NULL,
                score DECIMAL(5,2) NOT NULL,
                reason TEXT,
                strategy VARCHAR(32) DEFAULT 'rag',
                snapshot {json_type},
                clicked TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY {auto_inc},
                user_id BIGINT UNSIGNED NOT NULL,
                session_id VARCHAR(64) NOT NULL,
                role VARCHAR(16) NOT NULL,
                content MEDIUMTEXT NOT NULL,
                tool_calls {json_type},
                tokens INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================== 第四层：采集层（标准表）====================

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS crawl_sources (
                id INTEGER PRIMARY KEY {auto_inc},
                name VARCHAR(64) NOT NULL,
                type VARCHAR(32) DEFAULT 'job',
                base_url VARCHAR(255),
                enabled TINYINT(1) DEFAULT 1,
                config {json_type},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS crawl_tasks (
                id INTEGER PRIMARY KEY {auto_inc},
                source_id INT UNSIGNED NOT NULL,
                task_code VARCHAR(64) NOT NULL UNIQUE,
                keyword VARCHAR(128),
                city VARCHAR(64),
                status VARCHAR(16) DEFAULT 'pending',
                total INT DEFAULT 0,
                succeeded INT DEFAULT 0,
                failed INT DEFAULT 0,
                error_msg VARCHAR(512),
                start_at DATETIME,
                end_at DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================== LLM 模块特有表（保留）====================

        # 关系表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY {auto_inc},
                source_type VARCHAR(50) NOT NULL,
                source_name VARCHAR(255) NOT NULL,
                target_type VARCHAR(50) NOT NULL,
                target_name VARCHAR(255) NOT NULL,
                relation_type VARCHAR(50) NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 会话持久化表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions_db (
                id VARCHAR(50) PRIMARY KEY,
                user_id INTEGER,
                title VARCHAR(255) DEFAULT '',
                industry_context VARCHAR(50) DEFAULT '',
                role VARCHAR(50) DEFAULT 'job_seeker',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 消息表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY {auto_inc},
                session_id VARCHAR(50) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                intent VARCHAR(50),
                agent_tasks TEXT,
                recommended_jobs TEXT,
                latency_ms REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Agent执行记录表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS agent_executions (
                id INTEGER PRIMARY KEY {auto_inc},
                request_id VARCHAR(50),
                session_id VARCHAR(50),
                intent VARCHAR(50),
                task_type VARCHAR(50),
                model_used VARCHAR(100),
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0,
                latency_ms REAL DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 技能库表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS skill_taxonomy (
                id INTEGER PRIMARY KEY {auto_inc},
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                industry VARCHAR(50),
                level VARCHAR(50),
                description TEXT,
                source VARCHAR(100) DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 行业配置表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS industry_configs (
                id INTEGER PRIMARY KEY {auto_inc},
                industry_code VARCHAR(50) NOT NULL UNIQUE,
                industry_name VARCHAR(100) NOT NULL,
                skill_categories TEXT,
                prompt_overrides TEXT,
                extraction_keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 评估表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY {auto_inc},
                message_id INTEGER,
                user_id INTEGER,
                auto_score REAL DEFAULT 0,
                user_score REAL DEFAULT 0,
                user_feedback TEXT,
                intent_accuracy REAL DEFAULT 0,
                task_completion REAL DEFAULT 0,
                response_quality REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 监控指标表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY {auto_inc},
                metric_name VARCHAR(100) NOT NULL,
                metric_value REAL NOT NULL,
                labels_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 用户资源配额表
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_quotas (
                id INTEGER PRIMARY KEY {auto_inc},
                user_id INTEGER NOT NULL,
                daily_calls INTEGER DEFAULT 0,
                daily_tokens INTEGER DEFAULT 0,
                quota_date VARCHAR(10) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================== 为旧表追加新字段（兼容已有数据）====================
        # 旧的 skills 表若已存在且缺少 skill_code 等字段，需追加
        self._add_column_if_missing("skills", "skill_code", "VARCHAR(64)")
        self._add_column_if_missing("skills", "alias", "VARCHAR(255)")
        self._add_column_if_missing("skills", "is_hot", "TINYINT(1) DEFAULT 0")
        self._add_column_if_missing("skills", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        # skill_code 必须唯一，尝试追加唯一索引（失败忽略，已有重复数据时跳过）
        try:
            if self.use_mysql:
                self.cursor.execute("CREATE UNIQUE INDEX uk_skill_code ON skills(skill_code)")
            else:
                self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uk_skill_code ON skills(skill_code)")
        except Exception:
            pass

        # 旧的 users 表追加字段
        self._add_column_if_missing("users", "user_code", "VARCHAR(64)")
        self._add_column_if_missing("users", "phone", "VARCHAR(20)")
        self._add_column_if_missing("users", "nickname", "VARCHAR(64)")
        self._add_column_if_missing("users", "avatar_url", "VARCHAR(512)")
        self._add_column_if_missing("users", "last_login_at", "DATETIME")
        self._add_column_if_missing("users", "is_deleted", "TINYINT(1) DEFAULT 0")
        try:
            if self.use_mysql:
                self.cursor.execute("CREATE UNIQUE INDEX uk_user_code ON users(user_code)")
            else:
                self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uk_user_code ON users(user_code)")
        except Exception:
            pass

        # 旧的 jobs 表追加字段
        self._add_column_if_missing("jobs", "job_code", "VARCHAR(64)")
        self._add_column_if_missing("jobs", "company_id", "BIGINT UNSIGNED")
        self._add_column_if_missing("jobs", "city", "VARCHAR(64)")
        self._add_column_if_missing("jobs", "district", "VARCHAR(64)")
        self._add_column_if_missing("jobs", "experience_req", "VARCHAR(32)")
        self._add_column_if_missing("jobs", "education_req", "VARCHAR(32)")
        self._add_column_if_missing("jobs", "description_text", "TEXT")
        self._add_column_if_missing("jobs", "department", "VARCHAR(128)")
        self._add_column_if_missing("jobs", "salary_min", "INT")
        self._add_column_if_missing("jobs", "salary_max", "INT")
        self._add_column_if_missing("jobs", "salary_unit", "VARCHAR(8) DEFAULT 'month'")
        self._add_column_if_missing("jobs", "salary_months", "TINYINT")
        self._add_column_if_missing("jobs", "job_type", "VARCHAR(16) DEFAULT 'full'")
        self._add_column_if_missing("jobs", "highlights", json_type)
        self._add_column_if_missing("jobs", "advantage", "TEXT")
        self._add_column_if_missing("jobs", "work_address", "VARCHAR(255)")
        self._add_column_if_missing("jobs", "longitude", "DECIMAL(10,7)")
        self._add_column_if_missing("jobs", "latitude", "DECIMAL(10,7)")
        self._add_column_if_missing("jobs", "source_url", "VARCHAR(512)")
        self._add_column_if_missing("jobs", "source_id", "VARCHAR(64)")
        self._add_column_if_missing("jobs", "crawl_batch", "VARCHAR(32)")
        self._add_column_if_missing("jobs", "status", "VARCHAR(16) DEFAULT 'active'")
        self._add_column_if_missing("jobs", "publish_at", "DATETIME")
        self._add_column_if_missing("jobs", "crawl_at", "DATETIME")
        self._add_column_if_missing("jobs", "quality_score", "DECIMAL(4,2)")
        self._add_column_if_missing("jobs", "is_deleted", "TINYINT(1) DEFAULT 0")
        self._add_column_if_missing("jobs", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        try:
            if self.use_mysql:
                self.cursor.execute("CREATE UNIQUE INDEX uk_job_code ON jobs(job_code)")
            else:
                self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uk_job_code ON jobs(job_code)")
        except Exception:
            pass

        # 创建索引
        if self.use_mysql:
            # MySQL不支持CREATE INDEX IF NOT EXISTS，用存储过程处理
            index_sqls = [
                ("idx_jobs_name", "CREATE INDEX idx_jobs_name ON jobs(name)"),
                ("idx_skills_name", "CREATE INDEX idx_skills_name ON skills(name)"),
                ("idx_skills_category", "CREATE INDEX idx_skills_category ON skills(category)"),
                ("idx_relations_source", "CREATE INDEX idx_relations_source ON relations(source_name)"),
                ("idx_relations_target", "CREATE INDEX idx_relations_target ON relations(target_name)"),
                ("idx_messages_session", "CREATE INDEX idx_messages_session ON messages(session_id)"),
                ("idx_agent_exec_request", "CREATE INDEX idx_agent_exec_request ON agent_executions(request_id)"),
                ("idx_agent_exec_session", "CREATE INDEX idx_agent_exec_session ON agent_executions(session_id)"),
                ("idx_skill_taxonomy_industry", "CREATE INDEX idx_skill_taxonomy_industry ON skill_taxonomy(industry)"),
                ("idx_sessions_user_id", "CREATE INDEX idx_sessions_user_id ON sessions_db(user_id)"),
                ("idx_user_quotas_user_date", "CREATE INDEX idx_user_quotas_user_date ON user_quotas(user_id, quota_date)"),
                ("idx_industry_parent", "CREATE INDEX idx_industry_parent ON industries(parent_id)"),
                ("idx_resume_user", "CREATE INDEX idx_resume_user ON resumes(user_id)"),
                ("idx_resume_status", "CREATE INDEX idx_resume_status ON resumes(parse_status)"),
                ("idx_resume_city", "CREATE INDEX idx_resume_city ON resumes(city)"),
                ("idx_rs_resume", "CREATE INDEX idx_rs_resume ON resume_skills(resume_id)"),
                ("idx_rs_skill", "CREATE INDEX idx_rs_skill ON resume_skills(skill_id)"),
                ("idx_rexp_resume", "CREATE INDEX idx_rexp_resume ON resume_experiences(resume_id)"),
                ("idx_redu_resume", "CREATE INDEX idx_redu_resume ON resume_educations(resume_id)"),
                ("idx_company_industry", "CREATE INDEX idx_company_industry ON companies(industry_code)"),
                ("idx_company_city", "CREATE INDEX idx_company_city ON companies(city)"),
                ("idx_job_company", "CREATE INDEX idx_job_company ON jobs(company_id)"),
                ("idx_job_city", "CREATE INDEX idx_job_city ON jobs(city)"),
                ("idx_job_status", "CREATE INDEX idx_job_status ON jobs(status)"),
                ("idx_job_salary", "CREATE INDEX idx_job_salary ON jobs(salary_min, salary_max)"),
                ("idx_js_job", "CREATE INDEX idx_js_job ON job_skills(job_id)"),
                ("idx_js_skill", "CREATE INDEX idx_js_skill ON job_skills(skill_id)"),
                ("idx_app_user_status", "CREATE INDEX idx_app_user_status ON applications(user_id, status)"),
                ("idx_app_favorite", "CREATE INDEX idx_app_favorite ON applications(user_id, is_favorited)"),
                ("idx_app_job", "CREATE INDEX idx_app_job ON applications(job_id)"),
                ("idx_rec_user", "CREATE INDEX idx_rec_user ON recommendations(user_id, created_at)"),
                ("idx_rec_strategy", "CREATE INDEX idx_rec_strategy ON recommendations(strategy)"),
                ("idx_chat_session", "CREATE INDEX idx_chat_session ON chat_history(session_id, created_at)"),
                ("idx_chat_user", "CREATE INDEX idx_chat_user ON chat_history(user_id)"),
                ("idx_task_status", "CREATE INDEX idx_task_status ON crawl_tasks(status)"),
                ("idx_task_source", "CREATE INDEX idx_task_source ON crawl_tasks(source_id)"),
            ]
            for idx_name, idx_sql in index_sqls:
                try:
                    self.cursor.execute(idx_sql)
                except Exception:
                    pass  # 索引已存在，忽略
        else:
            # SQLite支持CREATE INDEX IF NOT EXISTS
            sqlite_indexes = [
                "idx_jobs_name ON jobs(name)",
                "idx_skills_name ON skills(name)",
                "idx_skills_category ON skills(category)",
                "idx_relations_source ON relations(source_name)",
                "idx_relations_target ON relations(target_name)",
                "idx_messages_session ON messages(session_id)",
                "idx_agent_exec_request ON agent_executions(request_id)",
                "idx_agent_exec_session ON agent_executions(session_id)",
                "idx_skill_taxonomy_industry ON skill_taxonomy(industry)",
                "idx_sessions_user_id ON sessions_db(user_id)",
                "idx_user_quotas_user_date ON user_quotas(user_id, quota_date)",
                "idx_industry_parent ON industries(parent_id)",
                "idx_resume_user ON resumes(user_id)",
                "idx_resume_status ON resumes(parse_status)",
                "idx_resume_city ON resumes(city)",
                "idx_rs_resume ON resume_skills(resume_id)",
                "idx_rs_skill ON resume_skills(skill_id)",
                "idx_rexp_resume ON resume_experiences(resume_id)",
                "idx_redu_resume ON resume_educations(resume_id)",
                "idx_company_industry ON companies(industry_code)",
                "idx_company_city ON companies(city)",
                "idx_job_company ON jobs(company_id)",
                "idx_job_city ON jobs(city)",
                "idx_job_status ON jobs(status)",
                "idx_job_salary ON jobs(salary_min, salary_max)",
                "idx_js_job ON job_skills(job_id)",
                "idx_js_skill ON job_skills(skill_id)",
                "idx_app_user_status ON applications(user_id, status)",
                "idx_app_favorite ON applications(user_id, is_favorited)",
                "idx_app_job ON applications(job_id)",
                "idx_rec_user ON recommendations(user_id, created_at)",
                "idx_rec_strategy ON recommendations(strategy)",
                "idx_chat_session ON chat_history(session_id, created_at)",
                "idx_chat_user ON chat_history(user_id)",
                "idx_task_status ON crawl_tasks(status)",
                "idx_task_source ON crawl_tasks(source_id)",
            ]
            for idx in sqlite_indexes:
                try:
                    self.cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx}")
                except Exception:
                    pass

        self.conn.commit()
        logger.info("数据表创建完成")

    # ========== 岗位操作 ==========

    def create_job(self, job: JobEntity) -> int:
        """创建岗位"""
        # 自动生成 job_code
        if not job.job_code:
            import uuid
            job.job_code = f"J_{uuid.uuid4().hex[:12]}"
        self.cursor.execute(self._q("""
            INSERT INTO jobs (job_code, company_id, name, category, department, city, district,
                experience_req, education_req, description, description_text, requirements,
                salary_range, salary_min, salary_max, salary_unit, salary_months, job_type,
                location, source, source_url, source_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (job.job_code, job.company_id, job.name, job.category, job.department,
              job.city, job.district, job.experience_req, job.education_req,
              job.description, job.description_text, job.requirements,
              job.salary_range, job.salary_min, job.salary_max, job.salary_unit,
              job.salary_months, job.job_type, job.location, job.source,
              job.source_url, job.source_id, job.status))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_job(self, job_id: int) -> Optional[Dict]:
        """获取岗位"""
        self.cursor.execute(self._q("SELECT * FROM jobs WHERE id = ?"), (job_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def search_jobs(self, keyword: str = "", category: str = "", city: str = "",
                     status: str = "", limit: int = 100) -> List[Dict]:
        """搜索岗位"""
        try:
            sql = "SELECT * FROM jobs WHERE is_deleted = 0"
            params = []

            # 业务主库 jobs 列: title(非 name)/description/city/status..., 无 category;
            # category 兼容入参但主库无此列故不使用。
            if keyword:
                sql += " AND (title LIKE ? OR description LIKE ?)"
                params.extend([f"%{keyword}%", f"%{keyword}%"])

            if city:
                sql += " AND city = ?"
                params.append(city)

            if status:
                sql += " AND status = ?"
                params.append(status)

            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            self.cursor.execute(self._q(sql), params)
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            # 主表 schema 由主后端维护, 个别差异列导致查询失败时降级空结果, 不阻断会话
            import logging
            logging.getLogger("db_service").warning(f"search_jobs 查询失败(降级): {e}")
            return []

    def search_job_openings(self, keyword: str = "", city: str = "",
                            job_type: str = "", limit: int = 8) -> List[Dict]:
        """检索真实在招岗位(带公司名/薪资/要求), 供 AI 顾问引用主库数据作答

        JOIN 主库 companies 补公司名; 列名严格对应当前 jobhunter schema:
        jobs(title/city/salary_*/experience_req/education_req/job_type/description),
        companies(name/industry_code)。
        """
        try:
            sql = ("SELECT j.id, j.title, j.city, j.district, j.salary_min, j.salary_max, "
                   "j.salary_unit, j.salary_months, j.experience_req, j.education_req, "
                   "j.job_type, j.description, c.name AS company, c.industry_code "
                   "FROM jobs j LEFT JOIN companies c ON j.company_id = c.id "
                   "WHERE j.is_deleted = 0")
            params = []
            if keyword:
                sql += " AND (j.title LIKE ? OR j.description LIKE ?)"
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            if city:
                sql += " AND j.city = ?"
                params.append(city)
            if job_type:
                sql += " AND j.job_type = ?"
                params.append(job_type)
            sql += " ORDER BY j.created_at DESC LIMIT ?"
            params.append(limit)
            self.cursor.execute(self._q(sql), params)
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            import logging
            logging.getLogger("db_service").warning(f"search_job_openings 查询失败(降级): {e}")
            return []

    def get_job_openings_summary(self, keyword: str = "", top: int = 5) -> Dict[str, Any]:
        """主库在招岗位口径统计(供 AI 顾问报告/趋势回答引用并标注来源)。

        keyword 非空时按 title/description 命中统计; 空则统计全库在招。
        返回: {keyword, total_openings, city_top:[{city,count}], sample_titles:[...]}
        """
        out: Dict[str, Any] = {"keyword": keyword, "total_openings": 0, "city_top": [], "sample_titles": []}
        try:
            base = "FROM jobs WHERE is_deleted = 0"
            kw_sql, kw_params = "", []
            if keyword:
                kw_sql = " AND (title LIKE ? OR description LIKE ?)"
                kw_params = [f"%{keyword}%", f"%{keyword}%"]
            self.cursor.execute(self._q("SELECT COUNT(*) AS c " + base + kw_sql), kw_params)
            row = self.cursor.fetchone()
            out["total_openings"] = int(row["c"]) if row and row["c"] is not None else 0
            self.cursor.execute(
                self._q("SELECT city, COUNT(*) AS c " + base + kw_sql +
                        " AND city IS NOT NULL AND city != '' GROUP BY city ORDER BY c DESC LIMIT ?"),
                kw_params + [top])
            out["city_top"] = [
                {"city": r["city"], "count": int(r["c"])}
                for r in self.cursor.fetchall()
            ]
            if keyword:
                self.cursor.execute(
                    self._q("SELECT title " + base + kw_sql + " ORDER BY created_at DESC LIMIT 5"),
                    kw_params)
                out["sample_titles"] = [r["title"] for r in self.cursor.fetchall()]
        except Exception as e:
            import logging
            logging.getLogger("db_service").warning(f"get_job_openings_summary 查询失败(降级): {e}")
        return out

    # ========== llm 运行时配置项(model_config 表) ==========

    def get_runtime_setting(self, key: str) -> Optional[str]:
        """读取 llm 运行时配置(如 admin_default_model)。表不存在/失败返回 None, 不抛错。"""
        try:
            self.cursor.execute(self._q("SELECT value FROM model_config WHERE config_key = ?"), (key,))
            row = self.cursor.fetchone()
            return row["value"] if row else None
        except Exception as e:
            import logging
            logging.getLogger("db_service").debug(f"get_runtime_setting({key}) 失败: {e}")
            return None

    def set_runtime_setting(self, key: str, value: str) -> bool:
        """写入 llm 运行时配置(upsert)。失败返回 False。"""
        try:
            if self.use_mysql:
                self.cursor.execute(self._q("""
                    INSERT INTO model_config (config_key, value, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE value = VALUES(value), updated_at = CURRENT_TIMESTAMP
                """), (key, value))
            else:
                self.cursor.execute(self._q("""
                    INSERT INTO model_config (config_key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(config_key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """), (key, value))
            self.conn.commit()
            return True
        except Exception as e:
            import logging
            logging.getLogger("db_service").warning(f"set_runtime_setting({key}) 失败: {e}")
            return False

    # ========== 技能操作 ==========

    def create_skill(self, skill: SkillEntity) -> int:
        """创建技能"""
        # 自动生成 skill_code
        if not skill.skill_code:
            import uuid
            skill.skill_code = f"SK_{uuid.uuid4().hex[:12]}"
        # 合并后业务表归主后端维护: skills 在 jobhunter 无 description/level/related_jobs 列,
        # 只插两 schema 共有列(skill_code/name/alias/category/is_hot), 保证可移植。
        self.cursor.execute(self._q("""
            INSERT INTO skills (skill_code, name, alias, category, is_hot)
            VALUES (?, ?, ?, ?, ?)
        """), (skill.skill_code, skill.name, skill.alias, skill.category, skill.is_hot))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_skill(self, skill_id: int) -> Optional[Dict]:
        """获取技能"""
        self.cursor.execute(self._q("SELECT * FROM skills WHERE id = ?"), (skill_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def search_skills(self, keyword: str = "", category: str = "", limit: int = 100) -> List[Dict]:
        """搜索技能"""
        sql = "SELECT * FROM skills WHERE 1=1"
        params = []

        if keyword:
            # 业务主库 skills 无 description 列(两 schema 共有 name/alias), 兼容检索
            sql += " AND (name LIKE ? OR alias LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 关系操作 ==========

    def create_relation(self, relation: CompetencyRelation) -> int:
        """创建关系"""
        self.cursor.execute(self._q("""
            INSERT INTO relations (source_type, source_name, target_type, target_name, relation_type, weight)
            VALUES (?, ?, ?, ?, ?, ?)
        """), (relation.source_type, relation.source_name, relation.target_type,
              relation.target_name, relation.relation_type, relation.weight))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_relations(self, source_name: str = "", target_name: str = "",
                     relation_type: str = "", limit: int = 100) -> List[Dict]:
        """获取关系"""
        sql = "SELECT * FROM relations WHERE 1=1"
        params = []

        if source_name:
            sql += " AND source_name = ?"
            params.append(source_name)

        if target_name:
            sql += " AND target_name = ?"
            params.append(target_name)

        if relation_type:
            sql += " AND relation_type = ?"
            params.append(relation_type)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    def get_job_skills(self, job_name: str) -> List[Dict]:
        """获取岗位所需技能"""
        self.cursor.execute(self._q("""
            SELECT r.*, s.* FROM relations r
            LEFT JOIN skills s ON r.target_name = s.name
            WHERE r.source_name = ? AND r.relation_type = 'requires'
        """), (job_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 用户操作 ==========

    def create_user(self, username: str, password_hash: str, email: str = "",
                    phone: str = "", nickname: str = "", industry: str = "",
                    role: str = "job_seeker") -> int:
        """创建用户"""
        # 自动生成 user_code
        import uuid
        user_code = f"U_{uuid.uuid4().hex[:12]}"
        self.cursor.execute(self._q("""
            INSERT INTO users (user_code, username, phone, email, password_hash, nickname, industry, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (user_code, username, phone, email, password_hash, nickname, industry, role))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名获取用户"""
        self.cursor.execute(self._q("SELECT * FROM users WHERE username = ?"), (username,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据ID获取用户"""
        self.cursor.execute(self._q("SELECT * FROM users WHERE id = ?"), (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_user(self, user_id: int, email: str = "", industry: str = "",
                    role: str = "") -> bool:
        """更新用户信息"""
        try:
            updates = []
            params = []
            if email:
                updates.append("email = ?")
                params.append(email)
            if industry:
                updates.append("industry = ?")
                params.append(industry)
            if role:
                updates.append("role = ?")
                params.append(role)
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            self.cursor.execute(
                self._q(f"UPDATE users SET {', '.join(updates)} WHERE id = ?"),
                params
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            return False

    # ========== 用户配额操作 ==========

    def list_sessions_by_user(self, user_id: int, limit: int = 100) -> List[Dict]:
        """列出指定用户的会话"""
        try:
            self.cursor.execute(
                self._q("SELECT * FROM sessions_db WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?"),
                (user_id, limit)
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"列出用户会话失败: {e}")
            return []

    def get_user_daily_usage(self, user_id: int, date: str = "") -> Optional[Dict]:
        """获取用户每日使用量"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        try:
            self.cursor.execute(self._q(
                "SELECT * FROM user_quotas WHERE user_id = ? AND quota_date = ?"
            ), (user_id, date))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取用户配额失败: {e}")
            return None

    def upsert_user_usage(self, user_id: int, date: str, daily_calls: int = 0,
                          daily_tokens: int = 0) -> bool:
        """插入或更新用户每日使用量"""
        try:
            if self.use_mysql:
                self.cursor.execute(self._q("""
                    INSERT INTO user_quotas (user_id, daily_calls, daily_tokens, quota_date, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        daily_calls = VALUES(daily_calls),
                        daily_tokens = VALUES(daily_tokens),
                        updated_at = CURRENT_TIMESTAMP
                """), (user_id, daily_calls, daily_tokens, date))
            else:
                self.cursor.execute(self._q("""
                    INSERT OR REPLACE INTO user_quotas (user_id, daily_calls, daily_tokens, quota_date, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """), (user_id, daily_calls, daily_tokens, date))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新用户配额失败: {e}")
            return False

    # ========== 统计 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {"database": "MySQL" if self.use_mysql else "SQLite"}

        # 旧表统计
        for table in ["jobs", "skills", "relations", "users", "sessions_db",
                       "messages", "agent_executions", "evaluations", "metrics"]:
            try:
                self.cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = self.cursor.fetchone()["count"]
            except Exception:
                stats[table] = 0

        # 新标准表统计
        for table in ["industries", "companies", "resumes", "resume_skills",
                       "resume_experiences", "resume_educations", "job_skills",
                       "applications", "recommendations", "chat_history",
                       "crawl_sources", "crawl_tasks"]:
            try:
                self.cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = self.cursor.fetchone()["count"]
            except Exception:
                stats[table] = 0

        return stats

    # ========== 会话持久化操作 ==========

    def create_session_db(self, session_id: str, industry: str = "", role: str = "",
                          title: str = "", user_id: int = 0) -> bool:
        """创建会话记录到数据库"""
        try:
            # MySQL不支持INSERT OR REPLACE，使用INSERT ... ON DUPLICATE KEY UPDATE
            if self.use_mysql:
                self.cursor.execute(self._q("""
                    INSERT INTO sessions_db (id, user_id, title, industry_context, role, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        industry_context = VALUES(industry_context),
                        role = VALUES(role),
                        updated_at = CURRENT_TIMESTAMP
                """), (session_id, user_id, title, industry, role))
            else:
                self.cursor.execute(self._q("""
                    INSERT OR REPLACE INTO sessions_db (id, user_id, title, industry_context, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """), (session_id, user_id, title, industry, role))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"创建会话记录失败: {e}")
            return False

    def get_session_db(self, session_id: str) -> Optional[Dict]:
        """从数据库获取会话"""
        try:
            self.cursor.execute(self._q("SELECT * FROM sessions_db WHERE id = ?"), (session_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取会话记录失败: {e}")
            return None

    def update_session_db(self, session_id: str, industry: str = "", role: str = "") -> bool:
        """更新会话记录"""
        try:
            updates = []
            params = []
            if industry:
                updates.append("industry_context = ?")
                params.append(industry)
            if role:
                updates.append("role = ?")
                params.append(role)
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(session_id)
            self.cursor.execute(
                self._q(f"UPDATE sessions_db SET {', '.join(updates)} WHERE id = ?"),
                params
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新会话记录失败: {e}")
            return False

    def delete_session_db(self, session_id: str) -> bool:
        """从数据库删除会话"""
        try:
            self.cursor.execute(self._q("DELETE FROM sessions_db WHERE id = ?"), (session_id,))
            # 同时删除该会话的消息
            self.cursor.execute(self._q("DELETE FROM messages WHERE session_id = ?"), (session_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除会话记录失败: {e}")
            return False

    def list_sessions_db(self, limit: int = 100) -> List[Dict]:
        """列出数据库中的所有会话"""
        try:
            self.cursor.execute(
                self._q("SELECT * FROM sessions_db ORDER BY updated_at DESC LIMIT ?"),
                (limit,)
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"列出会话记录失败: {e}")
            return []

    # ========== 消息操作 ==========

    def create_message(self, session_id: str, role: str, content: str,
                       intent: str = "", agent_tasks: str = "", latency_ms: float = 0,
                       recommended_jobs: Optional[str] = None) -> int:
        """创建消息记录; recommended_jobs 为结构化岗位推荐(JSON文本), 供历史回放渲染卡片"""
        self.cursor.execute(self._q("""
            INSERT INTO messages (session_id, role, content, intent, agent_tasks, latency_ms, recommended_jobs)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (session_id, role, content, intent, agent_tasks, latency_ms, recommended_jobs))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取会话消息"""
        self.cursor.execute(
            self._q("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?"),
            (session_id, limit)
        )
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== Agent执行记录 ==========

    def create_agent_execution(self, request_id: str, session_id: str, intent: str,
                                task_type: str, model_used: str = "",
                                input_tokens: int = 0, output_tokens: int = 0,
                                cost: float = 0, latency_ms: float = 0,
                                status: str = "pending", retry_count: int = 0,
                                error_message: str = "") -> int:
        """创建Agent执行记录"""
        self.cursor.execute(self._q("""
            INSERT INTO agent_executions (request_id, session_id, intent, task_type,
                model_used, input_tokens, output_tokens, cost, latency_ms, status,
                retry_count, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (request_id, session_id, intent, task_type, model_used,
              input_tokens, output_tokens, cost, latency_ms, status,
              retry_count, error_message))
        self.conn.commit()
        return self.cursor.lastrowid

    def list_agent_executions(self, limit: int = 1000) -> List[Dict]:
        """查询最近的Agent执行记录（用于追踪恢复）"""
        self.cursor.execute(self._q("""
            SELECT id, request_id, session_id, intent, task_type, model_used,
                   input_tokens, output_tokens, cost, latency_ms, status,
                   retry_count, error_message, created_at
            FROM agent_executions
            ORDER BY id DESC
            LIMIT ?
        """), (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def update_agent_execution(self, exec_id: int, status: str = "",
                                input_tokens: int = 0, output_tokens: int = 0,
                                cost: float = 0, latency_ms: float = 0,
                                retry_count: int = 0, error_message: str = ""):
        """更新Agent执行记录"""
        updates = []
        params = []
        if status:
            updates.append("status = ?")
            params.append(status)
        if input_tokens:
            updates.append("input_tokens = ?")
            params.append(input_tokens)
        if output_tokens:
            updates.append("output_tokens = ?")
            params.append(output_tokens)
        if cost:
            updates.append("cost = ?")
            params.append(cost)
        if latency_ms:
            updates.append("latency_ms = ?")
            params.append(latency_ms)
        if retry_count:
            updates.append("retry_count = ?")
            params.append(retry_count)
        if error_message:
            updates.append("error_message = ?")
            params.append(error_message)

        if not updates:
            return

        params.append(exec_id)
        self.cursor.execute(
            self._q(f"UPDATE agent_executions SET {', '.join(updates)} WHERE id = ?"),
            params
        )
        self.conn.commit()

    # ========== 评估操作 ==========

    def create_evaluation(self, message_id: int, user_id: int = 0,
                          auto_score: float = 0, user_score: float = 0,
                          user_feedback: str = "", intent_accuracy: float = 0,
                          task_completion: float = 0, response_quality: float = 0) -> int:
        """创建评估记录"""
        self.cursor.execute(self._q("""
            INSERT INTO evaluations (message_id, user_id, auto_score, user_score,
                user_feedback, intent_accuracy, task_completion, response_quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (message_id, user_id, auto_score, user_score, user_feedback,
              intent_accuracy, task_completion, response_quality))
        self.conn.commit()
        return self.cursor.lastrowid

    # ========== 监控指标操作 ==========

    def create_metric(self, metric_name: str, metric_value: float,
                      labels: Optional[Dict] = None) -> int:
        """创建监控指标记录"""
        labels_json = json.dumps(labels, ensure_ascii=False) if labels else "{}"
        self.cursor.execute(self._q("""
            INSERT INTO metrics (metric_name, metric_value, labels_json)
            VALUES (?, ?, ?)
        """), (metric_name, metric_value, labels_json))
        self.conn.commit()
        return self.cursor.lastrowid

    def query_metrics(self, metric_name: str = "", limit: int = 100,
                      since: str = "") -> List[Dict]:
        """查询监控指标"""
        sql = "SELECT * FROM metrics WHERE 1=1"
        params = []

        if metric_name:
            sql += " AND metric_name = ?"
            params.append(metric_name)

        if since:
            sql += " AND timestamp >= ?"
            params.append(since)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    def aggregate_metrics(self, metric_name: str, interval: str = "hour") -> List[Dict]:
        """
        聚合监控指标

        Args:
            metric_name: 指标名称
            interval: 聚合间隔 (hour/day)

        Returns:
            聚合结果列表
        """
        if self.use_mysql:
            if interval == "day":
                date_format = "%Y-%m-%d"
            else:
                date_format = "%Y-%m-%d %H:00"
            sql = f"""
                SELECT
                    DATE_FORMAT(timestamp, %s) as period,
                    COUNT(*) as count,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value,
                    SUM(metric_value) as sum_value
                FROM metrics
                WHERE metric_name = %s
                GROUP BY period
                ORDER BY period DESC
                LIMIT 100
            """
            self.cursor.execute(sql, (date_format, metric_name))
        else:
            if interval == "day":
                strftime_fmt = "%Y-%m-%d"
            else:
                strftime_fmt = "%Y-%m-%d %H:00"
            self.cursor.execute(f"""
                SELECT
                    strftime('{strftime_fmt}', timestamp) as period,
                    COUNT(*) as count,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value,
                    SUM(metric_value) as sum_value
                FROM metrics
                WHERE metric_name = ?
                GROUP BY period
                ORDER BY period DESC
                LIMIT 100
            """, (metric_name,))

        return [dict(row) for row in self.cursor.fetchall()]

    def cleanup_old_metrics(self, days: int = 30) -> int:
        """清理过期监控指标"""
        self.cursor.execute(self._q(
            "DELETE FROM metrics WHERE timestamp < datetime('now', ?)"
        ), (f"-{days} days",))
        deleted = self.cursor.rowcount
        self.conn.commit()
        return deleted

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")

    # ========== 字典层：行业操作 ==========

    def create_industry(self, industry: IndustryEntity) -> int:
        """创建行业"""
        self.cursor.execute(self._q("""
            INSERT INTO industries (code, name, parent_id, level)
            VALUES (?, ?, ?, ?)
        """), (industry.code, industry.name, industry.parent_id, industry.level))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_industry(self, code: str) -> Optional[Dict]:
        """根据编码获取行业"""
        self.cursor.execute(self._q("SELECT * FROM industries WHERE code = ?"), (code,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def search_industries(self, parent_id: Optional[int] = None, level: int = 0) -> List[Dict]:
        """查询行业（可按父级/层级过滤）"""
        sql = "SELECT * FROM industries WHERE 1=1"
        params = []
        if parent_id is not None:
            sql += " AND parent_id = ?"
            params.append(parent_id)
        if level:
            sql += " AND level = ?"
            params.append(level)
        sql += " ORDER BY level, id"
        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 主体层：公司操作 ==========

    def create_company(self, company: CompanyEntity) -> int:
        """创建公司"""
        if not company.company_code:
            import uuid
            company.company_code = f"C_{uuid.uuid4().hex[:12]}"
        self.cursor.execute(self._q("""
            INSERT INTO companies (company_code, name, short_name, industry_code, size, stage,
                city, district, address, logo_url, website, welfare, description, source, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (company.company_code, company.name, company.short_name, company.industry_code,
              company.size, company.stage, company.city, company.district, company.address,
              company.logo_url, company.website, company.welfare, company.description,
              company.source, company.source_url))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_company(self, company_id: int) -> Optional[Dict]:
        """获取公司"""
        self.cursor.execute(self._q("SELECT * FROM companies WHERE id = ? AND is_deleted = 0"), (company_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def search_companies(self, keyword: str = "", city: str = "",
                          industry_code: str = "", limit: int = 100) -> List[Dict]:
        """搜索公司"""
        sql = "SELECT * FROM companies WHERE is_deleted = 0"
        params = []
        if keyword:
            sql += " AND (name LIKE ? OR short_name LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if city:
            sql += " AND city = ?"
            params.append(city)
        if industry_code:
            sql += " AND industry_code = ?"
            params.append(industry_code)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 主体层：简历操作 ==========

    def create_resume(self, resume: ResumeEntity) -> int:
        """创建简历"""
        if not resume.resume_code:
            import uuid
            resume.resume_code = f"R_{uuid.uuid4().hex[:12]}"
        self.cursor.execute(self._q("""
            INSERT INTO resumes (resume_code, user_id, title, name, gender, age, city, phone, email,
                source_type, file_url, parse_status, work_years, education,
                expect_salary_min, expect_salary_max, expect_city, expect_job, overall_score, parsed_raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (resume.resume_code, resume.user_id, resume.title, resume.name, resume.gender,
              resume.age, resume.city, resume.phone, resume.email, resume.source_type,
              resume.file_url, resume.parse_status, resume.work_years, resume.education,
              resume.expect_salary_min, resume.expect_salary_max, resume.expect_city,
              resume.expect_job, resume.overall_score, resume.parsed_raw))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_resume(self, resume_id: int) -> Optional[Dict]:
        """获取简历"""
        self.cursor.execute(self._q("SELECT * FROM resumes WHERE id = ? AND is_deleted = 0"), (resume_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def search_resumes(self, user_id: int = 0, city: str = "",
                        parse_status: str = "", limit: int = 100) -> List[Dict]:
        """搜索简历"""
        sql = "SELECT * FROM resumes WHERE is_deleted = 0"
        params = []
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        if city:
            sql += " AND city = ?"
            params.append(city)
        if parse_status:
            sql += " AND parse_status = ?"
            params.append(parse_status)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    def update_resume_parse_status(self, resume_id: int, parse_status: str,
                                    parse_error: str = "", overall_score: Optional[float] = None) -> bool:
        """更新简历解析状态"""
        try:
            updates = ["parse_status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [parse_status]
            if parse_error:
                updates.append("parse_error = ?")
                params.append(parse_error)
            if overall_score is not None:
                updates.append("overall_score = ?")
                params.append(overall_score)
            params.append(resume_id)
            self.cursor.execute(
                self._q(f"UPDATE resumes SET {', '.join(updates)} WHERE id = ?"),
                params
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新简历解析状态失败: {e}")
            return False

    # ========== 主体层：简历子表操作 ==========

    def create_resume_skill(self, rs: ResumeSkillEntity) -> int:
        """创建简历-技能关联"""
        self.cursor.execute(self._q("""
            INSERT INTO resume_skills (resume_id, skill_id, proficiency, years)
            VALUES (?, ?, ?, ?)
        """), (rs.resume_id, rs.skill_id, rs.proficiency, rs.years))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_resume_skills(self, resume_id: int) -> List[Dict]:
        """获取简历技能（关联skills表）"""
        self.cursor.execute(self._q("""
            SELECT rs.*, s.name as skill_name, s.category as skill_category
            FROM resume_skills rs
            LEFT JOIN skills s ON rs.skill_id = s.id
            WHERE rs.resume_id = ?
        """), (resume_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_user_resume_profile(self, user_id) -> Optional[Dict]:
        """取某用户最新一份已解析简历的画像(读主库 resumes/resume_skills/resume_experiences)。

        供 AI 顾问把求职者真实简历/技能注入 resume_match/skill_gap/learning_path 等场景。
        无简历/出错一律返回 None(不抛异常, 上层降级为用户在对话里的自述)。
        返回: {resume_id, name, city, work_years, education, expect_job, expect_city,
               skills: [{name, category, proficiency, years}],
               experiences: [{company_name, title, start_date, end_date, is_current}]}
        """
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None
        try:
            self.cursor.execute(self._q(
                "SELECT * FROM resumes WHERE user_id = ? AND is_deleted = 0 "
                "AND parse_status = 'done' "
                "ORDER BY is_primary DESC, updated_at DESC LIMIT 1"
            ), (user_id,))
            row = self.cursor.fetchone()
            if not row:
                return None
            resume = dict(row)
            profile: Dict[str, Any] = {
                "resume_id": resume.get("id"),
                "name": resume.get("name"),
                "city": resume.get("city"),
                "work_years": resume.get("work_years"),
                "education": resume.get("education"),
                "expect_job": resume.get("expect_job"),
                "expect_city": resume.get("expect_city"),
                "skills": [],
                "experiences": [],
            }
            for s in self.get_resume_skills(resume["id"]):
                if s.get("skill_name"):
                    profile["skills"].append({
                        "name": s.get("skill_name"),
                        "category": s.get("skill_category"),
                        "proficiency": s.get("proficiency"),
                        "years": s.get("years"),
                    })
            try:
                profile["experiences"] = self.get_resume_experiences(resume["id"])
            except Exception:
                profile["experiences"] = []
            return profile
        except Exception as e:
            logger.warning(f"get_user_resume_profile 失败(降级 None): {e}")
            return None

    def create_resume_experience(self, exp: ResumeExperienceEntity) -> int:
        """创建工作经历"""
        self.cursor.execute(self._q("""
            INSERT INTO resume_experiences (resume_id, company_name, title, start_date, end_date, description, is_current)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (exp.resume_id, exp.company_name, exp.title, exp.start_date,
              exp.end_date, exp.description, exp.is_current))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_resume_experiences(self, resume_id: int) -> List[Dict]:
        """获取工作经历"""
        self.cursor.execute(self._q(
            "SELECT * FROM resume_experiences WHERE resume_id = ? ORDER BY start_date DESC"
        ), (resume_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    def create_resume_education(self, edu: ResumeEducationEntity) -> int:
        """创建教育经历"""
        self.cursor.execute(self._q("""
            INSERT INTO resume_educations (resume_id, school, major, degree, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """), (edu.resume_id, edu.school, edu.major, edu.degree, edu.start_date, edu.end_date))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_resume_educations(self, resume_id: int) -> List[Dict]:
        """获取教育经历"""
        self.cursor.execute(self._q(
            "SELECT * FROM resume_educations WHERE resume_id = ? ORDER BY start_date DESC"
        ), (resume_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 主体层：职位-技能关联 ==========

    def create_job_skill(self, js: JobSkillEntity) -> int:
        """创建职位-技能关联"""
        self.cursor.execute(self._q("""
            INSERT INTO job_skills (job_id, skill_id, is_must, weight)
            VALUES (?, ?, ?, ?)
        """), (js.job_id, js.skill_id, js.is_must, js.weight))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_job_skills_by_job(self, job_id: int) -> List[Dict]:
        """获取职位所需技能（关联skills表）"""
        self.cursor.execute(self._q("""
            SELECT js.*, s.name as skill_name, s.category as skill_category, s.skill_code
            FROM job_skills js
            LEFT JOIN skills s ON js.skill_id = s.id
            WHERE js.job_id = ?
        """), (job_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_job_skills_by_skill(self, skill_id: int, limit: int = 100) -> List[Dict]:
        """反向查询：某技能被多少职位需要"""
        self.cursor.execute(self._q("""
            SELECT js.*, j.name as job_name, j.city
            FROM job_skills js
            LEFT JOIN jobs j ON js.job_id = j.id
            WHERE js.skill_id = ? AND j.is_deleted = 0
            LIMIT ?
        """), (skill_id, limit))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 行为层：投递/收藏操作 ==========

    def create_application(self, app: ApplicationEntity) -> int:
        """创建用户-职位关系（投递/收藏）"""
        self.cursor.execute(self._q("""
            INSERT INTO applications (user_id, job_id, resume_id, status, is_favorited,
                match_score, external_source, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (app.user_id, app.job_id, app.resume_id, app.status, app.is_favorited,
              app.match_score, app.external_source, app.note))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_application(self, user_id: int, job_id: int) -> Optional[Dict]:
        """获取用户对某职位的关系记录"""
        self.cursor.execute(self._q(
            "SELECT * FROM applications WHERE user_id = ? AND job_id = ? AND is_deleted = 0"
        ), (user_id, job_id))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_application_status(self, app_id: int, status: str, note: str = "") -> bool:
        """更新投递进度状态"""
        try:
            updates = ["status = ?", "feedback_at = CURRENT_TIMESTAMP", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]
            if note:
                updates.append("note = ?")
                params.append(note)
            params.append(app_id)
            self.cursor.execute(
                self._q(f"UPDATE applications SET {', '.join(updates)} WHERE id = ?"),
                params
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新投递状态失败: {e}")
            return False

    def toggle_favorite(self, user_id: int, job_id: int, favorited: int = 1) -> bool:
        """切换收藏状态"""
        try:
            existing = self.get_application(user_id, job_id)
            if existing:
                self.cursor.execute(self._q(
                    "UPDATE applications SET is_favorited = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                ), (favorited, existing["id"]))
            else:
                self.cursor.execute(self._q("""
                    INSERT INTO applications (user_id, job_id, is_favorited)
                    VALUES (?, ?, ?)
                """), (user_id, job_id, favorited))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"切换收藏失败: {e}")
            return False

    def list_applications(self, user_id: int, status: str = "",
                           favorited_only: bool = False, limit: int = 100) -> List[Dict]:
        """列出用户的投递/收藏记录"""
        sql = "SELECT a.*, j.name as job_name, j.city, j.salary_min, j.salary_max FROM applications a LEFT JOIN jobs j ON a.job_id = j.id WHERE a.user_id = ? AND a.is_deleted = 0"
        params = [user_id]
        if status:
            sql += " AND a.status = ?"
            params.append(status)
        if favorited_only:
            sql += " AND a.is_favorited = 1"
        sql += " ORDER BY a.updated_at DESC LIMIT ?"
        params.append(limit)
        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 行为层：推荐流水 ==========

    def create_recommendation(self, rec: RecommendationEntity) -> int:
        """创建推荐记录"""
        self.cursor.execute(self._q("""
            INSERT INTO recommendations (user_id, resume_id, job_id, score, reason, strategy, snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (rec.user_id, rec.resume_id, rec.job_id, rec.score, rec.reason, rec.strategy, rec.snapshot))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_recommendations(self, user_id: int, strategy: str = "", limit: int = 100) -> List[Dict]:
        """查询用户推荐历史"""
        sql = "SELECT r.*, j.name as job_name FROM recommendations r LEFT JOIN jobs j ON r.job_id = j.id WHERE r.user_id = ?"
        params = [user_id]
        if strategy:
            sql += " AND r.strategy = ?"
            params.append(strategy)
        sql += " ORDER BY r.created_at DESC LIMIT ?"
        params.append(limit)
        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 行为层：AI对话历史 ==========

    def create_chat_history(self, ch: ChatHistoryEntity) -> int:
        """创建对话历史记录"""
        self.cursor.execute(self._q("""
            INSERT INTO chat_history (user_id, session_id, role, content, tool_calls, tokens)
            VALUES (?, ?, ?, ?, ?, ?)
        """), (ch.user_id, ch.session_id, ch.role, ch.content, ch.tool_calls, ch.tokens))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取会话的对话历史"""
        self.cursor.execute(self._q(
            "SELECT * FROM chat_history WHERE session_id = ? ORDER BY created_at ASC LIMIT ?"
        ), (session_id, limit))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 采集层：爬虫数据源 ==========

    def create_crawl_source(self, source: CrawlSourceEntity) -> int:
        """创建爬虫数据源"""
        self.cursor.execute(self._q("""
            INSERT INTO crawl_sources (name, type, base_url, enabled, config)
            VALUES (?, ?, ?, ?, ?)
        """), (source.name, source.type, source.base_url, source.enabled, source.config))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_crawl_source(self, name: str, type: str = "job") -> Optional[Dict]:
        """获取数据源"""
        self.cursor.execute(self._q(
            "SELECT * FROM crawl_sources WHERE name = ? AND type = ?"
        ), (name, type))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def list_crawl_sources(self, enabled_only: bool = False) -> List[Dict]:
        """列出所有数据源"""
        sql = "SELECT * FROM crawl_sources"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY created_at DESC"
        self.cursor.execute(self._q(sql))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========== 采集层：爬虫任务 ==========

    def create_crawl_task(self, task: CrawlTaskEntity) -> int:
        """创建爬虫任务"""
        if not task.task_code:
            import uuid
            task.task_code = f"T_{uuid.uuid4().hex[:12]}"
        self.cursor.execute(self._q("""
            INSERT INTO crawl_tasks (source_id, task_code, keyword, city, status, total)
            VALUES (?, ?, ?, ?, ?, ?)
        """), (task.source_id, task.task_code, task.keyword, task.city, task.status, task.total))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_crawl_task(self, task_code: str) -> Optional[Dict]:
        """获取爬虫任务"""
        self.cursor.execute(self._q("SELECT * FROM crawl_tasks WHERE task_code = ?"), (task_code,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_crawl_task_status(self, task_id: int, status: str,
                                  succeeded: int = 0, failed: int = 0, error_msg: str = "") -> bool:
        """更新爬虫任务状态"""
        try:
            updates = ["status = ?"]
            params = [status]
            if succeeded:
                updates.append("succeeded = ?")
                params.append(succeeded)
            if failed:
                updates.append("failed = ?")
                params.append(failed)
            if error_msg:
                updates.append("error_msg = ?")
                params.append(error_msg)
            if status == "running":
                updates.append("start_at = CURRENT_TIMESTAMP")
            elif status in ("success", "failed"):
                updates.append("end_at = CURRENT_TIMESTAMP")
            params.append(task_id)
            self.cursor.execute(
                self._q(f"UPDATE crawl_tasks SET {', '.join(updates)} WHERE id = ?"),
                params
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新爬虫任务失败: {e}")
            return False

    def list_crawl_tasks(self, status: str = "", source_id: int = 0, limit: int = 100) -> List[Dict]:
        """列出爬虫任务"""
        sql = "SELECT * FROM crawl_tasks WHERE 1=1"
        params = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if source_id:
            sql += " AND source_id = ?"
            params.append(source_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        self.cursor.execute(self._q(sql), params)
        return [dict(row) for row in self.cursor.fetchall()]


# 单例
_db_service: Any = None


def get_db_service() -> DatabaseService:
    """获取数据库服务单例"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
