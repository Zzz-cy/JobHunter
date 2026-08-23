"""
数据模型定义 - 使用Pydantic进行数据校验
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class EntityType(str, Enum):
    """实体类型"""
    JOB = "job"              # 岗位
    SKILL = "skill"          # 技能
    KNOWLEDGE = "knowledge"  # 知识点
    CERTIFICATE = "certificate"  # 证书
    TOOL = "tool"            # 工具
    INDUSTRY = "industry"    # 行业


class SkillSubType(str, Enum):
    """技能子类型 - 层级化本体"""
    PROGRAMMING_LANGUAGE = "programming_language"  # 编程语言
    FRAMEWORK = "framework"                        # 框架
    DATABASE = "database"                          # 数据库
    CLOUD_SERVICE = "cloud_service"                # 云服务
    DEVOPS = "devops"                              # 运维工具
    SOFT_SKILL = "soft_skill"                      # 软技能
    DOMAIN_KNOWLEDGE = "domain_knowledge"          # 领域知识
    ANALYTICAL = "analytical"                      # 分析能力
    MANAGEMENT = "management"                      # 管理能力
    CERTIFICATION = "certification"                # 资质认证
    OPERATION_SKILL = "operation_skill"            # 操作技能
    TEACHING_SKILL = "teaching_skill"              # 教学技能


class JobSubType(str, Enum):
    """岗位子类型 - 层级化本体"""
    DEVELOPER = "developer"            # 开发岗
    MANAGER_ROLE = "manager_role"      # 管理岗
    ANALYST_ROLE = "analyst_role"      # 分析岗
    DESIGNER = "designer"              # 设计岗
    OPERATIONS = "operations"          # 运营岗
    RESEARCHER = "researcher"          # 研究岗
    EDUCATOR = "educator"              # 教育岗
    MEDICAL_ROLE = "medical_role"      # 医疗岗
    FINANCE_ROLE = "finance_role"      # 金融岗
    ENGINEERING = "engineering"        # 工程岗


class RelationType(str, Enum):
    """关系类型"""
    REQUIRES = "requires"           # 要求（岗位->技能）
    LEADS_TO = "leads_to"           # 晋升路径（岗位->岗位）
    SIMILAR_TO = "similar_to"       # 相似（技能->技能）
    PREREQUISITE = "prerequisite"   # 前置（技能->技能）
    BELONGS_TO = "belongs_to"       # 属于（岗位->行业）
    ENHANCES = "enhances"           # 增强（技能->技能）
    CERTIFIES = "certifies"         # 认证（证书->技能）
    SUPERSEDES = "supersedes"       # 替代（技能->技能，新技能替代旧技能）


# 本体约束：定义哪些关系类型可以连接哪些实体类型对
ONTOLOGY_CONSTRAINTS = {
    # (source_type, relation_type) -> [allowed_target_types]
    ("job", "requires"): ["skill", "knowledge", "certificate", "tool"],
    ("job", "leads_to"): ["job"],
    ("job", "belongs_to"): ["industry"],
    ("skill", "prerequisite"): ["skill"],
    ("skill", "similar_to"): ["skill"],
    ("skill", "enhances"): ["skill"],
    ("skill", "supersedes"): ["skill"],
    ("certificate", "certifies"): ["skill"],
    ("tool", "requires"): ["skill"],
    ("industry", "requires"): ["skill"],
}


class Entity(BaseModel):
    """知识图谱实体"""
    id: Optional[str] = None
    name: str = Field(..., description="实体名称")
    type: EntityType = Field(..., description="实体类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="其他属性")


class Relation(BaseModel):
    """知识图谱关系"""
    source: str = Field(..., description="源实体名称")
    target: str = Field(..., description="目标实体名称")
    type: RelationType = Field(..., description="关系类型")
    confidence: float = Field(default=1.0, ge=0, le=1, description="置信度")


class ExtractedKnowledge(BaseModel):
    """从文本抽取的知识"""
    entities: List[Entity] = Field(default_factory=list, description="抽取的实体")
    relations: List[Relation] = Field(default_factory=list, description="抽取的关系")
    raw_text: str = Field(..., description="原始文本")


class QueryRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., description="用户问题", min_length=1)
    context: Optional[str] = Field(None, description="额外上下文")
    history: List[Dict[str, str]] = Field(default_factory=list, description="对话历史")


class QueryResponse(BaseModel):
    """问答响应"""
    answer: str = Field(..., description="回答内容")
    sources: List[str] = Field(default_factory=list, description="参考来源")
    confidence: float = Field(default=0.0, description="置信度")


class JobDescription(BaseModel):
    """岗位描述"""
    title: str = Field(..., description="岗位名称")
    company: Optional[str] = Field(None, description="公司名称")
    requirements: List[str] = Field(default_factory=list, description="岗位要求")
    responsibilities: List[str] = Field(default_factory=list, description="岗位职责")
    raw_text: str = Field(..., description="原始JD文本")


# ==================== 统一API响应模型 ====================

class ApiResponse(BaseModel):
    """统一API响应格式"""
    code: int = Field(0, description="状态码，0=成功")
    message: str = Field("success", description="状态消息")
    data: Any = Field(None, description="响应数据")
    request_id: str = Field("", description="请求ID")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")


# ==================== Agent输出Schema ====================

class JobAnalysisOutput(BaseModel):
    """岗位分析输出Schema"""
    report: str = Field(..., min_length=10, description="分析报告")
    job_title: str = Field("", description="岗位名称")


class SkillGapOutput(BaseModel):
    """技能差距输出Schema"""
    report: str = Field(..., min_length=10, description="差距分析报告")
    target_job: str = Field("", description="目标岗位")


class LearningPathOutput(BaseModel):
    """学习路径输出Schema"""
    report: str = Field(..., min_length=10, description="学习路径报告")


class TrendOutput(BaseModel):
    """趋势预测输出Schema"""
    report: str = Field(..., min_length=10, description="趋势分析报告")


class ReportOutput(BaseModel):
    """报告生成输出Schema"""
    report: str = Field(..., min_length=10, description="综合报告")
    report_type: str = Field("综合报告", description="报告类型")


class JobCompareOutput(BaseModel):
    """岗位对比输出Schema"""
    report: str = Field(..., min_length=10, description="对比分析报告")
    job_a: str = Field("", description="岗位A名称")
    job_b: str = Field("", description="岗位B名称")


class ResumeMatchOutput(BaseModel):
    """简历匹配输出Schema"""
    report: str = Field(..., min_length=10, description="匹配评估报告")
    target_job: str = Field("", description="目标岗位")


class GeneralQAOutput(BaseModel):
    """通用问答输出Schema"""
    answer: str = Field(..., min_length=1, description="回答内容")


# ==================== Agent输出Schema映射 ====================

# 每个Agent任务类型对应的输出Schema
AGENT_OUTPUT_SCHEMAS = {
    "job_analysis": JobAnalysisOutput,
    "skill_gap": SkillGapOutput,
    "learning_path": LearningPathOutput,
    "trend_prediction": TrendOutput,
    "report_generation": ReportOutput,
    "job_compare": JobCompareOutput,
    "resume_match": ResumeMatchOutput,
    "general_qa": GeneralQAOutput,
}


def validate_agent_output(task_type: str, data: Any) -> Dict[str, Any]:
    """
    校验Agent输出是否符合预定义的Pydantic schema

    Args:
        task_type: 任务类型
        data: Agent输出的数据

    Returns:
        {
            "valid": bool,
            "data": 校验后的数据（可能经过修正）,
            "errors": 校验错误列表,
            "confidence": 置信度评分(0-1)
        }
    """
    from pydantic import ValidationError

    schema_class = AGENT_OUTPUT_SCHEMAS.get(task_type)
    if not schema_class:
        # 无schema的任务类型，跳过校验
        return {"valid": True, "data": data, "errors": [], "confidence": 0.8}

    errors = []
    confidence = 1.0

    # 尝试校验
    try:
        if isinstance(data, dict):
            validated = schema_class(**data)
            validated_data = validated.model_dump()
        elif isinstance(data, str):
            # 如果data是纯文本，包装为report字段
            validated = schema_class(report=data)
            validated_data = validated.model_dump()
        else:
            # 尝试强制转换
            validated = schema_class(report=str(data))
            validated_data = validated.model_dump()

        return {
            "valid": True,
            "data": validated_data,
            "errors": [],
            "confidence": confidence,
        }

    except ValidationError as e:
        error_details = []
        for err in e.errors():
            field_name = ".".join(str(x) for x in err.get("loc", []))
            error_msg = err.get("msg", "")
            error_details.append(f"{field_name}: {error_msg}")

        # 尝试修正：如果只是report字段太短，尝试补充
        if isinstance(data, dict) and "report" in data:
            report_text = data.get("report", "")
            if len(report_text) < 10 and report_text:
                # 报告过短但非空，补充提示
                data["report"] = f"{report_text}\n\n（注：分析结果较为简略，建议进一步查询获取更详细信息）"
                try:
                    validated = schema_class(**data)
                    return {
                        "valid": True,
                        "data": validated.model_dump(),
                        "errors": error_details,
                        "confidence": 0.5,  # 修正后降低置信度
                    }
                except ValidationError:
                    pass

        # 校验失败，返回原始数据+错误信息
        return {
            "valid": False,
            "data": data,
            "errors": error_details,
            "confidence": 0.3,
        }

    except Exception as e:
        return {
            "valid": False,
            "data": data,
            "errors": [str(e)],
            "confidence": 0.2,
        }


# ==================== 简历解析 Schema ====================

class ResumeExperienceItem(BaseModel):
    """工作经历项（对齐 resume_experiences 表）"""
    company_name: str
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: Optional[int] = 0


class ResumeEducationItem(BaseModel):
    """教育经历项（对齐 resume_educations 表）"""
    school: str
    major: Optional[str] = None
    degree: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ParsedResumeData(BaseModel):
    """LLM 解析后的简历数据（对齐 LLM_RESUME_ANALYZE_API.md 第三节 + resumes 表）"""
    name: Optional[str] = None
    gender: Optional[int] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    work_years: Optional[int] = None
    education: Optional[str] = None
    expect_salary_min: Optional[int] = None
    expect_salary_max: Optional[int] = None
    expect_city: Optional[str] = None
    expect_job: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experiences: List[ResumeExperienceItem] = Field(default_factory=list)
    educations: List[ResumeEducationItem] = Field(default_factory=list)
    parsed_raw: Optional[Dict[str, Any]] = None


class AnalyzeResumeRequest(BaseModel):
    """JSON 方式调用请求（传 file_url）"""
    file_url: str
    file_type: Optional[str] = None  # pdf / image，不传则按扩展名推断
