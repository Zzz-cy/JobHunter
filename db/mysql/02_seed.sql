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

-- ---- 测试账号(密码: 123456 的 bcrypt 哈希) ----
INSERT INTO `users` (`user_code`,`phone`,`email`,`password_hash`,`nickname`,`role`) VALUES
('U_ADMIN_001','13800000000','admin@jobhunter.local','$2a$10$N9qo8uLOickgx2ZMRZoMy.MrqMJBrBnTgvIWIgUVS4tYqQ6tBqK.','管理员','admin'),
('U_USER_001','13900000001','user1@jobhunter.local','$2a$10$N9qo8uLOickgx2ZMRZoMy.MrqMJBrBnTgvIWIgUVS4tYqQ6tBqK.','求职者A','user')
ON DUPLICATE KEY UPDATE `nickname`=VALUES(`nickname`);
