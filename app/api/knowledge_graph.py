from fastapi import APIRouter, HTTPException, Query

from app.services.neo4j_service import neo4j_service


router = APIRouter(
    prefix="/knowledge-graph",
    tags=["知识图谱"],
)


@router.get("/health")
def knowledge_graph_health():
    try:
        return {
            "success": True,
            "neo4j": neo4j_service.health(),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Neo4j连接失败: {exc}",
        )


@router.get("/directions")
def get_directions():
    try:
        return {
            "success": True,
            "data": neo4j_service.get_directions(),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@router.get("/direction")
def get_direction(
    keyword: str = Query(
        ...,
        min_length=1,
        description="岗位方向，例如：数据分析",
    )
):
    keyword = keyword.strip()

    try:
        data = neo4j_service.get_direction_value(keyword)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if data is None:
        raise HTTPException(
            status_code=404,
            detail="没有找到对应的岗位方向",
        )

    return {
        "success": True,
        "data": data,
    }