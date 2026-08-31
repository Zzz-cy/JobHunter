"""MySQL → ES 全量同步脚本。

文档是冗余拍平的(company_name/skills 平铺, ES 不做 JOIN)。
_id 用 MySQL 主键, 重复跑天然幂等。helpers.bulk 分批写入。
"""
import asyncio

from elasticsearch import helpers
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.es import es_client, JOBS_INDEX
from app.models import Job


def _job_to_doc(job: Job) -> dict:
    """把 Job ORM 对象转成 ES 文档(冗余拍平关联字段)。"""
    # 技能名列表: 利用 ORM @property skill_name(已归一的标准名)
    skill_names = [js.skill_name for js in job.skills if js.skill_name]

    return {
        "_index": JOBS_INDEX,
        "_id": job.id,                      # MySQL 主键 → ES 文档 id(幂等)
        "_source": {
            # 全文搜索字段
            "title": job.title,
            "description_text": job.description_text,
            "company_name": job.company.name if job.company else None,
            # 精确筛选字段
            "skills": skill_names,
            "city": job.city,
            "district": job.district,
            "industry_code": (
                # 取一级行业(二级 IT-RD → IT), 和统计口径一致
                job.company.industry_code.split("-")[0]
                if job.company and job.company.industry_code else None
            ),
            "experience_req": job.experience_req,   # 已在入库时归一(5档)
            "education_req": job.education_req,     # 已归一(5档)
            "source": job.source,
            "job_status": job.status,
            # 范围字段
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "publish_at": job.publish_at.strftime("%Y-%m-%d %H:%M:%S") if job.publish_at else None,
        },
    }


async def sync():
    print("开始全量同步 MySQL → ES ...")
    async with AsyncSessionLocal() as db:
        # 查所有有效职位(skills/company 走 selectin 预加载, 无 N+1)
        stmt = select(Job).where(Job.is_deleted == 0)
        result = await db.scalars(stmt)
        jobs = result.unique().all()
        print(f"MySQL 待同步: {len(jobs)} 条职位")

        # 分批写入(500 条/批)
        success, errors = helpers.bulk(
            es_client,
            (_job_to_doc(j) for j in jobs),
            chunk_size=500,
            request_timeout=60,
            raise_on_error=False,   # 单条失败不中断, 收集错误
        )
        print(f"✅ 同步完成: 成功 {success} 条, 失败 {len(errors)} 条")
        if errors:
            for e in errors[:3]:    # 只看前3条错误样本
                print(f"   失败样本: {str(e)[:150]}")

    # 验证 ES 里的文档数
    count = es_client.count(index=JOBS_INDEX)["count"]
    print(f"ES 索引 {JOBS_INDEX} 现有文档: {count} 条")


if __name__ == "__main__":
    asyncio.run(sync())
