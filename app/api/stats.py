from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import Result, OverviewOut
from app.utils.jwtUtil import require_admin
from app.services.stats_service import count_overview, count_salary_distribution, count_city_distribution, \
    count_skills_hot, count_industry_distribution, count_source_distribution, count_education_distribution, \
    count_job_trend, count_experience_salary, count_skill_trend, count_emerging_skills

router = APIRouter(prefix="/stats", tags=["数据统计"])

@router.get("/emerging", response_model=Result[dict], summary="新兴技能发现(增速榜+新词榜)")
async def get_emerging_skills(db: AsyncSession = Depends(get_db)):
    """两路合并:
    trending   字典内技能的需求增速榜(近3月 vs 前3月, 翻倍以上)
    candidates 字典外新词榜(emerging_skills 候选表, 按出现次数)
    """
    from app.services.stats_service import count_emerging_candidates

    trending = await count_emerging_skills(db)
    candidates = await count_emerging_candidates(db)
    return Result.success(data={
        "trending": trending["skills"],
        "window": trending["window"],
        "candidates": candidates,
    })


@router.post("/emerging/adopt", response_model=Result[dict], summary="转正新兴技能(管理员)")
async def adopt_emerging(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """候选技能转正: 进字典 + 全文回溯补历史职位/简历的技能关联。

    body: {"names": ["MCP协议", "AIGC工程化"]}
    """
    from app.services.emerging_service import adopt_emerging_skills

    names = payload.get("names") or []
    if not names:
        raise HTTPException(status_code=400, detail="names 不能为空")
    out = await adopt_emerging_skills(db, names)
    return Result.success(data=out, message=f"已转正 {len(out['results'])} 个技能")

@router.get("/overview", response_model=Result[OverviewOut], summary="五个词条统计")
async def get_overview(db: AsyncSession = Depends(get_db)):
    out = await count_overview(db)
    return Result.success(data=out)

@router.get("/salary-distribution", response_model=Result[List], summary="薪资分布")
async def get_salary_distribution(db: AsyncSession = Depends(get_db)):
    out = await count_salary_distribution(db)
    return Result.success(data=out)

@router.get("/city-distribution", response_model=Result[dict], summary="城市分布top10")
async def get_city_distribution(db: AsyncSession = Depends(get_db)):
    out = await count_city_distribution(db)
    return Result.success(data=out)

@router.get("/skills/hot", response_model=Result[dict], summary="技能分布top15")
async def get_skills_hot(db: AsyncSession = Depends(get_db)):
    out = await count_skills_hot(db)
    return Result.success(data=out)

@router.get("/industry-distribution", response_model=Result[list], summary="行业占比")
async def get_industry_distribution(db: AsyncSession = Depends(get_db)):
    out = await count_industry_distribution(db)
    return Result.success(data=out)

@router.get("/source-distribution", response_model=Result[list], summary="数据来源占比")
async def get_source_distribution(db: AsyncSession = Depends(get_db)):
    out = await count_source_distribution(db)
    return Result.success(data=out)

@router.get("/education-distribution", response_model=Result[list], summary="学历分布(归一化)")
async def get_education_distribution(db: AsyncSession = Depends(get_db)):
    out = await count_education_distribution(db)
    return Result.success(data=out)

@router.get("/job-trend", response_model=Result[dict], summary="职位发布趋势(近8月)")
async def get_job_trend(db: AsyncSession = Depends(get_db)):
    out = await count_job_trend(db)
    return Result.success(data=out)


@router.get("/skill-trend", response_model=Result[dict], summary="技能需求月度趋势(时序演化)")
async def get_skill_trend(
    skills: str = Query("", description="逗号分隔的技能名, 留空自动取热门前5"),
    months: int = Query(6, ge=3, le=12, description="统计月份数"),
    db: AsyncSession = Depends(get_db),
):
    """指定技能在近 N 个月每月的岗位需求数。"""
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    out = await count_skill_trend(db, skill_list, months)
    return Result.success(data=out)

@router.get("/experience-salary", response_model=Result[dict], summary="经验要求×平均薪资")
async def get_experience_salary(db: AsyncSession = Depends(get_db)):
    out = await count_experience_salary(db)
    return Result.success(data=out)
