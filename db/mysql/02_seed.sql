-- ============================================================
-- JobHunter 种子数据 - 字典 / 测试账号
-- ============================================================
USE jobhunter;

-- ---- 行业字典(简化版，可扩展) ----
INSERT INTO `industries` (`code`,`name`,`parent_id`,`level`) VALUES
('IT','互联网/IT',NULL,1),
('IT-RD','研发',1,2),
('IT-DATA','数据',1,2),
('IT-PM','产品',1,2),
('FIN','金融',NULL,1),
('EDU','教育',NULL,1),
('MED','医疗',NULL,1),
('MFG','制造',NULL,1)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- ---- 技能字典 ----
INSERT INTO `skills` (`skill_code`,`name`,`alias`,`category`,`is_hot`) VALUES
('SK_PY','Python','py,python3','语言',1),
('SK_JAVA','Java','java8,jdk','语言',1),
('SK_JS','JavaScript','js,es6','语言',1),
('SK_TS','TypeScript','ts','语言',1),
('SK_GO','Go','golang','语言',1),
('SK_SQL','SQL','mysql,postgresql','语言',0),
('SK_REACT','React','reactjs,react.js','框架',1),
('SK_VUE','Vue','vuejs,vue3','框架',1),
('SK_NODE','Node.js','node','框架',1),
('SK_FASTAPI','FastAPI','fast-api','框架',0),
('SK_DJANGO','Django',NULL,'框架',0),
('SK_SPARK','Spark','apache-spark','框架',1),
('SK_FLINK','Flink','apache-flink','框架',1),
('SK_ML','机器学习','machine-learning,ml','方向',1),
('SK_DL','深度学习','deep-learning,dl','方向',1),
('SK_NLP','NLP','自然语言处理','方向',1),
('SK_LLM','大模型','LLM,GPT,大语言模型','方向',1),
('SK_DOCKER','Docker','容器','工具',1),
('SK_K8S','Kubernetes','k8s,kubernetes','工具',1),
('SK_MYSQL','MySQL','关系数据库','工具',0),
('SK_ES','Elasticsearch','es,elastic','工具',1),
('SK_NEO4J','Neo4j','图数据库','工具',0),
('SK_REDIS','Redis','缓存','工具',1),
('SK_GIT','Git','版本控制','工具',0),
('SK_LINUX','Linux','linux-shell','工具',0)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- ---- 测试账号(密码: 123456 的 bcrypt 哈希) ----
INSERT INTO `users` (`user_code`,`phone`,`email`,`password_hash`,`nickname`,`role`) VALUES
('U_ADMIN_001','13800000000','admin@jobhunter.local','$2a$10$N9qo8uLOickgx2ZMRZoMy.MrqMJBrBnTgvIWIgUVS4tYqQ6tBqK.','管理员','admin'),
('U_USER_001','13900000001','user1@jobhunter.local','$2a$10$N9qo8uLOickgx2ZMRZoMy.MrqMJBrBnTgvIWIgUVS4tYqQ6tBqK.','求职者A','user')
ON DUPLICATE KEY UPDATE `nickname`=VALUES(`nickname`);
