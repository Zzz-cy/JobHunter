"""
Prompt模板库 - 用于大模型知识抽取和问答
"""

# 岗位能力抽取Prompt
JOB_EXTRACTION_PROMPT = """你是一位专业的人力资源分析专家。请从以下岗位描述(JD)中抽取结构化的岗位能力信息。

【岗位描述】
{jd_text}

请按照以下JSON格式输出抽取结果：
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "实体类型(job/skill/knowledge/certificate/tool/industry)",
            "properties": {{"key": "value"}}
        }}
    ],
    "relations": [
        {{
            "source": "源实体",
            "target": "目标实体",
            "type": "关系类型(requires/leads_to/similar_to/prerequisite/belongs_to)"
        }}
    ]
}}

注意：
1. 实体类型必须是以下之一：job(岗位), skill(技能), knowledge(知识点), certificate(证书), tool(工具), industry(行业)
2. 关系类型必须是：requires(要求), leads_to(晋升路径), similar_to(相似), prerequisite(前置), belongs_to(属于)
3. 只输出JSON，不要其他内容
"""

# 技能差距分析Prompt
SKILL_GAP_PROMPT = """你是一位职业规划顾问。请根据用户的当前技能和目标岗位，分析技能差距。

【用户当前技能】
{current_skills}

【目标岗位】
{target_job}

请分析：
1. 用户已具备的优势技能
2. 用户需要补充的关键技能
3. 建议的学习路径和优先级
4. 预计达到目标岗位所需时间

请用结构化的方式输出分析结果。
"""

# 智能问答Prompt
QA_PROMPT = """你是一位专业的人力资源智能助手，精通各行业的岗位能力要求。
请根据以下上下文回答用户问题。如果上下文不足，请基于你的知识回答。

【上下文信息】
{context}

【用户问题】
{question}

请用中文回答，保持简洁专业。如果涉及具体数据，请给出明确的来源或依据。
"""

# 岗位匹配度评估Prompt
JOB_MATCH_PROMPT = """请评估以下候选人与岗位的匹配度。

【岗位信息】
{job_info}

【候选人信息】
{candidate_info}

请从以下维度评估（每项0-100分）：
1. 技能匹配度
2. 经验匹配度
3. 学历匹配度
4. 综合匹配度

并给出：
- 匹配优势
- 潜在风险
- 面试建议
"""

# 知识图谱问答Prompt
KG_QA_PROMPT = """你是一位知识图谱专家。请根据以下知识图谱信息回答用户问题。

【知识图谱信息】
{kg_info}

【用户问题】
{question}

请用中文回答，如果涉及图谱中的实体关系，请尽量引用具体数据。
"""

# 岗位趋势分析Prompt
TREND_ANALYSIS_PROMPT = """请分析以下岗位的市场趋势。

【岗位名称】
{job_title}

【历史数据】
{historical_data}

请分析：
1. 该岗位的需求趋势（上升/下降/稳定）
2. 核心技能要求的变化
3. 薪资水平变化趋势
4. 未来3-5年的发展前景
5. 相关新兴岗位推荐
"""

# 简历解析 Prompt —— 严格 JSON 输出，字段对齐 DATABASE_SCHEMA.md 的 resumes + 子表
RESUME_PARSE_PROMPT = """你是一位专业的简历解析助手。请从以下简历文本中抽取结构化信息。
严格按 JSON 格式输出，不要包含任何多余文字、不要使用 Markdown 代码块。

抽取规则：
1. name: 姓名（必填，抽不到给 null）
2. gender: 性别，0=男 1=女（抽不到 null）
3. age: 年龄（整数，抽不到 null）
4. phone / email: 联系方式（抽不到 null）
5. city: 当前所在城市
6. work_years: 工作年限（整数）。简历直接写年限则用之；未写则按「所有工作经历起止时间的总跨度」推算（含多段经历累加）；应届/无经历为 0。
   示例(必须遵守): 经历为 2020.07-2022.08 与 2022.09-至今 两段 → 总跨度 2020.07 至今 ≈ 4 年 → work_years=4 (不是只算最近一段的 2 年)
7. education: 最高学历，取值之一：大专/本科/硕士/博士
8. expect_salary_min / expect_salary_max: 期望薪资上下限（元/月，整数）
9. expect_city: 期望工作城市
10. expect_job: 期望岗位
11. skills: 技能名称数组（中英文均可，如 ["Python","Docker","MySQL"]）。必须保留简历中的具体技术名，禁止泛化；技能可从工作/项目描述中提取，不只看技能栏。
    示例(必须遵守):
    - 简历写"MySQL 分库分表" → 抽 "MySQL" ✅ (不是 "SQL" ❌)
    - 简历写"Spring Boot 微服务" → 抽 "Spring Boot" ✅ (不是 "Java" ❌)
    - 简历写"用 Vue.js 组件化开发" → 抽 "Vue.js" ✅ (保留原写法)
12. experiences: 工作经历数组，每项含 company_name(公司)、title(职位)、start_date(YYYY-MM-DD)、end_date(YYYY-MM-DD，在职则 null)、description(工作内容)、is_current(0/1)
13. educations: 教育经历数组，每项含 school(学校)、major(专业)、degree(学历)、start_date、end_date

输出 JSON 格式：
{{
  "name": "张三",
  "gender": 0,
  "age": 28,
  "phone": "13800138000",
  "email": "zhangsan@example.com",
  "city": "北京",
  "work_years": 5,
  "education": "本科",
  "expect_salary_min": 20000,
  "expect_salary_max": 30000,
  "expect_city": "北京",
  "expect_job": "高级Python开发工程师",
  "skills": ["Python","Docker"],
  "experiences": [
    {{\"company_name\":\"字节跳动\",\"title\":\"后端工程师\",\"start_date\":\"2022-06-01\",\"end_date\":\"2024-08-01\",\"description\":\"负责订单系统\",\"is_current\":0}}
  ],
  "educations": [
    {{\"school\":\"浙江大学\",\"major\":\"计算机科学与技术\",\"degree\":\"本科\",\"start_date\":\"2018-09-01\",\"end_date\":\"2022-06-01\"}}
  ]
}}

简历文本：
{resume_text}
"""
