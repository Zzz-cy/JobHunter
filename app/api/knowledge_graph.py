from fastapi import APIRouter, Query

from app.core.exceptions import BizException
from app.schemas import Result
from app.schemas.result import BizCode
from app.services.neo4j_service import neo4j_service


router = APIRouter(
    prefix="/knowledge-graph",
    tags=["知识图谱"],
)


@router.get(
    "/health",
    response_model=Result,
    summary="检查知识图谱服务状态",
)
def knowledge_graph_health():
    healthy = neo4j_service.health()

    if not healthy:
        raise BizException(
            message="Neo4j连接失败",
            code=BizCode.SYSTEM_ERROR,
        )

    return Result.success(
        data={
            "neo4j": True,
        }
    )


@router.get(
    "/directions",
    response_model=Result,
    summary="获取岗位方向列表",
)
def get_directions():
    data = neo4j_service.get_directions()

    if not data:
        raise BizException(
            message="知识图谱查询失败，请稍后重试",
            code=BizCode.SYSTEM_ERROR,
        )

    return Result.success(data=data)


@router.get(
    "/direction",
    response_model=Result,
    summary="查询岗位方向知识图谱",
)
def get_direction(
    keyword: str = Query(
        ...,
        min_length=1,
        description="岗位方向，例如：数据分析",
    ),
):
    keyword = keyword.strip()

    if not keyword:
        raise BizException(
            message="岗位方向不能为空",
            code=BizCode.PARAM_ERROR,
        )

    data = neo4j_service.get_direction_value(keyword)

    if not data:
        raise BizException(
            message="未找到对应的岗位方向",
            code=BizCode.NOT_FOUND,
        )

    return Result.success(data=data)