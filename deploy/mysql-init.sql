-- llm_module 独立使用的库(与主库 jobhunter 隔离, 由 compose 挂载到 MySQL 初始化目录)
CREATE DATABASE IF NOT EXISTS job_competency
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
