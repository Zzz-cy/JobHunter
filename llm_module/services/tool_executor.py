"""
工具执行器 - 为注册的工具提供具体执行逻辑
"""
from __future__ import annotations

import json
from typing import Dict, Any, Optional, Callable

from utils.logger import get_logger
logger = get_logger("services.tool_executor")


class ToolExecutor:
    """工具执行器 - 将工具名称映射到具体执行函数"""

    def __init__(self):
        self._executors: Dict[str, Callable] = {
            "knowledge_search": self._knowledge_search,
            "graph_query": self._graph_query,
            "skill_database": self._skill_database,
            "job_search": self._job_search,
            "jd_parser": self._jd_parser,
            "web_search": self._web_search,
            "calculator": self._calculator,
        }

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            {"success": bool, "data": Any, "error": str}
        """
        executor = self._executors.get(tool_name)
        if not executor:
            return {
                "success": False,
                "data": None,
                "error": f"未知工具: {tool_name}",
            }

        try:
            result = await executor(params)
            return {
                "success": True,
                "data": result,
                "error": "",
            }
        except Exception as e:
            logger.warning(f"工具执行失败 [{tool_name}]: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e),
            }

    async def _knowledge_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        向量知识库检索

        params: {query: str, top_k: int}
        """
        from services.rag_service import get_rag_service

        query = params.get("query", "")
        top_k = params.get("top_k", 5)

        if not query:
            return {"results": [], "count": 0}

        rag = get_rag_service()
        result = await rag.query(query, top_k=top_k)

        # 提取检索结果
        if isinstance(result, dict):
            sources = result.get("sources", [])
            answer = result.get("answer", "")
            return {
                "results": sources,
                "answer_from_kb": answer,
                "count": len(sources),
            }

        return {"results": [], "count": 0}

    async def _graph_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        知识图谱查询

        params: {entity_name: str, depth: int}
        """
        from services.neo4j_service import get_neo4j_service

        entity_name = params.get("entity_name", "")
        depth = params.get("depth", 2)

        if not entity_name:
            return {"entity": None, "neighbors": []}

        neo4j = get_neo4j_service()
        if not neo4j.is_connected():
            return {"entity": None, "neighbors": [], "error": "Neo4j未连接"}

        try:
            # 查找实体
            entity = neo4j.find_entity(entity_name)

            # 查找邻居
            neighbors = neo4j.find_neighbors(entity_name, depth=depth)

            return {
                "entity": entity,
                "neighbors": neighbors if isinstance(neighbors, list) else [],
            }
        except Exception as e:
            logger.warning(f"图谱查询失败: {e}")
            return {"entity": None, "neighbors": [], "error": str(e)}

    async def _skill_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        技能库查询

        params: {keyword: str, category: str, limit: int}
        """
        from services.db_service import get_db_service

        keyword = params.get("keyword", "")
        category = params.get("category", "")
        limit = params.get("limit", 20)

        db = get_db_service()
        skills = db.search_skills(keyword=keyword, category=category, limit=limit)

        return {
            "skills": skills,
            "count": len(skills),
        }

    async def _job_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        真实岗位检索(主库 jobs+companies)

        params: {keyword: str, city: str, job_type: str, limit: int}
        """
        from services.db_service import get_db_service

        keyword = params.get("keyword", "")
        city = params.get("city", "")
        job_type = params.get("job_type", "")
        limit = int(params.get("limit", 8))

        db = get_db_service()
        rows = db.search_job_openings(keyword=keyword, city=city,
                                      job_type=job_type, limit=limit)

        jobs = []
        for j in rows:
            salary = self._fmt_salary(j)
            desc = (j.get("description") or "").replace("\n", " ").strip()
            jobs.append({
                "job_id": j.get("id"),
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "city": j.get("city", ""),
                "district": j.get("district", ""),
                "salary": salary,
                "experience": j.get("experience_req", ""),
                "education": j.get("education_req", ""),
                "job_type": j.get("job_type", ""),
                "description": desc[:200],
            })

        return {"jobs": jobs, "count": len(jobs)}

    @staticmethod
    def _fmt_salary(job: Dict[str, Any]) -> str:
        """主库 salary_min/max 为元; unit=month/year/月/年。格式化给 LLM 引用"""
        lo = job.get("salary_min")
        hi = job.get("salary_max")
        unit = (job.get("salary_unit") or "").strip().lower()
        if lo is None and hi is None:
            return "薪资面议"
        lo = int(lo or 0)
        hi = int(hi or 0)
        if lo == 0 and hi == 0:
            return "薪资面议"
        rng = f"{lo}-{hi}" if hi else str(lo)
        if unit in ("month", "月"):
            return f"{rng}元/月"
        if unit in ("year", "年"):
            return f"{rng}元/年"
        return f"{rng}元"

    async def _jd_parser(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        JD结构化解析

        params: {content: str}
        """
        from core.extractor import get_extractor

        content = params.get("content", "")
        if not content:
            return {"extracted": None, "error": "内容为空"}

        extractor = get_extractor()
        try:
            result = await extractor.extract_from_jd(content)
            if hasattr(result, "model_dump"):
                return {"extracted": result.model_dump()}
            elif isinstance(result, dict):
                return {"extracted": result}
            else:
                return {"extracted": str(result)}
        except Exception as e:
            logger.warning(f"JD解析失败: {e}")
            return {"extracted": None, "error": str(e)}

    async def _web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        联网搜索（使用httpx请求DuckDuckGo Lite）

        params: {query: str, max_results: int}
        """
        import httpx

        query = params.get("query", "")
        max_results = params.get("max_results", 5)

        if not query:
            return {"results": [], "count": 0, "error": "查询为空"}

        try:
            # 使用DuckDuckGo Lite HTML搜索（无需API Key）
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://lite.duckduckgo.com/lite/",
                    params={"q": query, "kl": "cn-zh"},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    },
                )

                if response.status_code != 200:
                    return {"results": [], "count": 0, "error": f"HTTP {response.status_code}"}

                # 简单解析HTML结果
                import re
                # 提取搜索结果链接和摘要
                results = []
                # DuckDuckGo Lite的结果在<table>中，提取链接和摘要
                link_pattern = re.compile(r'<a[^>]*class="result-link"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
                snippet_pattern = re.compile(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', re.DOTALL)

                links = link_pattern.findall(response.text)
                snippets = snippet_pattern.findall(response.text)

                for i, (url, title) in enumerate(links[:max_results]):
                    # 清理HTML标签
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                    if clean_title and url.startswith("http"):
                        results.append({
                            "title": clean_title[:200],
                            "url": url[:500],
                            "snippet": snippet[:300],
                        })

                logger.info(f"联网搜索完成: query='{query[:30]}', results={len(results)}")
                return {"results": results, "count": len(results)}

        except Exception as e:
            logger.warning(f"联网搜索失败: {e}")
            return {"results": [], "count": 0, "error": str(e)}

    async def _calculator(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        数值计算（薪资对比、百分比、简单数学运算）

        params: {expression: str, description: str}
        """
        expression = params.get("expression", "")
        description = params.get("description", "")

        if not expression:
            return {"result": None, "error": "表达式为空"}

        # 安全计算：仅允许数字、运算符、括号、小数点
        # 移除空格和中文逗号
        expr_clean = expression.replace(" ", "").replace("，", ",").replace("％", "%")

        # 处理百分比
        expr_clean = expr_clean.replace("%", "/100")

        # 安全检查：只允许数字、运算符、括号、小数点
        if not re.match(r'^[\d+\-*/().,eE]+$', expr_clean):
            return {"result": None, "error": f"不安全的表达式: {expression}"}

        try:
            # 使用Python eval在受限环境下计算
            result = eval(expr_clean, {"__builtins__": {}}, {})

            # 格式化结果
            if isinstance(result, float):
                if abs(result) >= 10000:
                    formatted = f"{result:,.2f}"
                elif abs(result) >= 1:
                    formatted = f"{result:.2f}"
                else:
                    formatted = f"{result:.4f}"
            else:
                formatted = f"{result:,}"

            return {
                "result": result,
                "formatted": formatted,
                "expression": expression,
                "description": description,
            }

        except ZeroDivisionError:
            return {"result": None, "error": "除零错误"}
        except Exception as e:
            return {"result": None, "error": f"计算错误: {e}"}


# 单例
_tool_executor: Any = None


def get_tool_executor() -> ToolExecutor:
    """获取工具执行器单例"""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
