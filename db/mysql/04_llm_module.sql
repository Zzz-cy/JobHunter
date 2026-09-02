-- =============================================================
-- JobHunter - 04_llm_module.sql
-- llm_module(LLM/Agent 模块)特有的 9 张表
-- DDL 与 llm_module/services/db_service.py 的 _create_tables() 保持一致
-- (那边也保留了自建逻辑, 两边都是 IF NOT EXISTS 幂等, 谁先跑都行)
-- 索引按队友文档 add.md 补充
-- =============================================================

-- ---------- 聊天历史 ----------

-- 会话表(聊天历史)
CREATE TABLE IF NOT EXISTS `sessions_db` (
    `id`               VARCHAR(50) NOT NULL COMMENT '会话ID(前端生成, 非自增)',
    `user_id`          INT DEFAULT NULL COMMENT '所属用户ID',
    `title`            VARCHAR(255) NOT NULL DEFAULT '' COMMENT '会话标题',
    `industry_context` VARCHAR(50) NOT NULL DEFAULT '' COMMENT '会话绑定的行业上下文',
    `role`             VARCHAR(50) NOT NULL DEFAULT 'job_seeker' COMMENT 'job_seeker/hr/career_planner/manager',
    `created_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_sessions_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-会话表';

-- 聊天消息表
CREATE TABLE IF NOT EXISTS `messages` (
    `id`          INT NOT NULL AUTO_INCREMENT,
    `session_id`  VARCHAR(50) NOT NULL COMMENT '所属会话ID',
    `role`        VARCHAR(20) NOT NULL COMMENT 'user / assistant',
    `content`     TEXT NOT NULL COMMENT '消息正文',
    `intent`      VARCHAR(50) DEFAULT NULL COMMENT '意图分类(skill_gap/learning_path等)',
    `agent_tasks` TEXT COMMENT 'Agent任务明细(JSON文本)',
    `latency_ms`  DOUBLE NOT NULL DEFAULT 0 COMMENT '响应耗时(毫秒)',
    `created_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_messages_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-聊天消息表';

-- ---------- 运行追踪 ----------

-- Agent 执行追踪表(管理后台追踪页数据源)
CREATE TABLE IF NOT EXISTS `agent_executions` (
    `id`            INT NOT NULL AUTO_INCREMENT,
    `request_id`    VARCHAR(50) DEFAULT NULL COMMENT '请求/链路ID',
    `session_id`    VARCHAR(50) DEFAULT NULL COMMENT '所属会话ID',
    `intent`        VARCHAR(50) DEFAULT NULL COMMENT '意图分类',
    `task_type`     VARCHAR(50) DEFAULT NULL COMMENT '任务类型(chat/analysis/...)',
    `model_used`    VARCHAR(100) DEFAULT NULL COMMENT '实际调用的模型名',
    `input_tokens`  INT NOT NULL DEFAULT 0,
    `output_tokens` INT NOT NULL DEFAULT 0,
    `cost`          DOUBLE NOT NULL DEFAULT 0 COMMENT '调用成本',
    `latency_ms`    DOUBLE NOT NULL DEFAULT 0 COMMENT '耗时(毫秒)',
    `status`        VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/success/failed/retry',
    `retry_count`   INT NOT NULL DEFAULT 0,
    `error_message` TEXT COMMENT '失败时的错误信息',
    `created_at`    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_agent_exec_request` (`request_id`),
    KEY `idx_agent_exec_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-Agent执行追踪表';

-- 系统运行指标表(管理后台指标监控/Prometheus导出)
CREATE TABLE IF NOT EXISTS `metrics` (
    `id`           INT NOT NULL AUTO_INCREMENT,
    `metric_name`  VARCHAR(100) NOT NULL COMMENT '指标名(llm_call_count/llm_cost等)',
    `metric_value` DOUBLE NOT NULL COMMENT '指标数值',
    `labels_json`  TEXT COMMENT '维度标签(JSON文本)',
    `timestamp`    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    PRIMARY KEY (`id`),
    KEY `idx_metrics_name` (`metric_name`),
    KEY `idx_metrics_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-系统运行指标表';

-- ---------- 评价与配额 ----------

-- 回答质量评价表
CREATE TABLE IF NOT EXISTS `evaluations` (
    `id`               INT NOT NULL AUTO_INCREMENT,
    `message_id`       INT DEFAULT NULL COMMENT '被评价的消息ID',
    `user_id`          INT DEFAULT NULL COMMENT '评价用户ID',
    `auto_score`       DOUBLE NOT NULL DEFAULT 0 COMMENT '自动评分(0-5)',
    `user_score`       DOUBLE NOT NULL DEFAULT 0 COMMENT '用户评分',
    `user_feedback`    TEXT COMMENT '用户反馈文本',
    `intent_accuracy`  DOUBLE NOT NULL DEFAULT 0 COMMENT '意图识别准确率',
    `task_completion`  DOUBLE NOT NULL DEFAULT 0 COMMENT '任务完成度',
    `response_quality` DOUBLE NOT NULL DEFAULT 0 COMMENT '回答质量分',
    `created_at`       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-回答质量评价表';

-- 用户配额表(每用户每日调用限流)
CREATE TABLE IF NOT EXISTS `user_quotas` (
    `id`           INT NOT NULL AUTO_INCREMENT,
    `user_id`      INT NOT NULL COMMENT '用户ID',
    `daily_calls`  INT NOT NULL DEFAULT 0 COMMENT '当日已用调用次数',
    `daily_tokens` INT NOT NULL DEFAULT 0 COMMENT '当日已用token数',
    `quota_date`   VARCHAR(10) NOT NULL COMMENT '配额日期(YYYY-MM-DD)',
    `updated_at`   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_quotas_user_date` (`user_id`, `quota_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-用户配额表';

-- ---------- 分类/配置/关系 ----------

-- 技能分类体系表
CREATE TABLE IF NOT EXISTS `skill_taxonomy` (
    `id`          INT NOT NULL AUTO_INCREMENT,
    `name`        VARCHAR(255) NOT NULL COMMENT '技能名称',
    `category`    VARCHAR(100) DEFAULT NULL COMMENT '所属类目',
    `industry`    VARCHAR(50) DEFAULT NULL COMMENT '所属行业',
    `level`       VARCHAR(50) DEFAULT NULL COMMENT '层级(基础/进阶等)',
    `description` TEXT COMMENT '技能说明',
    `source`      VARCHAR(100) NOT NULL DEFAULT 'manual' COMMENT 'manual/crawl/extract',
    `created_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_skill_taxonomy_industry` (`industry`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-技能分类体系表';

-- 行业配置表(按行业定制技能分类/Prompt/抽取关键词)
CREATE TABLE IF NOT EXISTS `industry_configs` (
    `id`                  INT NOT NULL AUTO_INCREMENT,
    `industry_code`       VARCHAR(50) NOT NULL COMMENT '行业编码(internet/finance等)',
    `industry_name`       VARCHAR(100) NOT NULL COMMENT '行业名称',
    `skill_categories`    TEXT COMMENT '该行业技能分类(JSON/分隔文本)',
    `prompt_overrides`    TEXT COMMENT 'Prompt覆盖配置',
    `extraction_keywords` TEXT COMMENT '抽取关键词',
    `created_at`          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_industry_code` (`industry_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-行业配置表';

-- 能力关系表(岗位↔技能/技能↔技能, 知识图谱数据层)
CREATE TABLE IF NOT EXISTS `relations` (
    `id`            INT NOT NULL AUTO_INCREMENT,
    `source_type`   VARCHAR(50) NOT NULL COMMENT '起点类型: job/skill',
    `source_name`   VARCHAR(255) NOT NULL COMMENT '起点名称',
    `target_type`   VARCHAR(50) NOT NULL COMMENT '终点类型: skill/job',
    `target_name`   VARCHAR(255) NOT NULL COMMENT '终点名称',
    `relation_type` VARCHAR(50) NOT NULL COMMENT 'requires/prerequisite/related',
    `weight`        DOUBLE NOT NULL DEFAULT 1.0 COMMENT '关系权重',
    `created_at`    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_relations_source` (`source_name`(191)),
    KEY `idx_relations_target` (`target_name`(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='llm-能力关系表';
