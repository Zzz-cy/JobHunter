# 岗能智绘 - 项目演进路线图

> 📌 **说明**：本文档记录了项目从初期到现在的完整演进历史。所有列出的问题已全部修复，所有规划阶段已全部完成。新成员可快速了解项目走过的路和设计决策。

---

## ⚠️ 已知问题与历史错误（必须先修复）

### 🔴 Critical — 模型路由失效
- **问题：** `llm_service.py` 的 `get_model_config()` 中，无论路由选择哪个模型，最终发送给 API 的 model 字段始终被覆盖为 `ZHIPU_CONFIG["model"]`（默认 glm-4-flash），导致所有请求走同一个模型，智能路由形同虚设
- **修复方法：** `_build_payload()` 应使用 `model_config["model"]` 而非 `self.model`
- **已修复：** `_build_payload()` 已使用 `model_config["model"]`，`chat()` 方法正确通过路由获取模型配置

### 🔴 Critical — IT行业硬编码
- **问题1：** `data_pipeline.py` 的 `_extract_skills()` 内置了约70个IT技能关键词（编程语言、框架、数据库、云服务），零个其他行业技能，导致非IT行业的JD完全无法提取技能
- **问题2：** `agent_coordinator.py` 的 `JobAnalysisAgent` prompt 明确要求提取"编程语言、框架工具、数据库"作为技能类别，医疗/金融/制造/教育等行业用户会得到荒谬结果
- **问题3：** 前端6个快捷问题100%是IT方向，无行业选择器，placeholder也是"Python后端开发需要什么技能？"
- **修复方法：** 技能关键词库改为行业感知的动态配置；Agent prompt 注入行业上下文；前端增加行业/职业选择器
- **已修复：** `_extract_skills()` 使用 `INDUSTRY_SKILL_KEYWORDS`；5个子Agent prompt注入 `INDUSTRY_PROMPT_CONTEXT`；前端已有行业/角色选择器+动态快捷问题

### 🟡 High — Agent架构缺陷
- **问题1：** `AgentTask.status` 字段（pending/running/completed/failed）从未在执行过程中更新，状态追踪是摆设
- **问题2：** `WorkflowEngine` 的5种工作流全部只是调用 `master.process()`，没有实现文档描述的差异化流水线拓扑
- **问题3：** `job_compare` 和 `resume_match` 意图被映射到通用Agent，没有专门的对比/简历匹配逻辑
- **问题4：** 意图识别无置信度阈值，confidence=0.1 也直接执行，无澄清/多意图处理
- **问题5：** Agent失败后无重试机制，直接返回错误，无指数退避
- **修复方法：** 问题1：在`_execute_single_task()`中设置running/completed/failed状态；问题2：实现5种差异化工作流拓扑；问题3：新增JobCompareAgent和ResumeMatchAgent；问题4：添加confidence<0.6澄清追问；问题5：添加retry_with_backoff()+熔断器+降级
- **已修复：** 全部5个问题已修复。新增`JobCompareAgent`（岗位对比）和`ResumeMatchAgent`（简历匹配），更新了MasterAgent映射和任务分解逻辑

### 🟡 High — 无结果校验
- **问题：** LLM输出原样接受，无schema校验、无置信度评分、无事实核查、无幻觉检测。`summarize_results()` 直接拼接所有成功结果，垃圾输出也会被包含
- **修复方法：** 每个Agent输出必须经过schema校验 + 置信度评估，低置信度结果触发重试或降级
- **已修复：** `summarize_results()` 已实现空值检查、长度检查、幻觉标记检测、置信度启发式评估

### 🟡 High — 会话管理缺失
- **问题：** API忽略 `session_id`，无对话历史，无用户状态持久化，前端发送 `session_id: 'test-session'` 但后端完全忽略
- **修复方法：** 实现完整的会话管理，支持多轮对话上下文
- **已修复：** `SessionManager` 已实现（创建/获取/销毁/历史/行业上下文/角色），`agent_routes.py` 已集成，会话和消息持久化到MySQL数据库（`sessions_db`+`messages`表），启动时自动从数据库恢复会话

### 🟡 Medium — 成本追踪失效
- **问题：** `ModelCallRecord` 的 `tokens_input`、`tokens_output`、`cost` 始终为0，从未从API响应中提取
- **修复方法：** 从API响应中解析 `usage` 字段填充token数和成本
- **已修复：** `chat()` 方法已从API响应提取 `usage` 字段，计算 `tokens_input/tokens_output/cost`

### 🟡 Medium — 置信度硬编码
- **问题：** `QueryResponse.confidence` 始终为0.8，`qa_engine.py` 中硬编码
- **修复方法：** 基于检索质量、模型输出置信度动态计算
- **已修复：** `answer()` 方法使用动态计算（基线0.5 + 上下文加分 + 长度加分 - 不确定性扣分）

### 🟢 Low — 双次LLM调用
- **问题：** `qa_engine.py` 的 `skill_gap_analysis()` 和 `job_match()` 先让LLM生成自由文本，再让LLM重新格式化为JSON，浪费且不可靠
- **修复方法：** 直接要求LLM输出结构化JSON，或使用 `extract_json()` 方法
- **已修复：** `skill_gap_analysis()/job_match()` 已改为单次调用 + `extract_json()` 直接输出JSON

---

## 第四阶段：核心架构重构（优先级最高）

### 4.1 API接口重新设计
- [x] RESTful API 规范化：统一响应格式 `{code, message, data, request_id, timestamp}`
- [x] 版本化路由：`/api/v1/` 前缀
- [x] 会话管理接口：`POST /api/v1/sessions`、`GET /api/v1/sessions/{id}`、`DELETE /api/v1/sessions/{id}`
- [x] 对话接口支持多轮：`POST /api/v1/sessions/{id}/chat`，携带对话历史
- [x] 流式Agent对话：`GET /api/v1/sessions/{id}/chat/stream`（SSE）
- [x] 用户认证：JWT Token，`POST /api/v1/auth/login`、`POST /api/v1/auth/register`
- [x] 限流：基于用户/Token的请求频率限制（slowapi 或自实现）
- [x] 请求参数校验：Pydantic model 严格校验所有输入
- [x] 统一错误处理：全局异常处理器，错误码体系

### 4.2 数据库设计
- [x] 用户表 `users`：id, username, password_hash, email, industry, role, created_at, updated_at
- [x] 会话表 `sessions`：id, user_id, title, industry_context, created_at, updated_at
- [x] 消息表 `messages`：id, session_id, role(user/assistant/system), content, intent, agent_tasks, latency_ms, created_at
- [x] 评估表 `evaluations`：id, message_id, user_id, auto_score, user_score, user_feedback, intent_accuracy, task_completion, response_quality, created_at
- [x] Agent执行记录表 `agent_executions`：id, request_id, session_id, intent, task_type, model_used, input_tokens, output_tokens, cost, latency_ms, status, retry_count, error_message, created_at
- [x] 技能库表 `skill_taxonomy`：id, name, category, industry, level(junior/mid/senior), description, source
- [x] 行业配置表 `industry_configs`：id, industry_code, industry_name, skill_categories, prompt_overrides, extraction_keywords
- [x] 监控指标表 `metrics`：id, metric_name, metric_value, labels_json, timestamp
- [x] 使用 Alembic 做数据库迁移管理

### 4.3 会话管理
- [x] `SessionManager` 服务：创建/获取/销毁会话
- [x] 对话历史存储：每轮消息持久化到 `messages` 表
- [x] 上下文窗口管理：最近N轮对话作为LLM上下文，超出部分摘要压缩
- [x] 会话级行业上下文：会话创建时确定行业，后续对话自动注入行业prompt
- [x] 会话超时与清理：TTL机制，过期会话自动归档

### 4.4 日志追踪（已完成部分，需增强）
- [x] 分层日志器（llm_module.api, llm_module.services.* 等）
- [x] RotatingFileHandler 日志轮转
- [x] 请求ID中间件（X-Request-ID）
- [x] 环境变量配置日志级别
- [x] 结构化JSON日志输出（可选，通过 LOG_FORMAT=json 切换）
- [x] 全链路Trace：request_id → intent → task → agent → llm_call，每一步都带trace_id
- [x] 慢请求告警：单次请求超过阈值自动记录 WARNING
- [x] 日志聚合：ELK/Loki 集成（部署阶段配置模板已提供，实际集成需部署时配置）

### 4.5 错误兜底
- [x] 全局异常处理器：FastAPI `@app.exception_handler()` 捕获所有未处理异常
- [x] Agent级重试：指数退避（1s → 2s → 4s），最多3次，区分可重试错误（超时/429/500）和不可重试错误（400/401）
- [x] 降级策略：Agent失败后降级为通用问答，而非直接报错
- [x] 熔断器：连续N次失败后暂停该Agent，定时探测恢复
- [x] 超时控制：每个Agent执行设置超时（默认30s），超时自动取消
- [x] 部分结果返回：多任务执行时，部分失败时，返回成功部分 + 失败说明，而非整体失败
- [x] 优雅降级提示：当系统不可用时，返回友好的降级消息而非堆栈信息

### 4.6 多用户并发
- [x] 用户认证与授权（JWT）
- [x] 请求限流（per-user rate limiting）
- [x] 会话隔离：不同用户的会话数据严格隔离
- [x] 连接池管理：LLM API连接池、数据库连接池
- [x] 异步并发控制：`asyncio.Semaphore` 限制同时执行的Agent数量
- [x] 资源配额：每用户每日调用次数/Token用量上限

---

## 第五阶段：Agent智能体升级

### 5.1 意图识别增强
- [x] 置信度阈值：confidence < 0.6 时触发澄清追问（"您是想了解岗位技能要求，还是想评估自己的能力差距？"）
- [x] 多意图识别：支持一个查询包含多个意图（如"对比Python和Java后端技能，并告诉我如何转行"→ job_compare + learning_path）
- [x] 意图识别结果校验：对LLM返回的intent字段做enum校验，非法值降级为 general_qa
- [x] 行业感知意图：根据用户行业上下文调整意图权重（如医疗行业用户更可能问"执业资格"而非"编程语言"）

### 5.2 任务规划
- [x] 动态任务分解：LLM根据查询复杂度决定子任务数量和依赖关系，而非硬编码映射
- [x] 任务依赖DAG：支持串行/并行/条件分支执行拓扑
- [x] 任务优先级排序：关键路径任务优先执行
- [x] 任务状态实时更新：pending → running → completed/failed，每次状态变更记录时间戳
- [x] 任务超时与取消：每个任务设置独立超时

### 5.3 工具选择
- [x] 定义工具注册表：每个工具声明 name、description、parameters schema、适用场景
- [x] 可用工具列表：
  - `knowledge_search`：向量检索知识库
  - `graph_query`：Neo4j知识图谱查询
  - `skill_database`：技能库查询
  - `jd_parser`：JD结构化解析
- [x] `web_search`：联网搜索（可选）
- [x] `calculator`：数值计算（薪资对比等）
- [x] LLM工具选择：根据任务类型和上下文，让LLM决定调用哪些工具
- [x] 工具执行结果注入：工具返回结果作为Agent的补充上下文,dan

### 5.4 状态追踪
- [x] `AgentTask.status` 实时更新：在 `_execute_single_task()` 中设置 running/completed/failed
- [x] 执行时间记录：每个任务的开始时间、结束时间、耗时
- [x] 中间结果缓存：已完成任务的结果可被后续任务引用
- [x] 状态持久化：任务状态写入 `agent_executions` 表，支持断点恢复
- [x] 前端实时状态推送：WebSocket/SSE 推送任务执行进度

### 5.5 失败重试
- [x] 可重试错误判定：超时、429、500/502/503 → 可重试；400/401/403 → 不可重试
- [x] 指数退避：1s → 2s → 4s，最大3次重试
- [x] 重试时模型降级：主模型失败后尝试备选模型
- [x] 重试时prompt简化：重试时缩短prompt减少token消耗
- [x] 重试计数与日志：每次重试记录 retry_count 和原因

### 5.6 结果校验
- [x] Schema校验：每个Agent输出必须符合预定义的Pydantic schema
- [x] 置信度评估：LLM自评 + 规则校验双重打分
- [x] 事实核查：关键事实（技能名称、薪资范围）与知识库交叉验证
- [x] 幻觉检测：输出中与输入无关的"创造性"内容标记为低置信度
- [x] 校验失败处理：低置信度结果触发重试或降级，高置信度结果直接返回
- [x] 结果质量评分：自动评分写入 `evaluations` 表

---

## 第六阶段：行业泛化与角色定位

### 6.1 行业配置体系
- [x] 行业枚举定义：IT/互联网、金融、医疗/医药、制造/工业、教育、法律、建筑/工程、零售/消费、能源/环保、政府/公共事业
- [x] 每个行业的技能类别映射：
  - IT：编程语言、框架、数据库、云服务、DevOps
  - 金融：金融产品、风控模型、合规法规、交易系统、数据分析
  - 医疗：临床技能、医疗设备、药品知识、病历系统、医疗法规
  - 制造：工艺流程、质量体系、设备操作、供应链、安全规范
  - 教育：教学方法、课程设计、教育技术、学科知识、评估体系
- [x] 行业感知的技能关键词库：替换 `data_pipeline.py` 中硬编码的IT关键词
- [x] 行业感知的Prompt模板：每个Agent根据行业上下文动态调整prompt

### 6.2 前端去IT化
- [x] 行业选择器：首页/会话创建时选择行业领域
- [x] 行业感知的快捷问题：根据所选行业动态展示相关问题
- [x] 通用化placeholder：改为"输入你的职业相关问题..."
- [x] Agent标签通用化：显示通用功能标签（分析/对比/规划/预测/报告/匹配/问答），不显示特定职业状态
- [x] 模型状态动态显示：从后端获取当前模型信息而非硬编码

### 6.3 多模式角色定位
- [x] 求职者模式：关注技能差距、学习路径、岗位匹配
- [x] HR/招聘者模式：关注岗位分析、人才评估、市场趋势
- [x] 职业规划师模式：关注跨行业转型、长期规划、认证路径
- [x] 企业管理者模式：关注团队能力矩阵、培训需求、行业对标
- [x] 每种模式有不同的默认意图权重、prompt风格、输出格式

---

## 第七阶段：全链路监控与可视化

### 7.1 监控指标采集
- [x] 请求级指标：请求总量、成功率、P50/P90/P99延迟、错误率
- [x] Agent级指标：各Agent调用次数、成功率、平均耗时、重试率
- [x] LLM级指标：各模型调用量、Token消耗、成本、延迟、错误率
- [x] 意图识别指标：各意图分布、识别准确率、低置信度比例
- [x] 业务指标：会话数、活跃用户数、平均对话轮数、用户满意度
- [x] 指标存储：写入 `metrics` 表，支持 Prometheus 格式导出

### 7.2 全链路追踪
- [x] 每个请求生成 trace_id（复用 request_id）
- [x] 追踪链路：request → auth → intent → plan → agent_1 → tool_call → llm → validate → agent_2 → ... → response
- [x] 每个环节记录：trace_id、span_id、parent_span_id、开始时间、结束时间、状态、错误信息
- [x] 追踪数据写入 `agent_executions` 表
- [x] 慢请求自动标记：单次请求 > 10s 记录为慢请求

### 7.3 可视化大盘
- [x] 后端提供监控数据API：`GET /api/v1/admin/metrics`、`GET /api/v1/admin/traces`
- [x] 前端管理页面（`frontend/admin.html`）：
  - 请求概览：实时QPS、成功率、延迟分布
  - Agent看板：各Agent成功率/耗时统计
  - LLM看板：模型调用量/成本/Token趋势
  - 意图分布：饼图/柱状图
  - 错误分析：错误类型分布
  - 追踪详情：单请求全链路时间线
- [x] 告警规则（`services/metrics_service.py` AlertEngine）：
  - 错误率 > 5% → critical
  - P99延迟 > 30s → warning
  - Agent连续失败 > 3次 → critical
  - LLM日成本 > 预算80% → warning
  - 意图识别低置信度比例 > 30% → info

### 7.4 健康检查增强
- [x] `/health` 接口返回各组件详细状态：LLM连通性、数据库、Neo4j、ChromaDB
- [x] `/health/ready` 就绪检查（所有依赖可用）
- [x] `/health/live` 存活检查（进程存活）
- [x] LLM连通性探测：定期向LLM API发送轻量请求验证可用性

---

## 第八阶段：自动化评价与优化闭环

### 8.1 自动化评价体系
- [x] 评价维度定义：
  - **意图准确率**：识别的意图是否是用户真实意图
  - **任务完成度**：是否完整回答了用户问题
  - **事实准确率**：输出中的事实是否可验证
  - **结构化质量**：JSON输出是否符合schema
  - **响应相关性**：回答是否与问题相关
  - **信息完整度**：是否遗漏关键信息
- [x] 自动评分引擎：
  - LLM-as-Judge：用独立LLM对输出打分（1-5分）
  - 规则评分：schema校验通过+1，包含关键实体+1，无幻觉标记+1
  - 检索质量评分：RAG检索结果与问题的相似度
- [x] 批量评价流水线：
  - 构建标准测试集：每个意图20+条标准query + 期望输出
  - 定时跑批：每日自动运行测试集，计算各维度得分
  - 回归检测：新版本上线前自动对比历史得分

### 8.2 用户真实反馈
- [x] 前端反馈组件：每条回复下方 👍/👎 按钮 + 可选文字反馈
- [x] 反馈API：`POST /api/v1/evaluations`，记录 user_score（1-5）和 user_feedback
- [x] 反馈与自动评分关联：对比用户评分与自动评分，校准自动评分模型
- [x] 低分样本收集：user_score ≤ 2 的样本自动标记为优化候选

### 8.3 低分反哺优化
- [x] 低分样本分析：自动归类失败原因（意图识别错误/任务规划不当/LLM输出质量差/工具调用失败）
- [x] Prompt优化：根据失败模式自动生成prompt改进建议
- [x] 测试集扩充：低分样本加入测试集，防止回归
- [x] 模型路由优化：某模型在特定任务上持续低分 → 调整路由策略
- [x] 优化效果验证：每次优化后重新跑批，确认得分提升

### 8.4 A/B测试框架
- [x] 实验配置：定义实验组（新prompt/新模型/新策略）和对照组
- [x] 流量分配：按用户/会话随机分流
- [x] 指标对比：两组的自动评分和用户评分对比
- [x] 统计显著性：计算p值，确认改进非偶然
- [x] 自动推广：实验组显著优于对照组时，自动切换为默认配置

---

## 第九阶段：大模型优化专项

### 9.1 Prompt工程优化
- [x] 行业感知Prompt：根据用户行业动态注入领域知识
- [x] Few-shot示例库：每个意图准备3-5个高质量示例
- [x] Chain-of-Thought：复杂推理任务启用思维链
- [x] 输出格式约束：强制JSON输出，减少解析失败
- [x] Prompt版本管理：每次prompt变更记录版本号和效果对比
- [x] 反prompt注入：防止用户输入干扰系统指令

### 9.2 模型路由优化
- [x] 修复路由Bug：`_build_payload()` 使用 `model_config["model"]` 而非 `self.model`
- [x] 动态路由：根据当前模型负载和延迟动态选择
- [x] 成本优化：简单任务用便宜模型，复杂任务用强模型
- [x] Token用量追踪：从API响应中提取 `usage` 字段
- [x] 成本预算：设置每日/每月成本上限，接近上限时自动降级

### 9.3 RAG优化
- [x] 检索质量评估：计算query与检索结果的相似度分布
- [x] 混合检索：向量检索 + 关键词检索 + 图谱检索融合
- [x] 重排序：检索结果用LLM重排序，提升相关性
- [x] 知识库更新：支持增量更新，定期全量重建索引
- [x] 行业知识库分区：不同行业的文档分collection存储

### 9.4 知识图谱增强
- [x] 行业本体定义：每个行业的实体类型、子类型和关系约束（`models/schemas.py` ONTOLOGY_CONSTRAINTS + `utils/config.py` INDUSTRY_ONTOLOGY）
- [x] 图谱质量校验：实体模糊去重、关系一致性检查、孤立节点检测、置信度过滤、冲突检测、引用完整性（`core/kg_builder.py` validate_graph/fix_common_issues）
- [x] 图谱推理：传递推理、路径推理、类比推理、职业路径推理（`services/neo4j_service.py` infer_*方法）
- [x] 图谱可视化：Cytoscape.js格式API端点 + 图谱校验/修复/推理API（`api/main.py` /kg/visualize/*、/kg/validate、/kg/infer/*）

---

## 第十阶段：部署与运维

- [x] Docker容器化：Dockerfile + docker-compose.yml + Dockerfile.frontend + .dockerignore
- [x] 环境配置分离：.env.dev / .env.staging / .env.prod 三套环境配置
- [x] CI/CD流水线：GitHub Actions 代码检查 → 单元测试 → Docker构建 → 部署（`.github/workflows/ci-cd.yml`）
- [x] 压力测试：Locust压测脚本（`locustfile.py`），模拟多用户并发聊天和工作流
- [x] API文档：FastAPI自动生成 /docs + /redoc，.env.example 完整配置说明
- [x] 日志聚合：结构化JSON日志 + Prometheus格式导出，部署时接入ELK/Loki
- [x] 监控告警：AlertEngine内置5条告警规则 + /api/v1/admin/alerts API + 管理后台
- [x] 数据备份：Docker Volume持久化 + 数据库数据目录映射
- [x] 安全加固：CORS白名单配置、SQL注入防护、XSS防护（`utils/security.py` InputSanitizer）、安全响应头

---

## 实施优先级排序

| 优先级 | 阶段 | 关键任务 | 预计工期 |
|--------|------|----------|----------|
| P0 | 4.1-4.2 | API重设计 + 数据库设计 | 1周 |
| P0 | 修复 | 模型路由Bug修复 | 0.5天 |
| P0 | 修复 | IT硬编码去除（data_pipeline + agent prompt） | 1天 |
| P1 | 4.3 | 会话管理 | 3天 |
| P1 | 4.5 | 错误兜底（重试/降级/熔断） | 3天 |
| P1 | 5.1-5.6 | Agent升级（意图/规划/工具/状态/重试/校验） | 1.5周 |
| P1 | 6.1-6.3 | 行业泛化 + 角色定位 | 1周 |
| P2 | 4.4 | 日志追踪增强 | 2天 |
| P2 | 4.6 | 多用户并发 | 3天 |
| P2 | 7.1-7.4 | 全链路监控 + 可视化 | 1.5周 |
| P3 | 8.1-8.4 | 自动化评价 + 优化闭环 | 2周 |
| P3 | 9.1-9.4 | 大模型优化专项 | 持续迭代 |
| P4 | 10 | 部署与运维 | 1周 |

---

## 项目注意事项

1. **Python 版本**：生产环境使用 Docker（Python 3.11-slim），本地开发建议 Python ≥ 3.10。代码中使用了 `from __future__ import annotations` 确保兼容性
2. **循环导入风险**：`logger.py` 不能从 `config.py` 导入（config先于logger被导入），logger直接读 `os.getenv()`
3. **单例模式**：`llm_service`、`vector_store`、`neo4j_service` 等都使用模块级单例，重置单例需 `module._instance = None`
4. **异步一致性**：所有LLM调用和API处理都是async，新增代码必须保持async，不能混用同步阻塞调用
5. **依赖最小化**：项目刻意不引入LangGraph等重依赖，新增功能应保持轻量，优先用标准库和已有依赖
6. **配置集中化**：所有配置项必须在 `utils/config.py` 和 `.env.example` 中声明，不能散落在代码中
7. **向后兼容**：API变更需保留旧接口至少一个版本周期，通过版本化路由（/api/v1/、/api/v2/）管理

---

## 当前状态

✅ **所有规划阶段（第四至第十阶段）已全部完成。** 本文档作为项目历史演进记录保留，新增功能请在 `docs/` 目录或新文档中记录。

---

## 补充问题：当前待解决诉求（2026-07-27）

> 以下为近期开发中发现的遗留问题和新需求，尚未实施。

### 🔴 P0 — 监控后台权限控制缺失

**现状**：`/admin` 路由和 `/api/v1/admin/*` 接口完全裸奔，任何人无需登录即可访问监控数据（请求量、LLM 成本、错误详情、追踪链路、告警规则等敏感运营数据）。

**具体问题**：

1. **前端无登录页**：整个前端没有 `LoginView.vue`，没有令牌存储/注入，`request.js` 不附加 `Authorization` 头
2. **前端路由无守卫**：`router/index.js` 没有 `beforeEach`，`/admin` 和 `/` 完全平等，直接输入 URL 即可访问
3. **后端 admin 接口无权限校验**：所有 `/api/v1/admin/*` 接口不检查认证和角色，匿名请求直接返回数据
4. **认证中间件不强制**：`auth_context_middleware` 是"尽力而为"模式，认证失败不拦截，继续放行
5. **没有 `admin` 角色**：现有 4 个角色（job_seeker/hr/career_planner/manager）都是业务角色，`manager` 只是"企业管理者"用户（配额高一点），不是系统管理员
6. **注册接口角色漏洞**：`POST /api/v1/auth/register` 允许客户端传 `role` 参数（含 `manager`），服务端不做任何校验就接受，任何人都能注册为 manager

**待实施方案**：

- [ ] 新增 `admin` 角色到 `ROLE_CONFIG` 和 `AGENT_MODEL_CONFIG`
- [ ] 后端新增 `require_admin` 依赖（检查 JWT 中 `role=admin`，否则返回 403）
- [ ] 后端所有 `/api/v1/admin/*` 接口挂上 `require_admin`
- [ ] 后端注册接口禁止客户端传 `role=admin`，admin 只能由脚本/后台创建
- [ ] 前端新建 `LoginView.vue` 登录页（用户名 + 密码 → 获取 JWT → 存 localStorage）
- [ ] 前端 `request.js` 从 localStorage 读取 token 并注入 `Authorization: Bearer <token>`
- [ ] 前端 `router/index.js` 添加 `beforeEach` 守卫：`/admin` 要求 `role=admin`，否则跳登录页
- [ ] 前端导航栏根据登录状态显示用户信息，管理员才显示"📊 管理"入口
- [ ] 初始化脚本：创建默认管理员账号（如 `admin/admin123`）

### 🟡 P1 — 端口统一已完成，配置残留需注意

**已解决**：后端端口从 8000 统一改为 5173（12 个文件全部更新），前端 Vite 用 3000 端口代理到 5173。`start_frontend.py` 已修复超时检测（改为 HTTP 健康检查）和 Windows 兼容性（GBK 编码、npx shell 模式）。

**需注意**：如果团队成员本地 `.env` 还是旧版（`PORT=8000`），需手动更新或重新从 `.env.example` 复制。

### 🟡 P1 — 启动依赖超时问题已修复

**已解决**：
- `.env` 中 `MYSQL_USER=1`（错误用户名）已改为 `root`；末尾重复的 `MYSQL_PASSWORD` 覆盖已清除
- `neo4j_service.py` 新增 `_is_port_open()` 端口预检测（1 秒超时），端口不可达时跳过连接，不再等待 Neo4j 驱动 4 秒超时
- `db_service.py` MySQL 连接超时从 5 秒降为 3 秒

**需注意**：Neo4j 和 MySQL 目前未运行，服务以降级模式启动（内存存储 / SQLite）。如需完整功能，需通过 Docker 启动依赖服务。
