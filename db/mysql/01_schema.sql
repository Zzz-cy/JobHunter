-- ============================================================
-- JobHunter 智能招聘平台 - MySQL 主库 Schema
-- 设计原则：
--   1. MySQL 只存权威源(OLTP)，全文检索/聚合走 ES
--   2. 业务主键 BIGINT 自增，对外暴露 *_code
--   3. 软删除(is_deleted) + 时间戳(created_at/updated_at)
--   4. 字典表(skills/industries)与业务表多对多解耦
--   5. 爬虫数据用 *_source 标记来源，便于回溯
-- ============================================================

CREATE DATABASE IF NOT EXISTS jobhunter
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
USE jobhunter;

-- ---------- 1. 字典表 ----------
-- 技能字典：与 Neo4j 中的 Skill 节点一一对应
CREATE TABLE IF NOT EXISTS `skills` (
    `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `skill_code`   VARCHAR(64)  NOT NULL COMMENT '对外编码(雪花/UUID)',
    `name`         VARCHAR(128) NOT NULL COMMENT '标准化技能名(e.g. Python)',
    `alias`        VARCHAR(255) DEFAULT NULL COMMENT '别称逗号分隔(e.g. py,Python3)',
    `category`     VARCHAR(64)  DEFAULT NULL COMMENT '分类:语言/框架/工具/软技能',
    `is_hot`       TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否热门技能',
    `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_skill_code` (`skill_code`),
    UNIQUE KEY `uk_skill_name` (`name`),
    KEY `idx_skill_category` (`category`),
    KEY `idx_skill_hot` (`is_hot`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能标准化字典';

-- 行业 / 城市字典
CREATE TABLE IF NOT EXISTS `industries` (
    `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `code`       VARCHAR(32)  NOT NULL,
    `name`       VARCHAR(64)  NOT NULL,
    `parent_id`  INT UNSIGNED DEFAULT NULL,
    `level`      TINYINT      NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_industry_code` (`code`),
    KEY `idx_industry_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行业层级字典';

-- ---------- 2. 用户 & 简历 ----------
CREATE TABLE IF NOT EXISTS `users` (
    `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_code`     VARCHAR(64)  NOT NULL,
    `phone`         VARCHAR(20)  DEFAULT NULL COMMENT '手机号(加密存储)',
    `email`         VARCHAR(128) DEFAULT NULL,
    `password_hash` VARCHAR(128) NOT NULL,
    `nickname`      VARCHAR(64)  DEFAULT NULL,
    `avatar_url`    VARCHAR(512) DEFAULT NULL,
    `role`          VARCHAR(16)  NOT NULL DEFAULT 'user' COMMENT 'user/admin',
    `last_login_at` DATETIME     DEFAULT NULL,
    `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0,
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_code` (`user_code`),
    UNIQUE KEY `uk_user_phone` (`phone`),
    UNIQUE KEY `uk_user_email` (`email`),
    KEY `idx_user_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户';

-- 简历主表：只存元信息，详细经历分表存
CREATE TABLE IF NOT EXISTS `resumes` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `resume_code`    VARCHAR(64)  NOT NULL,
    `user_id`        BIGINT UNSIGNED NOT NULL,
    `name`           VARCHAR(64)  NOT NULL COMMENT '姓名',
    `gender`         TINYINT      DEFAULT NULL COMMENT '0男 1女',
    `age`            INT          DEFAULT NULL,
    `city`           VARCHAR(64)  DEFAULT NULL COMMENT '期望/现居城市',
    `phone`          VARCHAR(20)  DEFAULT NULL,
    `email`          VARCHAR(128) DEFAULT NULL,
    `source_type`    VARCHAR(16)  NOT NULL DEFAULT 'pdf' COMMENT 'pdf/image/manual',
    `file_url`       VARCHAR(512) DEFAULT NULL COMMENT '原始文件URL',
    `parse_status`   VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending/parsing/done/failed',
    `parse_error`    VARCHAR(512) DEFAULT NULL,
    `work_years`     INT          DEFAULT NULL COMMENT '总工作年限',
    `education`      VARCHAR(16)  DEFAULT NULL COMMENT '最高学历',
    `expect_salary_min` INT       DEFAULT NULL,
    `expect_salary_max` INT       DEFAULT NULL,
    `expect_city`    VARCHAR(64)  DEFAULT NULL,
    `expect_job`     VARCHAR(128) DEFAULT NULL COMMENT '期望岗位',
    `overall_score`  DECIMAL(5,2) DEFAULT NULL COMMENT '简历完整度评分0-100',
    `parsed_raw`     JSON         DEFAULT NULL COMMENT 'OCR/解析原始结果',
    `is_deleted`     TINYINT(1)   NOT NULL DEFAULT 0,
    `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_resume_code` (`resume_code`),
    KEY `idx_resume_user` (`user_id`),
    KEY `idx_resume_status` (`parse_status`),
    KEY `idx_resume_city` (`city`),
    KEY `idx_resume_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历主表';

-- 简历技能关联(多对多 + 熟练度)
CREATE TABLE IF NOT EXISTS `resume_skills` (
    `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `resume_id`   BIGINT UNSIGNED NOT NULL,
    `skill_id`    BIGINT UNSIGNED NOT NULL,
    `proficiency` TINYINT NOT NULL DEFAULT 3 COMMENT '1-5熟练度',
    `years`       DECIMAL(4,1) DEFAULT NULL COMMENT '使用年限',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_resume_skill` (`resume_id`,`skill_id`),
    KEY `idx_rs_skill` (`skill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历-技能关联';

-- 工作经历
CREATE TABLE IF NOT EXISTS `resume_experiences` (
    `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `resume_id`    BIGINT UNSIGNED NOT NULL,
    `company_name` VARCHAR(128) NOT NULL,
    `title`        VARCHAR(128) DEFAULT NULL COMMENT '职位',
    `start_date`   DATE DEFAULT NULL,
    `end_date`     DATE DEFAULT NULL,
    `description`  TEXT DEFAULT NULL,
    `is_current`   TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    KEY `idx_rexp_resume` (`resume_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历工作经历';

-- 教育经历
CREATE TABLE IF NOT EXISTS `resume_educations` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `resume_id`  BIGINT UNSIGNED NOT NULL,
    `school`     VARCHAR(128) NOT NULL,
    `major`      VARCHAR(128) DEFAULT NULL,
    `degree`     VARCHAR(32)  DEFAULT NULL COMMENT '大专/本科/硕士/博士',
    `start_date` DATE DEFAULT NULL,
    `end_date`   DATE DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_redu_resume` (`resume_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历教育经历';

-- ---------- 3. 公司 & 职位 ----------
CREATE TABLE IF NOT EXISTS `companies` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `company_code`   VARCHAR(64)  NOT NULL,
    `name`           VARCHAR(128) NOT NULL,
    `short_name`     VARCHAR(64)  DEFAULT NULL,
    `industry_code`  VARCHAR(32)  DEFAULT NULL COMMENT '关联industries.code',
    `size`           VARCHAR(32)  DEFAULT NULL COMMENT '0-20/20-99/...',
    `stage`          VARCHAR(32)  DEFAULT NULL COMMENT '融资阶段',
    `city`           VARCHAR(64)  DEFAULT NULL,
    `district`       VARCHAR(64)  DEFAULT NULL,
    `address`        VARCHAR(255) DEFAULT NULL,
    `logo_url`       VARCHAR(512) DEFAULT NULL,
    `website`        VARCHAR(255) DEFAULT NULL,
    `welfare`        JSON         DEFAULT NULL COMMENT '["六险一金","免费餐"]',
    `description`    TEXT         DEFAULT NULL,
    `source`         VARCHAR(32)  NOT NULL DEFAULT 'boss' COMMENT 'boss/liepin/official',
    `source_url`     VARCHAR(512) DEFAULT NULL,
    `is_deleted`     TINYINT(1)   NOT NULL DEFAULT 0,
    `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_company_code` (`company_code`),
    UNIQUE KEY `uk_company_name_source` (`name`,`source`),
    KEY `idx_company_industry` (`industry_code`),
    KEY `idx_company_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公司信息';

-- 职位主表（爬虫核心产物）
CREATE TABLE IF NOT EXISTS `jobs` (
    `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `job_code`        VARCHAR(64)  NOT NULL,
    `company_id`      BIGINT UNSIGNED DEFAULT NULL,
    `title`           VARCHAR(255) NOT NULL COMMENT '职位名',
    `department`      VARCHAR(128) DEFAULT NULL,
    `city`            VARCHAR(64)  DEFAULT NULL,
    `district`        VARCHAR(64)  DEFAULT NULL,
    `experience_req`  VARCHAR(32)  DEFAULT NULL COMMENT '经验要求 3-5年',
    `education_req`   VARCHAR(32)  DEFAULT NULL COMMENT '学历要求',
    `salary_min`      INT          DEFAULT NULL COMMENT '月薪下限(K*1000)',
    `salary_max`      INT          DEFAULT NULL,
    `salary_unit`     VARCHAR(8)   DEFAULT 'month' COMMENT 'month/day/year',
    `salary_months`   TINYINT      DEFAULT NULL COMMENT '13/14薪',
    `job_type`        VARCHAR(16)  DEFAULT 'full' COMMENT 'full/part/intern',
    `description`     TEXT         DEFAULT NULL COMMENT 'JD正文(含HTML)',
    `description_text` TEXT        DEFAULT NULL COMMENT 'JD纯文本(给ES/向量)',
    `highlights`      JSON         DEFAULT NULL COMMENT '["弹性工作","股票期权"]',
    `advantage`       TEXT         DEFAULT NULL COMMENT '岗位亮点',
    `work_address`    VARCHAR(255) DEFAULT NULL,
    `longitude`       DECIMAL(10,7) DEFAULT NULL,
    `latitude`        DECIMAL(10,7) DEFAULT NULL,
    `source`          VARCHAR(32)  NOT NULL DEFAULT 'boss',
    `source_url`      VARCHAR(512) NOT NULL COMMENT '原始URL，供用户跳转',
    `source_id`       VARCHAR(64)  DEFAULT NULL COMMENT '平台原始ID，用于去重',
    `crawl_batch`     VARCHAR(32)  DEFAULT NULL COMMENT '采集批次号',
    `status`          VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT 'active/closed/expired',
    `publish_at`      DATETIME     DEFAULT NULL,
    `crawl_at`        DATETIME     DEFAULT NULL,
    `quality_score`   DECIMAL(4,2) DEFAULT NULL COMMENT '数据质量评分0-100',
    `is_deleted`      TINYINT(1)   NOT NULL DEFAULT 0,
    `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_job_code` (`job_code`),
    UNIQUE KEY `uk_job_source` (`source`,`source_id`),
    KEY `idx_job_company` (`company_id`),
    KEY `idx_job_city` (`city`),
    KEY `idx_job_status` (`status`),
    KEY `idx_job_publish` (`publish_at`),
    KEY `idx_job_salary` (`salary_min`,`salary_max`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='职位主表';

-- 职位技能关联
CREATE TABLE IF NOT EXISTS `job_skills` (
    `id`        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `job_id`    BIGINT UNSIGNED NOT NULL,
    `skill_id`  BIGINT UNSIGNED NOT NULL,
    `is_must`   TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否必须技能',
    `weight`    DECIMAL(4,2) DEFAULT 1.00 COMMENT '权重，用于匹配评分',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_job_skill` (`job_id`,`skill_id`),
    KEY `idx_js_skill` (`skill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='职位-技能关联';

-- ---------- 4. 用户行为 & 业务 ----------
-- 用户-职位关系(点击/收藏/外站投递反馈)
-- 本平台不代投，仅提供 jobs.source_url 跳转；applied 之后状态依赖用户手动反馈
CREATE TABLE IF NOT EXISTS `applications` (
    `id`                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id`            BIGINT UNSIGNED NOT NULL,
    `job_id`             BIGINT UNSIGNED NOT NULL,
    `resume_id`          BIGINT UNSIGNED DEFAULT NULL COMMENT '跳转时参考的简历',
    `status`             VARCHAR(16) NOT NULL DEFAULT 'clicked' COMMENT 'clicked/favorited/submitted/interviewed/offer/rejected',
    `match_score`        DECIMAL(5,2) DEFAULT NULL COMMENT '推荐时的匹配分0-100',
    `redirected_at`      DATETIME DEFAULT NULL COMMENT '点击跳转到外站的时间',
    `submitted_at`       DATETIME DEFAULT NULL COMMENT '用户反馈已在外站投递的时间',
    `feedback_at`        DATETIME DEFAULT NULL COMMENT '用户最近一次手动反馈时间',
    `click_count`        INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '跳转点击次数(热度统计)',
    `external_source`    VARCHAR(32)  DEFAULT NULL COMMENT '实际投递来源 boss/liepin/official',
    `note`               VARCHAR(512) DEFAULT NULL COMMENT '用户备注(面试进度/HR联系等)',
    `is_deleted`         TINYINT(1) NOT NULL DEFAULT 0,
    `created_at`         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_job` (`user_id`,`job_id`),
    KEY `idx_app_user_status` (`user_id`,`status`),
    KEY `idx_app_job` (`job_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户-职位关系(点击/收藏/外站投递反馈)';

-- 推荐记录：每次推荐生成一条，方便做A/B和效果回溯
CREATE TABLE IF NOT EXISTS `recommendations` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id`        BIGINT UNSIGNED NOT NULL,
    `resume_id`      BIGINT UNSIGNED DEFAULT NULL,
    `job_id`         BIGINT UNSIGNED NOT NULL,
    `score`          DECIMAL(5,2) NOT NULL,
    `reason`         TEXT DEFAULT NULL COMMENT '推荐理由(LLM生成)',
    `strategy`       VARCHAR(32) NOT NULL DEFAULT 'rag' COMMENT 'rag/graph/hybrid/cold_start',
    `snapshot`       JSON DEFAULT NULL COMMENT '推荐时的特征快照',
    `clicked`        TINYINT(1) NOT NULL DEFAULT 0,
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_rec_user` (`user_id`,`created_at`),
    KEY `idx_rec_strategy` (`strategy`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推荐结果流水';

-- AI对话历史
CREATE TABLE IF NOT EXISTS `chat_history` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id`    BIGINT UNSIGNED NOT NULL,
    `session_id` VARCHAR(64) NOT NULL,
    `role`       VARCHAR(16) NOT NULL COMMENT 'user/assistant/system',
    `content`    MEDIUMTEXT NOT NULL,
    `tool_calls` JSON DEFAULT NULL COMMENT '工具调用记录',
    `tokens`     INT DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_chat_session` (`session_id`,`created_at`),
    KEY `idx_chat_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI对话历史';

-- ---------- 5. 爬虫管理 ----------
CREATE TABLE IF NOT EXISTS `crawl_sources` (
    `id`           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name`         VARCHAR(64) NOT NULL COMMENT 'boss/liepin/qcc...',
    `type`         VARCHAR(32) NOT NULL DEFAULT 'job' COMMENT 'job/company',
    `base_url`     VARCHAR(255) DEFAULT NULL,
    `enabled`      TINYINT(1) NOT NULL DEFAULT 1,
    `config`       JSON DEFAULT NULL COMMENT '抓取规则/选择器',
    `created_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_source_name` (`name`,`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬虫数据源配置';

CREATE TABLE IF NOT EXISTS `crawl_tasks` (
    `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `source_id`    INT UNSIGNED NOT NULL,
    `task_code`    VARCHAR(64) NOT NULL,
    `keyword`      VARCHAR(128) DEFAULT NULL,
    `city`         VARCHAR(64) DEFAULT NULL,
    `status`       VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending/running/success/failed',
    `total`        INT DEFAULT 0 COMMENT '预期抓取数',
    `succeeded`    INT DEFAULT 0,
    `failed`       INT DEFAULT 0,
    `error_msg`    VARCHAR(512) DEFAULT NULL,
    `start_at`     DATETIME DEFAULT NULL,
    `end_at`       DATETIME DEFAULT NULL,
    `created_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_code` (`task_code`),
    KEY `idx_task_status` (`status`),
    KEY `idx_task_source` (`source_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬虫任务执行记录';
