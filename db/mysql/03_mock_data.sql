-- ============================================================
-- JobHunter 假数据 - 用于前端开发调试
-- 覆盖: 公司 / 职位 / 职位技能 / 简历 / 简历技能 / 投递 / 推荐
-- ============================================================
USE jobhunter;

-- 清空相关表(保留字典和测试账号)
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE applications;
TRUNCATE TABLE recommendations;
TRUNCATE TABLE job_skills;
TRUNCATE TABLE resume_skills;
TRUNCATE TABLE resume_experiences;
TRUNCATE TABLE resume_educations;
TRUNCATE TABLE resumes;
TRUNCATE TABLE jobs;
TRUNCATE TABLE companies;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 1. 公司数据 (10 家,覆盖 3 个来源)
-- ============================================================
INSERT INTO `companies` (`company_code`, `name`, `short_name`, `industry_code`, `size`, `stage`, `city`, `district`, `address`, `website`, `welfare`, `description`, `source`, `source_url`) VALUES
('C_BD_001', '字节跳动', '字节', 'IT', '10000+', '已上市', '北京', '海淀区', '海淀区中关村大街 1 号', 'https://bytedance.com',
 JSON_ARRAY('六险一金','免费三餐','弹性工作','股票期权','年度旅游'),
 '字节跳动是全球领先的内容科技公司,旗下产品包括抖音、TikTok、今日头条等。', 'boss', 'https://www.zhipin.com/gongsi/ee9f3f.html'),

('C_BD_002', '阿里巴巴集团', '阿里', 'IT', '10000+', '已上市', '杭州', '余杭区', '余杭区文一西路 969 号', 'https://alibaba.com',
 JSON_ARRAY('五险一金','补充医疗','股票期权','免费班车'),
 '阿里巴巴集团是中国领先的互联网基础设施提供商,业务涵盖电商、云计算、金融科技等。', 'boss', 'https://www.zhipin.com/gongsi/abc123.html'),

('C_BD_003', '腾讯科技', '腾讯', 'IT', '10000+', '已上市', '深圳', '南山区', '南山区科技中一路腾讯大厦', 'https://tencent.com',
 JSON_ARRAY('六险一金','免费餐补','股票期权','年度体检'),
 '腾讯是中国领先的互联网增值服务提供商,旗下有微信、QQ 等知名产品。', 'boss', 'https://www.zhipin.com/gongsi/tencent.html'),

('C_LP_001', '美团', '美团', 'IT', '10000+', '已上市', '北京', '朝阳区', '朝阳区望京东路 6 号', 'https://meituan.com',
 JSON_ARRAY('五险一金','免费三餐','股票期权','岗位晋升'),
 '美团是中国领先的生活服务电子商务平台。', 'liepin', 'https://www.liepin.com/company/12345.shtml'),

('C_LP_002', '拼多多', '拼多多', 'IT', '10000+', '已上市', '上海', '长宁区', '长宁区娄山关路 533 号', 'https://pinduoduo.com',
 JSON_ARRAY('五险一金','股票期权','周末双休'),
 '拼多多是国内领先的新型电商平台。', 'liepin', 'https://www.liepin.com/company/23456.shtml'),

('C_LP_003', '京东集团', '京东', 'IT', '10000+', '已上市', '北京', '大兴区', '大兴区科创十一街 18 号', 'https://jd.com',
 JSON_ARRAY('六险一金','免费班车','股票期权'),
 '京东是中国领先的自营式电商企业。', 'liepin', 'https://www.liepin.com/company/34567.shtml'),

('C_OF_001', '小红书', '小红书', 'IT', '5000-10000', 'D 轮及以上', '上海', '黄浦区', '黄浦区思南路 105 号', 'https://xiaohongshu.com',
 JSON_ARRAY('六险一金','弹性工作','免费零食','年度团建'),
 '小红书是年轻人的生活方式平台和消费决策入口。', 'official', 'https://job.xiaohongshu.com'),

('C_OF_002', '网易公司', '网易', 'IT', '10000+', '已上市', '杭州', '滨江区', '滨江区网商路 599 号', 'https://163.com',
 JSON_ARRAY('五险一金','免费三餐','猪厂食堂','股票期权'),
 '网易是中国领先的互联网技术公司。', 'official', 'https://hr.163.com'),

('C_OF_003', '华为技术', '华为', 'MFG', '10000+', '已上市', '深圳', '龙岗区', '龙岗区坂田华为基地', 'https://huawei.com',
 JSON_ARRAY('六险一金','员工宿舍','股票期权','外派机会'),
 '华为是全球领先的 ICT 基础设施和智能终端提供商。', 'official', 'https://career.huawei.com'),

('C_OF_004', '招商银行', '招行', 'FIN', '10000+', '已上市', '深圳', '福田区', '福田区深南大道 7088 号', 'https://cmbchina.com',
 JSON_ARRAY('五险一金','企业年金','补充医疗','员工优惠'),
 '招商银行是中国领先的零售银行。', 'official', 'https://hr.cmbchina.com');


-- ============================================================
-- 2. 职位数据 (15 个职位)
-- ============================================================
INSERT INTO `jobs` (`job_code`, `company_id`, `title`, `department`, `city`, `district`, `experience_req`, `education_req`, `salary_min`, `salary_max`, `salary_unit`, `salary_months`, `job_type`, `description`, `description_text`, `highlights`, `advantage`, `work_address`, `source`, `source_url`, `source_id`, `crawl_batch`, `status`, `publish_at`, `crawl_at`, `quality_score`) VALUES

('J_20260101', 1, '资深 Python 后端工程师', '基础架构', '北京', '海淀区', '3-5年', '本科', 25, 45, 'month', 15, 'full',
 '<h3>岗位职责</h3><ul><li>负责字节跳动核心业务系统的设计与开发</li><li>参与高并发、高可用系统的架构优化</li><li>解决生产环境的技术难题</li></ul><h3>任职要求</h3><ul><li>3 年以上 Python 后端开发经验</li><li>熟悉 Django/FastAPI 等框架</li><li>精通 MySQL、Redis</li><li>有大规模分布式系统经验优先</li></ul>',
 '岗位职责:负责字节跳动核心业务系统的设计与开发,参与高并发、高可用系统的架构优化,解决生产环境的技术难题。任职要求:3 年以上 Python 后端开发经验,熟悉 Django/FastAPI 等框架,精通 MySQL、Redis,有大规模分布式系统经验优先。',
 JSON_ARRAY('弹性工作','股票期权','免费三餐','六险一金','15薪'),
 '加入核心架构团队,参与日活过亿产品的研发', '北京市海淀区中关村大街 1 号',
 'boss', 'https://www.zhipin.com/job/111.html', 'boss_111', 'mock_202606', 'active', '2026-06-01 10:00:00', '2026-06-13 02:00:00', 92.50),

('J_20260102', 1, '机器学习算法工程师', 'AI 实验室', '北京', '海淀区', '3-5年', '硕士', 30, 60, 'month', 15, 'full',
 '<h3>岗位职责</h3><ul><li>负责推荐系统、NLP 项目的算法研发</li><li>跟进大模型前沿技术,落地业务场景</li></ul><h3>任职要求</h3><ul><li>熟练掌握 Python、PyTorch</li><li>熟悉 LLM、Transformer 架构</li><li>有推荐系统/搜索/NLP 项目经验</li></ul>',
 '岗位职责:负责推荐系统、NLP 项目的算法研发,跟进大模型前沿技术,落地业务场景。任职要求:熟练掌握 Python、PyTorch,熟悉 LLM、Transformer 架构,有推荐系统/搜索/NLP 项目经验。',
 JSON_ARRAY('股票期权','免费三餐','15薪','技术研发'),
 '参与 TikTok 全球推荐系统研发', '北京市海淀区中关村大街 1 号',
 'boss', 'https://www.zhipin.com/job/112.html', 'boss_112', 'mock_202606', 'active', '2026-06-05 14:00:00', '2026-06-13 02:00:00', 90.00),

('J_20260103', 2, '高级 Java 开发工程师', '中间件团队', '杭州', '余杭区', '5-10年', '本科', 30, 50, 'month', 16, 'full',
 '<h3>岗位职责</h3><ul><li>负责阿里中间件产品的设计与开发</li><li>打造亿级用户的分布式系统</li></ul><h3>任职要求</h3><ul><li>5 年以上 Java 开发经验</li><li>深入理解 JVM、并发编程</li><li>熟悉 Spring Cloud 微服务架构</li></ul>',
 '岗位职责:负责阿里中间件产品的设计与开发,打造亿级用户的分布式系统。任职要求:5 年以上 Java 开发经验,深入理解 JVM、并发编程,熟悉 Spring Cloud 微服务架构。',
 JSON_ARRAY('16薪','股票期权','免费班车','弹性工作'),
 '阿里核心中间件团队,主导双十一技术挑战', '杭州市余杭区文一西路 969 号',
 'boss', 'https://www.zhipin.com/job/121.html', 'boss_121', 'mock_202606', 'active', '2026-06-08 09:30:00', '2026-06-13 02:00:00', 88.50),

('J_20260104', 2, '数据分析师', '数据智能', '杭州', '余杭区', '1-3年', '本科', 15, 25, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责业务数据的分析、建模和可视化</li><li>搭建数据看板,支持业务决策</li></ul><h3>任职要求</h3><ul><li>熟练 SQL、Python</li><li>熟悉 Spark、Hive 等大数据工具</li><li>有电商数据分析经验优先</li></ul>',
 '岗位职责:负责业务数据的分析、建模和可视化,搭建数据看板,支持业务决策。任职要求:熟练 SQL、Python,熟悉 Spark、Hive 等大数据工具,有电商数据分析经验优先。',
 JSON_ARRAY('14薪','五险一金','股票期权'),
 '阿里电商数据团队,接触海量业务数据', '杭州市余杭区文一西路 969 号',
 'boss', 'https://www.zhipin.com/job/122.html', 'boss_122', 'mock_202606', 'active', '2026-06-10 11:00:00', '2026-06-13 02:00:00', 85.00),

('J_20260105', 3, '前端开发工程师 (Vue 方向)', '微信支付', '深圳', '南山区', '3-5年', '本科', 20, 40, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责微信支付商户平台的前端开发</li><li>与产品、设计协作交付高质量产品</li></ul><h3>任职要求</h3><ul><li>3 年以上前端开发经验</li><li>精通 Vue 3 + TypeScript</li><li>熟悉 Vite、Pinia、Element Plus</li><li>有大型 SPA 项目经验</li></ul>',
 '岗位职责:负责微信支付商户平台的前端开发,与产品、设计协作交付高质量产品。任职要求:3 年以上前端开发经验,精通 Vue 3 + TypeScript,熟悉 Vite、Pinia、Element Plus,有大型 SPA 项目经验。',
 JSON_ARRAY('14薪','免费餐补','股票期权','六险一金'),
 '加入微信支付核心技术团队', '深圳市南山区科技中一路腾讯大厦',
 'boss', 'https://www.zhipin.com/job/131.html', 'boss_131', 'mock_202606', 'active', '2026-06-12 10:00:00', '2026-06-13 02:00:00', 89.00),

('J_20260106', 3, 'DevOps 工程师', '云架构', '深圳', '南山区', '3-5年', '本科', 22, 35, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责腾讯云基础架构的运维和优化</li><li>搭建 CI/CD 流水线</li></ul><h3>任职要求</h3><ul><li>熟悉 Docker、Kubernetes</li><li>掌握 Linux、Shell 脚本</li><li>有大规模集群运维经验</li></ul>',
 '岗位职责:负责腾讯云基础架构的运维和优化,搭建 CI/CD 流水线。任职要求:熟悉 Docker、Kubernetes,掌握 Linux、Shell 脚本,有大规模集群运维经验。',
 JSON_ARRAY('14薪','六险一金','股票期权','年度体检'),
 '主导腾讯云核心集群运维', '深圳市南山区科技中一路腾讯大厦',
 'boss', 'https://www.zhipin.com/job/132.html', 'boss_132', 'mock_202606', 'active', '2026-06-09 14:30:00', '2026-06-13 02:00:00', 83.00),

('J_20260107', 4, '资深大数据开发工程师', '配送网络', '北京', '朝阳区', '5-10年', '本科', 35, 60, 'month', 15, 'full',
 '<h3>岗位职责</h3><ul><li>负责美团配送大数据平台建设</li><li>处理 PB 级实时数据流</li></ul><h3>任职要求</h3><ul><li>5 年以上大数据开发经验</li><li>精通 Spark、Flink</li><li>熟悉 Hive、HBase、Kafka</li></ul>',
 '岗位职责:负责美团配送大数据平台建设,处理 PB 级实时数据流。任职要求:5 年以上大数据开发经验,精通 Spark、Flink,熟悉 Hive、HBase、Kafka。',
 JSON_ARRAY('15薪','免费三餐','股票期权','岗位晋升'),
 '处理美团全量配送数据,挑战 PB 级规模', '北京市朝阳区望京东路 6 号',
 'liepin', 'https://www.liepin.com/job/211.shtml', 'lp_211', 'mock_202606', 'active', '2026-06-11 16:00:00', '2026-06-13 02:00:00', 87.50),

('J_20260108', 4, '产品经理 (C 端)', '到店事业群', '北京', '朝阳区', '3-5年', '本科', 20, 35, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责美团到店业务的产品规划</li><li>挖掘用户需求,设计产品方案</li></ul><h3>任职要求</h3><ul><li>3 年以上互联网产品经验</li><li>熟悉 C 端产品方法论</li><li>数据分析能力强</li></ul>',
 '岗位职责:负责美团到店业务的产品规划,挖掘用户需求,设计产品方案。任职要求:3 年以上互联网产品经验,熟悉 C 端产品方法论,数据分析能力强。',
 JSON_ARRAY('14薪','免费三餐','岗位晋升','弹性工作'),
 '主导日活千万级产品迭代', '北京市朝阳区望京东路 6 号',
 'liepin', 'https://www.liepin.com/job/212.shtml', 'lp_212', 'mock_202606', 'active', '2026-06-06 10:30:00', '2026-06-13 02:00:00', 80.00),

('J_20260109', 5, '推荐算法专家', '智能推荐', '上海', '长宁区', '5-10年', '硕士', 40, 70, 'month', 15, 'full',
 '<h3>岗位职责</h3><ul><li>负责拼多多核心推荐算法优化</li><li>设计深度学习模型提升 GMV</li></ul><h3>任职要求</h3><ul><li>5 年以上推荐算法经验</li><li>熟悉深度学习、特征工程</li><li>有大型电商推荐系统经验</li></ul>',
 '岗位职责:负责拼多多核心推荐算法优化,设计深度学习模型提升 GMV。任职要求:5 年以上推荐算法经验,熟悉深度学习、特征工程,有大型电商推荐系统经验。',
 JSON_ARRAY('15薪','股票期权','周末双休','弹性工作'),
 '主导电商推荐核心算法,直接影响 GMV', '上海市长宁区娄山关路 533 号',
 'liepin', 'https://www.liepin.com/job/221.shtml', 'lp_221', 'mock_202606', 'active', '2026-06-07 11:00:00', '2026-06-13 02:00:00', 94.00),

('J_20260110', 5, 'Android 高级工程师', '客户端', '上海', '长宁区', '3-5年', '本科', 25, 40, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责拼多多 Android 客户端开发</li><li>优化 App 性能和用户体验</li></ul><h3>任职要求</h3><ul><li>3 年以上 Android 开发经验</li><li>熟悉 Kotlin、Jetpack</li><li>有性能优化经验</li></ul>',
 '岗位职责:负责拼多多 Android 客户端开发,优化 App 性能和用户体验。任职要求:3 年以上 Android 开发经验,熟悉 Kotlin、Jetpack,有性能优化经验。',
 JSON_ARRAY('14薪','股票期权','周末双休'),
 '主导亿级用户 App 开发', '上海市长宁区娄山关路 533 号',
 'liepin', 'https://www.liepin.com/job/222.shtml', 'lp_222', 'mock_202606', 'active', '2026-06-04 09:00:00', '2026-06-13 02:00:00', 82.50),

('J_20260111', 6, '全栈工程师', '技术研发', '北京', '大兴区', '3-5年', '本科', 22, 38, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责京东商家后台全栈开发</li><li>独立完成前后端模块交付</li></ul><h3>任职要求</h3><ul><li>3 年以上全栈开发经验</li><li>精通 Vue 3 + Node.js / Python</li><li>熟悉 MySQL、Redis</li></ul>',
 '岗位职责:负责京东商家后台全栈开发,独立完成前后端模块交付。任职要求:3 年以上全栈开发经验,精通 Vue 3 + Node.js / Python,熟悉 MySQL、Redis。',
 JSON_ARRAY('14薪','六险一金','股票期权','免费班车'),
 '全栈岗位,前后端均衡发展', '北京市大兴区科创十一街 18 号',
 'liepin', 'https://www.liepin.com/job/231.shtml', 'lp_231', 'mock_202606', 'active', '2026-06-03 13:00:00', '2026-06-13 02:00:00', 81.00),

('J_20260112', 7, '大模型应用工程师', 'AI 创新部', '上海', '黄浦区', '1-3年', '本科', 25, 50, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责小红书大模型应用产品研发</li><li>探索 LLM 在内容创作场景的落地</li></ul><h3>任职要求</h3><ul><li>熟悉 LangChain、Prompt Engineering</li><li>有 LLM 微调经验优先</li><li>Python 后端扎实</li></ul>',
 '岗位职责:负责小红书大模型应用产品研发,探索 LLM 在内容创作场景的落地。任职要求:熟悉 LangChain、Prompt Engineering,有 LLM 微调经验优先,Python 后端扎实。',
 JSON_ARRAY('14薪','六险一金','弹性工作','免费零食'),
 '前沿 LLM 应用方向,自由探索空间大', '上海市黄浦区思南路 105 号',
 'official', 'https://job.xiaohongshu.com/position/1', 'xhs_1', 'mock_202606', 'active', '2026-06-12 15:00:00', '2026-06-13 02:00:00', 86.50),

('J_20260113', 7, '后端开发工程师 (Python)', '社区技术', '上海', '黄浦区', '1-3年', '本科', 18, 30, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责小红书社区后端服务开发</li><li>保障高并发场景下的系统稳定</li></ul><h3>任职要求</h3><ul><li>1 年以上 Python 后端经验</li><li>熟悉 FastAPI / Django</li><li>了解 Elasticsearch、Redis</li></ul>',
 '岗位职责:负责小红书社区后端服务开发,保障高并发场景下的系统稳定。任职要求:1 年以上 Python 后端经验,熟悉 FastAPI / Django,了解 Elasticsearch、Redis。',
 JSON_ARRAY('14薪','六险一金','弹性工作','年度团建'),
 '加入小红书核心技术团队', '上海市黄浦区思南路 105 号',
 'official', 'https://job.xiaohongshu.com/position/2', 'xhs_2', 'mock_202606', 'active', '2026-06-10 10:00:00', '2026-06-13 02:00:00', 84.00),

('J_20260114', 8, '资深 NLP 算法工程师', '网易有道', '杭州', '滨江区', '3-5年', '硕士', 28, 50, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责有道词典、翻译产品的 NLP 算法研发</li><li>提升机器翻译质量</li></ul><h3>任职要求</h3><ul><li>3 年以上 NLP 相关经验</li><li>熟悉 Transformer、BERT</li><li>有机器翻译项目经验优先</li></ul>',
 '岗位职责:负责有道词典、翻译产品的 NLP 算法研发,提升机器翻译质量。任职要求:3 年以上 NLP 相关经验,熟悉 Transformer、BERT,有机器翻译项目经验优先。',
 JSON_ARRAY('14薪','猪厂食堂','股票期权','五险一金'),
 '有道核心算法团队,深耕 NLP 前沿', '杭州市滨江区网商路 599 号',
 'official', 'https://hr.163.com/position/1', '163_1', 'mock_202606', 'active', '2026-06-08 11:30:00', '2026-06-13 02:00:00', 88.00),

('J_20260115', 9, '云计算工程师', '华为云', '深圳', '龙岗区', '3-5年', '本科', 22, 38, 'month', 14, 'full',
 '<h3>岗位职责</h3><ul><li>负责华为云容器服务开发与运维</li><li>参与云原生产品研发</li></ul><h3>任职要求</h3><ul><li>3 年以上云计算领域经验</li><li>熟悉 Kubernetes、Docker</li><li>了解 Go / Python</li></ul>',
 '岗位职责:负责华为云容器服务开发与运维,参与云原生产品研发。任职要求:3 年以上云计算领域经验,熟悉 Kubernetes、Docker,了解 Go / Python。',
 JSON_ARRAY('14薪','六险一金','股票期权','员工宿舍'),
 '加入华为云核心研发团队', '深圳市龙岗区坂田华为基地',
 'official', 'https://career.huawei.com/position/1', 'hw_1', 'mock_202606', 'active', '2026-06-05 09:00:00', '2026-06-13 02:00:00', 85.50);


-- ============================================================
-- 3. 职位技能关联 (job_skills)
-- ============================================================
-- 技能 ID 对照:
--   1=Python  2=Java   3=JS    4=TS    5=Go
--   6=SQL     7=React  8=Vue   9=Node  10=FastAPI
--  11=Django 12=Spark 13=Flink 14=ML   15=DL
--  16=NLP   17=LLM   18=Docker 19=K8s 20=MySQL
--  21=ES    22=Neo4j 23=Redis 24=Git  25=Linux

INSERT INTO `job_skills` (`job_id`, `skill_id`, `is_must`, `weight`) VALUES
-- J1 资深 Python 后端 (字节)
(1, 1, 1, 5.00),    -- Python (必须)
(1, 10, 1, 4.00),   -- FastAPI (必须)
(1, 20, 1, 3.50),   -- MySQL (必须)
(1, 23, 0, 3.00),   -- Redis
(1, 18, 0, 2.50),   -- Docker
(1, 24, 0, 1.50),   -- Git
(1, 25, 0, 2.00),   -- Linux
-- J2 机器学习算法 (字节)
(2, 1, 1, 5.00),    -- Python
(2, 14, 1, 4.50),   -- ML
(2, 15, 1, 4.00),   -- DL
(2, 17, 0, 4.00),   -- LLM
(2, 16, 0, 3.00),   -- NLP
-- J3 高级 Java (阿里)
(3, 2, 1, 5.00),    -- Java
(3, 20, 1, 3.50),   -- MySQL
(3, 23, 0, 3.00),   -- Redis
(3, 18, 0, 2.50),   -- Docker
(3, 25, 0, 2.00),   -- Linux
-- J4 数据分析师 (阿里)
(4, 6, 1, 4.50),    -- SQL
(4, 1, 1, 4.00),    -- Python
(4, 12, 0, 3.50),   -- Spark
-- J5 前端 Vue (腾讯)
(5, 8, 1, 5.00),    -- Vue
(5, 3, 1, 4.00),    -- JS
(5, 4, 1, 4.00),    -- TS
(5, 24, 0, 1.50),   -- Git
-- J6 DevOps (腾讯)
(6, 18, 1, 5.00),   -- Docker
(6, 19, 1, 5.00),   -- K8s
(6, 25, 1, 4.00),   -- Linux
(6, 5, 0, 2.50),    -- Go
-- J7 资深大数据 (美团)
(7, 1, 1, 4.00),    -- Python
(7, 12, 1, 5.00),   -- Spark
(7, 13, 1, 4.50),   -- Flink
(7, 6, 0, 3.00),    -- SQL
-- J8 产品经理 (美团)
-- 软技能为主,暂不关联硬技能
-- J9 推荐算法专家 (拼多多)
(9, 1, 1, 4.00),    -- Python
(9, 14, 1, 5.00),   -- ML
(9, 15, 1, 5.00),   -- DL
(9, 12, 0, 3.00),   -- Spark
-- J10 Android (拼多多)
(10, 24, 0, 1.50),  -- Git
-- J11 全栈 (京东)
(11, 8, 1, 5.00),   -- Vue
(11, 9, 1, 4.00),   -- Node
(11, 1, 1, 4.00),   -- Python
(11, 20, 0, 3.00),  -- MySQL
(11, 23, 0, 2.50),  -- Redis
-- J12 大模型应用 (小红书)
(12, 1, 1, 4.00),   -- Python
(12, 17, 1, 5.00),  -- LLM
(12, 16, 0, 3.00),  -- NLP
(12, 21, 0, 2.00),  -- ES
-- J13 Python 后端 (小红书)
(13, 1, 1, 5.00),   -- Python
(13, 10, 1, 4.00),  -- FastAPI
(13, 11, 0, 3.00),  -- Django
(13, 21, 0, 2.50),  -- ES
(13, 23, 0, 2.00),  -- Redis
-- J14 NLP 算法 (网易有道)
(14, 1, 1, 4.00),   -- Python
(14, 16, 1, 5.00),  -- NLP
(14, 15, 1, 4.00),  -- DL
(14, 17, 0, 3.00),  -- LLM
-- J15 云计算 (华为云)
(15, 19, 1, 5.00),  -- K8s
(15, 18, 1, 4.50),  -- Docker
(15, 5, 0, 3.00),   -- Go
(15, 25, 0, 2.50);  -- Linux


-- ============================================================
-- 4. 简历数据 (求职者 A: 2 份简历)
-- ============================================================
-- user_id=2 是种子里的 求职者A

INSERT INTO `resumes` (`resume_code`, `user_id`, `name`, `gender`, `age`, `city`, `phone`, `email`, `source_type`, `file_url`, `parse_status`, `work_years`, `education`, `expect_salary_min`, `expect_salary_max`, `expect_city`, `expect_job`, `overall_score`, `parsed_raw`) VALUES

('R_20260101', 2, '张三', 0, 28, '北京', '13900000001', 'zhangsan@example.com',
 'pdf', 'https://cdn.jobhunter.com/resumes/r_20260101.pdf',
 'done', 5, '本科', 25, 40, '北京', 'Python 后端工程师', 88.50,
 JSON_OBJECT(
   'education', JSON_ARRAY(
     JSON_OBJECT('school', '北京理工大学', 'major', '计算机科学与技术', 'degree', '本科', 'start', '2014-09', 'end', '2018-06')
   ),
   'experiences', JSON_ARRAY(
     JSON_OBJECT('company', '字节跳动', 'title', 'Python 后端工程师', 'start', '2021-07', 'end', 'current',
       'desc', '负责核心业务系统开发,参与高并发架构优化'),
     JSON_OBJECT('company', '某创业公司', 'title', '初级 Python 开发', 'start', '2018-07', 'end', '2021-06',
       'desc', 'Web 后端开发,使用 Django 框架')
   ),
   'skills', JSON_ARRAY('Python','FastAPI','Django','MySQL','Redis','Docker','Git','Linux')
 )),

('R_20260102', 2, '张三', 0, 28, '北京', '13900000001', 'zhangsan@example.com',
 'pdf', 'https://cdn.jobhunter.com/resumes/r_20260102.pdf',
 'done', 5, '本科', 30, 50, '北京', '机器学习工程师', 82.00,
 JSON_OBJECT(
   'skills', JSON_ARRAY('Python','机器学习','深度学习','NLP','LLM','PyTorch')
 ));


-- ============================================================
-- 5. 简历技能档案 (resume_skills)
-- ============================================================
-- 简历 1: Python 后端方向
INSERT INTO `resume_skills` (`resume_id`, `skill_id`, `proficiency`, `years`) VALUES
(1, 1, 5, 5.0),    -- Python: 精通, 5年
(1, 10, 4, 2.0),   -- FastAPI: 熟悉, 2年
(1, 11, 4, 3.0),   -- Django: 熟悉, 3年
(1, 20, 4, 5.0),   -- MySQL: 熟悉, 5年
(1, 23, 4, 4.0),   -- Redis: 熟悉, 4年
(1, 18, 3, 2.0),   -- Docker: 了解, 2年
(1, 21, 3, 1.5),   -- ES: 了解, 1.5年
(1, 24, 4, 5.0),   -- Git: 熟悉, 5年
(1, 25, 4, 5.0),   -- Linux: 熟悉, 5年
(1, 6, 4, 5.0);    -- SQL: 熟悉, 5年

-- 简历 2: 机器学习方向
INSERT INTO `resume_skills` (`resume_id`, `skill_id`, `proficiency`, `years`) VALUES
(2, 1, 5, 5.0),    -- Python: 精通
(2, 14, 4, 3.0),   -- ML: 熟悉
(2, 15, 3, 2.0),   -- DL: 了解
(2, 16, 4, 2.5),   -- NLP: 熟悉
(2, 17, 3, 1.0),   -- LLM: 了解
(2, 6, 4, 4.0);    -- SQL


-- ============================================================
-- 6. 工作经历 (resume_experiences)
-- ============================================================
INSERT INTO `resume_experiences` (`resume_id`, `company_name`, `title`, `start_date`, `end_date`, `description`, `is_current`) VALUES
(1, '字节跳动', 'Python 后端工程师', '2021-07-01', NULL, '负责核心业务系统的设计与开发,参与高并发架构优化,主导多个微服务项目。', 1),
(1, '某创业公司', '初级 Python 开发', '2018-07-01', '2021-06-30', 'Web 后端开发,使用 Django 框架,负责电商平台 API 开发。', 0),
(2, '字节跳动', 'Python 后端工程师', '2021-07-01', NULL, '兼顾业务开发和算法落地,参与推荐系统特征工程项目。', 1);


-- ============================================================
-- 7. 教育经历 (resume_educations)
-- ============================================================
INSERT INTO `resume_educations` (`resume_id`, `school`, `major`, `degree`, `start_date`, `end_date`) VALUES
(1, '北京理工大学', '计算机科学与技术', '本科', '2014-09-01', '2018-06-30'),
(2, '北京理工大学', '计算机科学与技术', '本科', '2014-09-01', '2018-06-30');


-- ============================================================
-- 8. 用户行为数据 (applications)
-- ============================================================
INSERT INTO `applications` (`user_id`, `job_id`, `resume_id`, `status`, `match_score`, `redirected_at`, `submitted_at`, `feedback_at`, `click_count`, `external_source`, `note`) VALUES

-- 求职者A 对几个职位的交互
(2, 1, 1, 'favorited', 92.30, '2026-06-12 10:30:00', NULL, '2026-06-12 10:30:00', 2, 'boss',
 '字节的 Python 后端,匹配度非常高,准备投递'),
(2, 5, 1, 'submitted', 78.50, '2026-06-11 14:20:00', '2026-06-11 15:00:00', '2026-06-11 15:00:00', 1, 'boss',
 '已通过 Boss 投递,等 HR 联系'),
(2, 13, 1, 'clicked', 85.00, '2026-06-10 09:15:00', NULL, NULL, 3, NULL, NULL),
(2, 11, 1, 'interviewed', 76.00, '2026-06-08 16:00:00', '2026-06-09 10:00:00', '2026-06-12 11:00:00', 1, 'liepin',
 '京东全栈岗,一面已过,约二面中'),
(2, 7, 2, 'rejected', 65.00, '2026-06-05 11:00:00', '2026-06-05 14:00:00', '2026-06-10 18:00:00', 1, 'liepin',
 '美团大数据岗,经验不够被拒'),
(2, 12, 2, 'clicked', 88.50, '2026-06-13 09:00:00', NULL, NULL, 1, NULL, NULL);


-- ============================================================
-- 9. 推荐记录 (recommendations)
-- ============================================================
INSERT INTO `recommendations` (`user_id`, `resume_id`, `job_id`, `score`, `reason`, `strategy`, `snapshot`, `clicked`) VALUES

-- 基于简历 1 (Python 后端) 的推荐
(2, 1, 1, 92.30, '你的 Python 精通度 5 + 5 年经验,与字节跳动资深 Python 后端岗位高度匹配,FastAPI/MySQL/Redis 全部命中核心要求。',
 'hybrid',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Python','FastAPI','MySQL','Redis','Docker','Git','Linux'),
   'missing_skills', JSON_ARRAY(),
   'matched_must', 3, 'total_must', 3
 ), 1),

(2, 1, 13, 88.50, '小红书 Python 后端岗位,你精通 Python,且有 FastAPI 经验,Redis/Django 也命中,匹配度高。',
 'hybrid',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Python','FastAPI','Django','Redis','ES'),
   'missing_skills', JSON_ARRAY(),
   'matched_must', 2, 'total_must', 2
 ), 1),

(2, 1, 11, 80.20, '京东全栈工程师岗位,你精通 Vue + Python,符合岗位核心要求,Redis/MySQL 也命中。',
 'graph',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Vue','Python','MySQL','Redis'),
   'missing_skills', JSON_ARRAY('Node.js'),
   'matched_must', 2, 'total_must', 3
 ), 1),

(2, 1, 5, 72.00, '腾讯前端 Vue 岗位,你熟悉 Vue,但岗位要求深度前端经验,你的方向是后端,可作为转向考虑。',
 'rag',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Vue','Git'),
   'missing_skills', JSON_ARRAY('TypeScript','JavaScript'),
   'matched_must', 2, 'total_must', 3
 ), 0),

-- 基于简历 2 (机器学习) 的推荐
(2, 2, 2, 89.50, '你的 Python + 机器学习经验,与字节跳动机器学习算法工程师岗位高度匹配,LLM 经验是加分项。',
 'hybrid',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Python','机器学习','深度学习','NLP','LLM'),
   'missing_skills', JSON_ARRAY(),
   'matched_must', 3, 'total_must', 3
 ), 0),

(2, 2, 12, 90.00, '小红书大模型应用工程师岗位,你熟悉 LangChain 思路,LLM 方向匹配度非常高,岗位薪资也优。',
 'hybrid',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Python','LLM','NLP'),
   'missing_skills', JSON_ARRAY(),
   'matched_must', 2, 'total_must', 2
 ), 1),

(2, 2, 14, 82.30, '网易有道 NLP 算法工程师,你的 NLP 经验直接命中,深度学习/Python 也满足。',
 'rag',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Python','NLP','深度学习'),
   'missing_skills', JSON_ARRAY(),
   'matched_must', 3, 'total_must', 3
 ), 0),

(2, 2, 9, 75.50, '拼多多推荐算法专家,你满足 Python + ML 基础,但岗位要求 5 年以上深度经验,可能有挑战。',
 'cold_start',
 JSON_OBJECT(
   'matched_skills', JSON_ARRAY('Python','机器学习'),
   'missing_skills', JSON_ARRAY('深度学习','Spark'),
   'matched_must', 1, 'total_must', 3
 ), 0);


-- ============================================================
-- 完成
-- ============================================================
SELECT
  (SELECT COUNT(*) FROM companies) AS companies_count,
  (SELECT COUNT(*) FROM jobs) AS jobs_count,
  (SELECT COUNT(*) FROM job_skills) AS job_skills_count,
  (SELECT COUNT(*) FROM resumes) AS resumes_count,
  (SELECT COUNT(*) FROM resume_skills) AS resume_skills_count,
  (SELECT COUNT(*) FROM applications) AS applications_count,
  (SELECT COUNT(*) FROM recommendations) AS recommendations_count;
