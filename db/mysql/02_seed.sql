-- ============================================================
-- JobHunter 种子数据 - 字典 / 测试账号
-- ============================================================
USE jobhunter;

-- ---- 行业字典(简化版，可扩展) ----
-- 一级大类(level=1)用于职位筛选, 二级(level=2)是 IT 子方向(暂留)
-- 爬虫给的 industry 是中文细字符串(141种), 导入时用 normalize_industry 归并到这些大类
INSERT INTO `industries` (`code`,`name`,`parent_id`,`level`) VALUES
('IT','互联网/IT',NULL,1),
('IT-RD','研发',1,2),
('IT-DATA','数据',1,2),
('IT-PM','产品',1,2),
('FIN','金融',NULL,1),
('EDU','教育',NULL,1),
('MED','医疗',NULL,1),
('MFG','制造',NULL,1),
('LOGI','物流/运输',NULL,1),
('RETAIL','消费/零售',NULL,1),
('REALEST','房产/建筑',NULL,1),
('ENERGY','能源/环保',NULL,1),
('CULTURE','文化/传媒',NULL,1),
('OTHER','其他',NULL,1)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- ---- 技能字典 ----
INSERT INTO `skills` (`skill_code`,`name`,`alias`,`category`,`is_hot`) VALUES
('SK_PY','Python','py,python3','语言',1),
('SK_JAVA','Java','java,java8,jdk','语言',1),
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

-- ---- 技能字典补充(覆盖爬虫数据 raw_skills 里出现的高频技能) ----
INSERT INTO `skills` (`skill_code`,`name`,`alias`,`category`,`is_hot`) VALUES
-- 语言补充
('SK_CPP','C++','cpp','语言',0),
('SK_CSHARP','C#','csharp,dotnet','语言',0),
('SK_DART','Dart',NULL,'语言',0),
('SK_CSS','CSS','stylesheet','语言',0),
('SK_KOTLIN','Kotlin',NULL,'语言',0),
('SK_SWIFT','Swift',NULL,'语言',0),
-- 框架补充
('SK_SPRINGBOOT','Spring Boot','springboot,spring-boot','框架',1),
('SK_FLASK','Flask',NULL,'框架',0),
('SK_FLUTTER','Flutter',NULL,'框架',1),
('SK_TENSORFLOW','TensorFlow','tf','框架',1),
('SK_PYTORCH','PyTorch',NULL,'框架',1),
('SK_WEBPACK','Webpack',NULL,'框架',0),
('SK_DOTNET','.NET','dotnet,Net','框架',0),
-- 大数据补充
('SK_HADOOP','Hadoop',NULL,'大数据',1),
('SK_HIVE','Hive',NULL,'大数据',0),
('SK_KAFKA','Kafka',NULL,'大数据',1),
-- DevOps / 工具补充
('SK_SHELL','Shell','bash,shell-script','工具',0),
('SK_CICD','CI/CD','cicd,jenkins','工具',0),
('SK_PROMETHEUS','Prometheus','prom','工具',0),
('SK_AZURE','Azure',NULL,'平台',0),
('SK_TABLEAU','Tableau',NULL,'工具',0),
('SK_EXCEL','Excel',NULL,'工具',0),
-- 设计 / 产品
('SK_FIGMA','Figma',NULL,'工具',1),
('SK_SKETCH','Sketch',NULL,'工具',0),
('SK_ADOBE','Adobe','ps,ai','工具',0),
('SK_PHOTOSHOP','Photoshop','PS','工具',0),
('SK_ADOBEXD','Adobe XD','XD','工具',0),
('SK_AXURE','Axure','axure-rp','工具',0),
('SK_UIUX','UI/UX','ux','方向',0),
-- 计算机基础 / 架构
('SK_DATASTRUCT','数据结构',NULL,'方向',0),
('SK_ALGORITHM','算法',NULL,'方向',1),
('SK_DESIGNPATTERN','设计模式',NULL,'方向',0),
('SK_RESTAPI','REST API','REST,restful,Restful','工具',0),
('SK_MICROSERVICE','微服务','microservice','方向',1),
('SK_DISTRIBUTED','分布式',NULL,'方向',0),
('SK_SYSARCH','系统架构','架构','方向',1),
('SK_CLOUDNATIVE','云原生','cloud-native','方向',0),
('SK_ANDROID','Android SDK','android','移动',0),
('SK_IOS','iOS SDK','ios','移动',0),
('SK_STL','STL',NULL,'方向',0),
-- AI / 算法补充
('SK_CV','计算机视觉','CV','方向',1),
('SK_DATAANALYSIS','数据分析','data-analysis','方向',1),
-- 测试
('SK_AUTOTEST','自动化测试','auto-test','方向',0),
('SK_SELENIUM','Selenium',NULL,'工具',0),
('SK_PENTEST','渗透测试','penetration-test','安全',0),
('SK_NETSEC','网络安全','network-security','安全',0),
-- 软技能
('SK_PM','产品经理','PM,product-manager','软技能',1),
('SK_PROJECTMGMT','项目管理','PM','软技能',1),
('SK_TEAMMGMT','团队管理',NULL,'软技能',0),
('SK_LEADERSHIP','领导力',NULL,'软技能',0),
('SK_REQUIREMENT','需求分析',NULL,'软技能',0),
('SK_SOLUTION','解决方案',NULL,'软技能',0),
('SK_NEGOTIATION','商务谈判',NULL,'软技能',0),
('SK_COPYWRITING','文案策划',NULL,'软技能',0),
('SK_CREATIVE','创意策划',NULL,'软技能',0),
('SK_EVENTEXEC','活动执行',NULL,'软技能',0),
('SK_MARKETING','市场推广','marketing','软技能',0),
('SK_COMMUNICATION','沟通能力',NULL,'软技能',0),
('SK_HR','人力资源管理','HR','软技能',0),
('SK_EMPLOYEE','员工关系',NULL,'软技能',0),
('SK_CUSTOMER','客户关系','CRM','软技能',0),
('SK_MARKETANA','市场分析',NULL,'软技能',0),
('SK_RECRUIT','招聘','recruiting','软技能',0),
('SK_USERRESEARCH','用户研究','user-research','方向',0),
('SK_FINANCE','财务分析',NULL,'软技能',0),
('SK_OFFICE','Office','office-suite','工具',0)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- ---- 技能字典补充(真实简历实测反馈: 词形/别名对不上导致归一化漏匹配) ----
INSERT INTO `skills` (`skill_code`,`name`,`alias`,`category`,`is_hot`) VALUES
('SK_CLANG','C语言','c','语言',0),
('SK_AI','人工智能','AI应用','方向',1),
('SK_MYBATIS','MyBatis','mybatis-plus','框架',0),
('SK_JQUERY','jQuery','jq','框架',0),
('SK_BOOTSTRAP','Bootstrap',NULL,'框架',0),
('SK_KERAS','Keras',NULL,'框架',0),
('SK_OPENCV','OpenCV',NULL,'工具',0),
('SK_UNITY','Unity',NULL,'工具',0),
('SK_WORD','Word','ms-word','工具',0),
('SK_PPT','PowerPoint','ppt,power-point','工具',0),
('SK_PREMIERE','Premiere','adobe premiere pro,pr','工具',0),
('SK_DREAMWEAVER','Dreamweaver','dw','工具',0),
('SK_ORACLE','Oracle','oracle数据库','工具',0),
('SK_SQLSERVER','SQL Server','sqlserver','工具',0),
('SK_NEURALNET','神经网络','neural-network','方向',0),
('SK_CAD','CAD',NULL,'工具',0),
('SK_CHATGPT','ChatGPT','chat-gpt','工具',0)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- ---- 测试账号(三个, 密码都是 123456) ----
-- id=1 管理员 / id=2 求职者A(03_mock 会给它简历, 用于演示推荐) / id=3 新用户(空白, 演示首次使用流程)
INSERT INTO `users` (`user_code`,`phone`,`email`,`password_hash`,`nickname`,`role`) VALUES
('U_ADMIN_001','13800000000','admin@jobhunter.local','$2b$12$GIR0SJJK4lQ80K7dFg1Zvu16GU4yUzUeCeuB/guTPb1HGznoO3ZUC','管理员','admin'),
('U_USER_001','13900000001','user1@jobhunter.local','$2b$12$GIR0SJJK4lQ80K7dFg1Zvu16GU4yUzUeCeuB/guTPb1HGznoO3ZUC','求职者A','user'),
('U_USER_002','13900000002','user2@jobhunter.local','$2b$12$GIR0SJJK4lQ80K7dFg1Zvu16GU4yUzUeCeuB/guTPb1HGznoO3ZUC','新用户','user')
ON DUPLICATE KEY UPDATE `nickname`=VALUES(`nickname`), `password_hash`=VALUES(`password_hash`);


-- ============================================================
-- 求职者A(id=2) 演示简历: 让推荐功能开箱可演示。
-- 不含任何 mock 职位(职位只来自爬虫真实数据)。
-- 幂等策略: 按 resume_code 先删后插; 技能按"字典名"映射, 不依赖自增 id。
-- ============================================================

DELETE FROM `resume_skills`
WHERE resume_id IN (SELECT id FROM `resumes` WHERE `resume_code` IN ('R_20260101','R_20260102'));
DELETE FROM `resume_experiences`
WHERE resume_id IN (SELECT id FROM `resumes` WHERE `resume_code` IN ('R_20260101','R_20260102'));
DELETE FROM `resume_educations`
WHERE resume_id IN (SELECT id FROM `resumes` WHERE `resume_code` IN ('R_20260101','R_20260102'));
DELETE FROM `resumes` WHERE `resume_code` IN ('R_20260101','R_20260102');

INSERT INTO `resumes` (`resume_code`, `user_id`, `name`, `gender`, `age`, `city`, `phone`, `email`, `source_type`, `file_url`, `parse_status`, `work_years`, `education`, `expect_salary_min`, `expect_salary_max`, `expect_city`, `expect_job`, `overall_score`) VALUES
('R_20260101', 2, '张三', 0, 28, '北京', '13900000001', 'zhangsan@example.com',
 'pdf', NULL, 'done', 5, '本科', 25, 40, '北京', 'Python 后端工程师', 88.50),
('R_20260102', 2, '张三', 0, 28, '北京', '13900000001', 'zhangsan@example.com',
 'pdf', NULL, 'done', 5, '本科', 30, 50, '北京', '机器学习工程师', 82.00);

INSERT INTO `resume_skills` (`resume_id`, `skill_id`, `proficiency`, `years`)
SELECT r.id, s.id, t.prof, t.yrs
FROM `resumes` r
JOIN (
    SELECT 'R_20260101' AS code, 'Python' AS skill_name, 5 AS prof, 5.0 AS yrs UNION ALL
    SELECT 'R_20260101', 'FastAPI', 4, 2.0 UNION ALL
    SELECT 'R_20260101', 'Django', 4, 3.0 UNION ALL
    SELECT 'R_20260101', 'MySQL', 4, 5.0 UNION ALL
    SELECT 'R_20260101', 'Redis', 4, 4.0 UNION ALL
    SELECT 'R_20260101', 'Docker', 3, 2.0 UNION ALL
    SELECT 'R_20260101', 'Git', 4, 5.0 UNION ALL
    SELECT 'R_20260101', 'Linux', 4, 5.0 UNION ALL
    SELECT 'R_20260102', 'Python', 5, 5.0 UNION ALL
    SELECT 'R_20260102', '机器学习', 4, 3.0 UNION ALL
    SELECT 'R_20260102', '深度学习', 3, 2.0 UNION ALL
    SELECT 'R_20260102', 'NLP', 4, 2.5 UNION ALL
    SELECT 'R_20260102', 'LLM', 3, 1.0 UNION ALL
    SELECT 'R_20260102', 'SQL', 4, 4.0
) t ON t.code = r.resume_code
JOIN `skills` s ON s.name = t.skill_name;

INSERT INTO `resume_experiences` (`resume_id`, `company_name`, `title`, `start_date`, `end_date`, `description`, `is_current`)
SELECT r.id, x.company_name, x.title, x.start_date, x.end_date, x.description, x.is_current
FROM `resumes` r
JOIN (
    SELECT 'R_20260101' AS code, '字节跳动' AS company_name, 'Python 后端工程师' AS title, '2021-07-01' AS start_date, NULL AS end_date, '负责核心业务系统的设计与开发,参与高并发架构优化。' AS description, 1 AS is_current UNION ALL
    SELECT 'R_20260101', '某创业公司', '初级 Python 开发', '2018-07-01', '2021-06-30', 'Web 后端开发,使用 Django 框架,负责电商平台 API 开发。', 0 UNION ALL
    SELECT 'R_20260102', '字节跳动', 'Python 后端工程师', '2021-07-01', NULL, '兼顾业务开发和算法落地,参与推荐系统特征工程项目。', 1
) x ON x.code = r.resume_code;

INSERT INTO `resume_educations` (`resume_id`, `school`, `major`, `degree`, `start_date`, `end_date`)
SELECT r.id, '北京理工大学', '计算机科学与技术', '本科', '2014-09-01', '2018-06-30'
FROM `resumes` r WHERE r.resume_code IN ('R_20260101','R_20260102');
