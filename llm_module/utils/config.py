"""
统一配置管理
支持多模型提供商、智能路由、Agent差异化配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# ==================== MySQL配置 ====================
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "job_competency"),
}

# SQLite配置 (MySQL不可用时使用)
SQLITE_PATH = os.getenv("SQLITE_PATH", str(BASE_DIR / "data" / "job_competency.db"))

# Elasticsearch配置
# 合并后 llm 与主后端共库: 真实 JD 索引由主后端写入维护, 名为 jobs(5000 条), llm 检索对准该索引
ES_CONFIG = {
    "hosts": [os.getenv("ES_HOST", "http://localhost:9200")],
    "index_name": os.getenv("ES_INDEX", "jobs"),
}

# ==================== 大模型配置（自动检测主力提供商） ====================

# 读取环境变量，自动检测主力模型提供商
_LLM_API_KEY = os.getenv("LLM_API_KEY", "")
_LLM_API_BASE = os.getenv("LLM_API_BASE", "")
_LLM_MODEL = os.getenv("LLM_MODEL", "")

# 智谱AI (Zhipu) 主力配置
# 优先使用 ZHIPU_ 前缀的环境变量，否则回退到 LLM_ 前缀
ZHIPU_CONFIG = {
    "api_key": os.getenv("ZHIPU_API_KEY", _LLM_API_KEY),
    "api_base": os.getenv("ZHIPU_API_BASE", os.getenv("LLM_API_BASE", "https://open.bigmodel.cn/api/paas/v4")),
    "model": os.getenv("ZHIPU_MODEL", os.getenv("LLM_MODEL", "glm-4-flash")),
    "temperature": float(os.getenv("ZHIPU_TEMPERATURE", "0.3")),
    "max_tokens": int(os.getenv("ZHIPU_MAX_TOKENS", "4096")),
}

# 备选模型配置（降级用）
FALLBACK_CONFIGS = {
    "deepseek": {
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "api_base": os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "kimi": {
        "api_key": os.getenv("KIMI_API_KEY", ""),
        "api_base": os.getenv("KIMI_API_BASE", "https://api.moonshot.cn/v1"),
        "model": os.getenv("KIMI_MODEL", "moonshot-v1-8k"),
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "dashscope": {
        "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
        "api_base": os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "model": os.getenv("DASHSCOPE_MODEL", "qwen-turbo"),
        "temperature": 0.3,
        "max_tokens": 4096,
    },
}

# 讯飞星火配置（特殊认证）
XFYUN_CONFIG = {
    "appid": os.getenv("XFYUN_APPID", ""),
    "apikey": os.getenv("XFYUN_APIKEY", ""),
    "apisecret": os.getenv("XFYUN_APISECRET", ""),
    "api_base": os.getenv("XFYUN_API_BASE", "https://spark-api-open.xf-yun.com/v1"),
    "model": os.getenv("XFYUN_MODEL", "generalv3.5"),
}

# ==================== 智能模型路由配置 ====================

# 智谱GLM模型能力矩阵
ZHIPU_MODELS = {
    "glm-4-flash": {
        "name": "glm-4-flash",
        "tier": "light",
        "json_mode": False,
        "tool_call": False,
        "stream": True,
        "max_tokens": 4096,
        "cost_per_1k": 0.0,  # 免费
        "description": "轻量快速，适合简单任务",
    },
    "glm-4-air": {
        "name": "glm-4-air",
        "tier": "standard",
        "json_mode": False,
        "tool_call": True,
        "stream": True,
        "max_tokens": 4096,
        "cost_per_1k": 0.001,
        "description": "标准版，平衡性能与成本",
    },
    "glm-4": {
        "name": "glm-4",
        "tier": "premium",
        "json_mode": False,
        "tool_call": True,
        "stream": True,
        "max_tokens": 8192,
        "cost_per_1k": 0.005,
        "description": "高精度，适合知识抽取和结构化输出",
    },
    "glm-4-plus": {
        "name": "glm-4-plus",
        "tier": "premium",
        "json_mode": False,
        "tool_call": True,
        "stream": True,
        "max_tokens": 8192,
        "cost_per_1k": 0.01,
        "description": "旗舰版，最强推理和生成能力",
    },
    "glm-4-long": {
        "name": "glm-4-long",
        "tier": "premium",
        "json_mode": False,
        "tool_call": True,
        "stream": True,
        "max_tokens": 16384,
        "cost_per_1k": 0.005,
        "description": "长文本版，适合处理长JD",
    },
    "glm-4-alltools": {
        "name": "glm-4-alltools",
        "tier": "premium",
        "json_mode": False,
        "tool_call": True,
        "stream": True,
        "max_tokens": 4096,
        "cost_per_1k": 0.005,
        "description": "工具调用版，支持联网搜索",
    },
}

# 任务类型到模型的路由映射
MODEL_ROUTER = {
    # 默认配置
    "default": {
        "primary": "glm-4-air",
        "fallback": "glm-4-flash",
        "max_tokens": 4096,
        "temperature": 0.3,
    },
    # 意图识别（轻量、快速）
    "intent_classification": {
        "primary": "glm-4-flash",
        "fallback": "glm-4-air",
        "max_tokens": 512,
        "temperature": 0.1,  # 低温度，确定性输出
        "description": "意图识别，分类任务",
    },
    # 岗位分析（结构化输出）
    "job_analysis": {
        "primary": "glm-4",
        "fallback": "glm-4-air",
        "max_tokens": 4096,
        "temperature": 0.3,
        "json_mode": False,
        "description": "岗位能力分析，需要结构化输出",
    },
    # 技能抽取（结构化输出）
    "skill_extraction": {
        "primary": "glm-4",
        "fallback": "glm-4-air",
        "max_tokens": 2048,
        "temperature": 0.2,
        "json_mode": False,
        "description": "技能关键词抽取，NER任务",
    },
    # 差距分析（推理能力）
    "skill_gap": {
        "primary": "glm-4",
        "fallback": "glm-4-air",
        "max_tokens": 4096,
        "temperature": 0.3,
        "description": "能力差距分析，需要对比推理",
    },
    # 学习路径规划（推理+生成）
    "learning_path": {
        "primary": "glm-4-air",
        "fallback": "glm-4-flash",
        "max_tokens": 4096,
        "temperature": 0.4,  # 稍高温度，生成更丰富的内容
        "description": "学习路径规划，需要创造性",
    },
    # 趋势预测（深度推理）
    "trend_analysis": {
        "primary": "glm-4-plus",
        "fallback": "glm-4",
        "max_tokens": 4096,
        "temperature": 0.3,
        "description": "趋势预测分析，需要深度推理",
    },
    # 报告生成（最强生成能力）
    "report_generation": {
        "primary": "glm-4-plus",
        "fallback": "glm-4",
        "max_tokens": 8192,
        "temperature": 0.3,
        "description": "综合报告生成，需要最强文本能力",
    },
    # 通用问答
    "general_qa": {
        "primary": "glm-4-air",
        "fallback": "glm-4-flash",
        "max_tokens": 2048,
        "temperature": 0.3,
        "description": "通用问答",
    },
    # 岗位对比分析
    "job_compare": {
        "primary": "glm-4",
        "fallback": "glm-4-air",
        "max_tokens": 4096,
        "temperature": 0.3,
        "description": "岗位对比分析，需要多维度对比推理",
    },
    # 简历岗位匹配
    "resume_match": {
        "primary": "glm-4",
        "fallback": "glm-4-air",
        "max_tokens": 4096,
        "temperature": 0.3,
        "description": "简历岗位匹配评估，需要对比推理",
    },
    # 长文本处理
    "long_text": {
        "primary": "glm-4-long",
        "fallback": "glm-4",
        "max_tokens": 16384,
        "temperature": 0.3,
        "description": "长文本处理，如长JD分析",
    },
}

# Agent 模型偏好配置
AGENT_MODEL_CONFIG = {
    "master": {
        "intent_classification": MODEL_ROUTER["intent_classification"],
        "task_decomposition": MODEL_ROUTER["default"],
    },
    "job_analysis": {
        "primary": MODEL_ROUTER["job_analysis"],
    },
    "skill_gap": {
        "primary": MODEL_ROUTER["skill_gap"],
    },
    "learning_path": {
        "primary": MODEL_ROUTER["learning_path"],
    },
    "trend_analysis": {
        "primary": MODEL_ROUTER["trend_analysis"],
    },
    "report_generation": {
        "primary": MODEL_ROUTER["report_generation"],
    },
    "job_compare": {
        "primary": MODEL_ROUTER["job_compare"],
    },
    "resume_match": {
        "primary": MODEL_ROUTER["resume_match"],
    },
}

# ==================== 降级策略配置 ====================

FALLBACK_STRATEGY = {
    # 触发降级的错误码
    "trigger_codes": [401, 429, 500, 502, 503],
    # 触发降级的错误关键词
    "trigger_keywords": [
        "认证失败", "rate limit", "quota exceeded",
        "server error", "bad gateway", "service unavailable",
    ],
    # 自动恢复时间（秒）
    "recovery_time": 300,
    # 最大降级次数
    "max_fallback_count": 3,
    # 降级后是否尝试恢复
    "auto_recovery": True,
}

# ==================== 跨厂商可选模型目录(管理员可切平台默认) ====================
# 智谱是主力; deepseek/kimi/dashscope(标准 OpenAI 兼容 Bearer)与讯飞星火(HMAC 签名)
# 只在各自密钥配齐后才会出现在可选列表里(没 key 不开放, 免得选了个必然 401 的项)。
# 管理员"模型配置"把平台默认切到任一目录内模型后, 生成/分析类任务随默认走, 意图识别仍走廉价智谱。
# 模型名即所选 remote model 名(与智谱 glm-* 无冲突), 端点/密钥由 resolve_model_endpoint 解析。
def _build_extra_provider_models():
    extras = {}
    # 标准 OpenAI 兼容(Bearer Token): deepseek / kimi / dashscope
    for pid, cfg in FALLBACK_CONFIGS.items():
        api_key = (cfg.get("api_key") or "").strip()
        model = (cfg.get("model") or "").strip()
        base = (cfg.get("api_base") or "").strip()
        if not api_key or not model or not base:
            continue
        extras[model] = {
            "name": model,
            "provider": pid,
            "provider_label": {
                "deepseek": "DeepSeek",
                "kimi": "Kimi(Moonshot)",
                "dashscope": "通义千问(阿里)",
            }.get(pid, pid),
            "api_base": base,
            "api_key": api_key,
            "tier": pid,
            "cost_per_1k": 0.0,
            "json_mode": True,
            "tool_call": False,
            "stream": True,
            "max_tokens": int(cfg.get("max_tokens") or 4096),
            "description": f"{pid} 云端 API(OpenAI 兼容), 需该厂商自己的密钥",
        }
    # 讯飞星火: HMAC-SHA256 签名鉴权(三要素齐才开放)
    xf_key = (XFYUN_CONFIG.get("apikey") or "").strip()
    xf_secret = (XFYUN_CONFIG.get("apisecret") or "").strip()
    xf_model = (XFYUN_CONFIG.get("model") or "").strip()
    if xf_key and xf_secret and xf_model:
        extras[xf_model] = {
            "name": xf_model,
            "provider": "xfyun",
            "provider_label": "讯飞星火",
            "api_base": (XFYUN_CONFIG.get("api_base") or "https://spark-api-open.xf-yun.com/v1").strip(),
            "api_key": xf_key,
            "api_secret": xf_secret,
            "appid": (XFYUN_CONFIG.get("appid") or "").strip(),
            "tier": "xfyun",
            "cost_per_1k": 0.0,
            "json_mode": False,
            "tool_call": False,
            "stream": True,
            "max_tokens": 4096,
            "description": "讯飞星火(HMAC-SHA256 鉴权)",
        }
    return extras


EXTRA_MODELS = _build_extra_provider_models()

# 全量可选模型: 智谱 + 已配 key 的其它厂商(供管理员模型配置/路由覆盖校验)
ALL_MODELS = dict(ZHIPU_MODELS)
ALL_MODELS.update(EXTRA_MODELS)


def resolve_model_endpoint(model_name):
    """模型名 → 实际调用的端点信息(provider/api_base/api_key/api_secret/appid/model)。

    非智谱模型返回其厂商端点; 智谱(以及未匹配项)归一到智谱主端点。供 chat/chat_stream 每次按需切底座。
    """
    extra = EXTRA_MODELS.get(model_name)
    if extra:
        return {
            "provider": extra.get("provider"),
            "api_base": extra.get("api_base") or "",
            "api_key": extra.get("api_key") or "",
            "api_secret": extra.get("api_secret") or "",
            "appid": extra.get("appid") or "",
            "model": extra.get("name", model_name),
        }
    return {
        "provider": "zhipu",
        "api_base": ZHIPU_CONFIG["api_base"],
        "api_key": ZHIPU_CONFIG["api_key"],
        "api_secret": "",
        "appid": "",
        "model": model_name,
    }

# ==================== Neo4j配置 ====================
NEO4J_CONFIG = {
    "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "password"),
}

# 向量数据库配置
VECTOR_DB_CONFIG = {
    "path": os.getenv("VECTOR_DB_PATH", str(BASE_DIR / "data" / "vector_db")),
    "collection_name": "job_competency",
}

# 服务配置
SERVER_CONFIG = {
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", 8001)),
    "debug": os.getenv("DEBUG", "false").lower() == "true",
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO").upper(),
    "format": os.getenv("LOG_FORMAT", "text").lower(),  # "text" 或 "json"
    "text_format": os.getenv(
        "LOG_TEXT_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
    ),
    "max_bytes": int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))),
    "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
    "slow_request_threshold": float(os.getenv("SLOW_REQUEST_THRESHOLD", "10.0")),
}

# ==================== 行业本体定义 ====================

INDUSTRY_ONTOLOGY = {
    "it": {
        "entity_types": {
            "job": {
                "sub_types": ["developer", "manager_role", "analyst_role", "designer", "operations"],
                "key_attributes": ["experience_level", "salary_range", "education"],
            },
            "skill": {
                "sub_types": ["programming_language", "framework", "database", "cloud_service", "devops", "soft_skill"],
                "key_attributes": ["proficiency_level", "market_demand"],
            },
            "tool": {
                "sub_types": ["ide", "version_control", "ci_cd", "monitoring"],
                "key_attributes": ["category", "popularity"],
            },
            "certificate": {
                "sub_types": ["cloud_cert", "security_cert", "pm_cert"],
                "key_attributes": ["issuer", "validity"],
            },
        },
        "relation_constraints": {
            ("job", "requires"): ["skill", "tool", "certificate"],
            ("skill", "prerequisite"): ["skill"],
            ("skill", "enhances"): ["skill"],
        },
    },
    "finance": {
        "entity_types": {
            "job": {
                "sub_types": ["finance_role", "analyst_role", "manager_role", "operations"],
                "key_attributes": ["experience_level", "salary_range", "regulatory_requirements"],
            },
            "skill": {
                "sub_types": ["domain_knowledge", "analytical", "management", "certification", "soft_skill"],
                "key_attributes": ["proficiency_level", "regulatory_relevance"],
            },
            "certificate": {
                "sub_types": ["cpa", "cfa", "frm", "securities_license", "insurance_license"],
                "key_attributes": ["issuer", "validity", "jurisdiction"],
            },
        },
        "relation_constraints": {
            ("job", "requires"): ["skill", "certificate"],
            ("certificate", "certifies"): ["skill"],
            ("skill", "prerequisite"): ["skill"],
        },
    },
    "healthcare": {
        "entity_types": {
            "job": {
                "sub_types": ["medical_role", "researcher", "manager_role", "operations"],
                "key_attributes": ["experience_level", "license_required", "specialty"],
            },
            "skill": {
                "sub_types": ["domain_knowledge", "operation_skill", "analytical", "soft_skill", "certification"],
                "key_attributes": ["proficiency_level", "clinical_relevance"],
            },
            "certificate": {
                "sub_types": ["medical_license", "nursing_license", "pharmacy_license", "specialty_cert"],
                "key_attributes": ["issuer", "validity", "specialty"],
            },
        },
        "relation_constraints": {
            ("job", "requires"): ["skill", "certificate"],
            ("certificate", "certifies"): ["skill"],
            ("skill", "prerequisite"): ["skill"],
        },
    },
    "manufacturing": {
        "entity_types": {
            "job": {
                "sub_types": ["engineering", "manager_role", "operations", "analyst_role"],
                "key_attributes": ["experience_level", "safety_cert_required", "specialty"],
            },
            "skill": {
                "sub_types": ["operation_skill", "domain_knowledge", "management", "analytical", "certification"],
                "key_attributes": ["proficiency_level", "safety_relevance"],
            },
            "certificate": {
                "sub_types": ["iso_cert", "safety_cert", "quality_cert"],
                "key_attributes": ["issuer", "validity", "standard"],
            },
        },
        "relation_constraints": {
            ("job", "requires"): ["skill", "certificate", "tool"],
            ("skill", "prerequisite"): ["skill"],
            ("tool", "requires"): ["skill"],
        },
    },
    "education": {
        "entity_types": {
            "job": {
                "sub_types": ["educator", "manager_role", "researcher", "operations"],
                "key_attributes": ["experience_level", "subject", "education_level"],
            },
            "skill": {
                "sub_types": ["teaching_skill", "domain_knowledge", "management", "soft_skill", "certification"],
                "key_attributes": ["proficiency_level", "subject_relevance"],
            },
            "certificate": {
                "sub_types": ["teaching_license", "language_cert", "counseling_cert"],
                "key_attributes": ["issuer", "validity", "level"],
            },
        },
        "relation_constraints": {
            ("job", "requires"): ["skill", "certificate"],
            ("certificate", "certifies"): ["skill"],
            ("skill", "prerequisite"): ["skill"],
        },
    },
}

# ==================== 行业技能关键词配置 ====================

INDUSTRY_SKILL_KEYWORDS = {
    "it": {
        # 编程语言
        "python", "java", "javascript", "js", "typescript", "ts",
        "c++", "c#", "go", "golang", "rust", "scala", "kotlin",
        "php", "ruby", "swift", "dart", "r语言",
        # 前端
        "react", "vue", "angular", "html", "css", "jquery",
        "bootstrap", "webpack", "vite", "next.js", "nuxt",
        # 后端
        "django", "flask", "fastapi", "spring", "springboot",
        "express", "koa", "nestjs",
        # 数据库
        "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "oracle", "sqlserver", "sqlite", "neo4j",
        # 大数据
        "hadoop", "spark", "flink", "kafka", "hive", "hbase",
        "etl", "数据仓库",
        # AI/ML
        "tensorflow", "pytorch", "sklearn", "机器学习", "深度学习",
        "nlp", "计算机视觉", "cv",
        # 运维
        "docker", "kubernetes", "k8s", "jenkins", "gitlab",
        "aws", "azure", "阿里云", "腾讯云",
        # 其他
        "git", "linux", "restful", "graphql", "微服务", "分布式",
    },
    "finance": {
        # 金融产品
        "股票", "债券", "基金", "期货", "期权", "外汇", "理财产品",
        "信托", "资管", "投行", "风控", "合规",
        # 金融系统
        "交易系统", "结算系统", "清算", "核心银行", "支付系统",
        "反洗钱", "aml", "kyc",
        # 分析工具
        "bloomberg", "wind", "万得", "同花顺", "excel", "vba",
        "sql", "python", "r", "sas", "spss",
        # 证书
        "cpa", "cfa", "frm", "acca", "证券从业", "基金从业",
        # 法规
        "巴塞尔", "银保监", "证监会", "金融监管",
    },
    "healthcare": {
        # 临床技能
        "临床诊断", "病历书写", "处方", "手术", "护理", "急救",
        "影像诊断", "病理", "检验", "药学",
        # 医疗系统
        "his", "pacs", "lis", "emr", "电子病历", "医院信息系统",
        # 医疗设备
        "ct", "mri", "超声", "x光", "心电图", "监护仪",
        # 证书
        "执业医师", "执业护士", "执业药师", "规培",
        # 法规
        "医疗法规", "gmp", "gsp", "医疗器械", "药品管理",
    },
    "manufacturing": {
        # 工艺
        "工艺流程", "生产管理", "精益生产", "六西格玛", "5s",
        "质量管理", "qc", "qa", "spc", "fmea",
        # 设备
        "cnc", "plc", "scada", "dcs", "mes", "erp",
        "cad", "cam", "cae", "solidworks", "autocad",
        # 体系
        "iso9001", "iso14001", "ts16949", "ohsas",
        # 供应链
        "供应链", "采购", "仓储", "物流", "物料管理",
        # 安全
        "安全生产", "ehs", "危险品管理", "消防",
    },
    "education": {
        # 教学方法
        "教学法", "课程设计", "教学评估", "课堂管理", "差异化教学",
        "项目式学习", "翻转课堂", "混合式教学",
        # 教育技术
        "在线教育", "慕课", "微课", "直播教学", "智慧课堂",
        "lms", "moodle", "canvas", "blackboard",
        # 学科
        "语文", "数学", "英语", "物理", "化学", "生物",
        # 证书
        "教师资格", "普通话", "心理咨询师",
        # 评估
        "形成性评价", "总结性评价", "rubric",
    },
}

# 默认行业（未指定行业时使用）
DEFAULT_INDUSTRY = "it"

# ==================== 行业Prompt上下文配置 ====================

INDUSTRY_PROMPT_CONTEXT = {
    "it": {
        "skill_categories": "编程语言、框架工具、数据库、云服务、DevOps",
        "skill_examples": "如Python、Java、React、MySQL、Docker等",
        "career_path_examples": "初级开发→中级开发→高级开发→架构师→技术总监",
        "industry_name": "IT/互联网",
    },
    "finance": {
        "skill_categories": "金融产品、风控模型、合规法规、交易系统、数据分析",
        "skill_examples": "如CPA、CFA、Bloomberg、Wind、反洗钱系统等",
        "career_path_examples": "分析师→高级分析师→经理→总监→合伙人",
        "industry_name": "金融",
    },
    "healthcare": {
        "skill_categories": "临床技能、医疗设备、药品知识、病历系统、医疗法规",
        "skill_examples": "如执业医师证、HIS系统、CT/MRI操作、GMP规范等",
        "career_path_examples": "住院医师→主治医师→副主任医师→主任医师",
        "industry_name": "医疗/医药",
    },
    "manufacturing": {
        "skill_categories": "工艺流程、质量体系、设备操作、供应链管理、安全规范",
        "skill_examples": "如六西格玛、ISO9001、CNC/PLC、MES/ERP等",
        "career_path_examples": "技术员→工程师→高级工程师→主任工程师→总工程师",
        "industry_name": "制造/工业",
    },
    "education": {
        "skill_categories": "教学方法、课程设计、教育技术、学科知识、评估体系",
        "skill_examples": "如教师资格证、LMS平台、项目式学习、翻转课堂等",
        "career_path_examples": "助教→讲师→副教授→教授",
        "industry_name": "教育",
    },
}

# ==================== 向后兼容（保留旧配置） ====================

# 旧版 LLM_CONFIG（兼容用）
LLM_CONFIG = {
    "api_key": ZHIPU_CONFIG["api_key"],
    "api_base": ZHIPU_CONFIG["api_base"],
    "model": ZHIPU_CONFIG["model"],
    "temperature": ZHIPU_CONFIG["temperature"],
    "max_tokens": ZHIPU_CONFIG["max_tokens"],
}

# ==================== 限流与并发配置 ====================

RATE_LIMIT_CONFIG = {
    "enabled": os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    "max_requests_per_minute": int(os.getenv("RATE_LIMIT_MAX", "60")),
    "max_concurrent_agents": int(os.getenv("MAX_CONCURRENT_AGENTS", "5")),
}

# ==================== 多模式角色配置 ====================

ROLE_CONFIG = {
    "job_seeker": {
        "name": "求职者",
        "description": "关注技能差距、学习路径、岗位匹配",
        "default_intents": ["skill_gap", "learning_path", "job_analysis"],
        "prompt_style": "鼓励式，侧重个人发展",
    },
    "hr": {
        "name": "HR/招聘者",
        "description": "关注岗位分析、人才评估、市场趋势",
        "default_intents": ["job_analysis", "trend_prediction", "resume_match"],
        "prompt_style": "专业式，侧重人才筛选",
    },
    "career_planner": {
        "name": "职业规划师",
        "description": "关注跨行业转型、长期规划、认证路径",
        "default_intents": ["learning_path", "skill_gap", "trend_prediction"],
        "prompt_style": "顾问式，侧重长期规划",
    },
    "manager": {
        "name": "企业管理者",
        "description": "关注团队能力矩阵、培训需求、行业对标",
        "default_intents": ["job_analysis", "trend_prediction", "report_generation"],
        "prompt_style": "报告式，侧重决策支撑",
    },
}

DEFAULT_ROLE = "job_seeker"

# ==================== 认证配置 ====================

AUTH_CONFIG = {
    # 与 backend 用同一个环境变量名 JWT_SECRET_KEY, 保证两服务密钥一致
    # (JWT 是无状态验签, 密钥不同则互相验签必失败)
    # 仍兼容旧的 AUTH_SECRET_KEY, 便于平滑迁移
    "secret_key": os.getenv("JWT_SECRET_KEY", os.getenv("AUTH_SECRET_KEY", "9a53ef343042c90b248f593637aaeb21f83d9df265b7c213eac3683e12f87444")),
    "algorithm": os.getenv("AUTH_ALGORITHM", "HS256"),
    "access_token_expire_minutes": int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    "refresh_token_expire_days": int(os.getenv("AUTH_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
}

# ==================== 资源配额配置 ====================

QUOTA_CONFIG = {
    "enabled": os.getenv("QUOTA_ENABLED", "true").lower() == "true",
    "default_daily_calls": int(os.getenv("QUOTA_DAILY_CALLS", "100")),
    "default_daily_tokens": int(os.getenv("QUOTA_DAILY_TOKENS", "50000")),
    "admin_daily_calls": int(os.getenv("QUOTA_ADMIN_DAILY_CALLS", "10000")),
    "admin_daily_tokens": int(os.getenv("QUOTA_ADMIN_DAILY_TOKENS", "500000")),
}

# ==================== 健康检查配置 ====================

HEALTH_CONFIG = {
    "llm_probe_enabled": os.getenv("HEALTH_LLM_PROBE_ENABLED", "true").lower() == "true",
    "llm_probe_interval_seconds": int(os.getenv("HEALTH_LLM_PROBE_INTERVAL", "300")),
    "llm_probe_prompt": "Hi",
}

# ==================== 成本预算配置 ====================

COST_BUDGET_CONFIG = {
    "enabled": os.getenv("COST_BUDGET_ENABLED", "true").lower() == "true",
    "daily_budget": float(os.getenv("COST_BUDGET_DAILY", "10.0")),  # 每日成本上限（元）
    "monthly_budget": float(os.getenv("COST_BUDGET_MONTHLY", "200.0")),  # 每月成本上限（元）
    "warning_threshold": float(os.getenv("COST_BUDGET_WARNING_THRESHOLD", "0.8")),  # 预警阈值（80%）
    "auto_degrade": os.getenv("COST_BUDGET_AUTO_DEGRADE", "true").lower() == "true",  # 接近上限时自动降级
}

# ==================== 简历解析配置 ====================

UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads" / "resumes"))

RESUME_ANALYZE_CONFIG = {
    # 允许的文件扩展名
    "allowed_pdf_ext": {".pdf"},
    "allowed_image_ext": {".png", ".jpg", ".jpeg", ".webp", ".bmp"},
    # 单文件大小上限（字节），默认 10MB
    "max_file_size": int(os.getenv("RESUME_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
    # OCR 开关：装了 pytesseract 才会真正启用
    "ocr_enabled": os.getenv("RESUME_OCR_ENABLED", "true").lower() == "true",
    # LLM 任务类型（复用 MODEL_ROUTER；skill_extraction 用 glm-4，结构化输出能力好）
    "llm_task_type": os.getenv("RESUME_LLM_TASK_TYPE", "skill_extraction"),
    # 是否开启 JSON 模式
    "use_json_mode": os.getenv("RESUME_JSON_MODE", "true").lower() == "true",
}
