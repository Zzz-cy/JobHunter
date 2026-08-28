"""
初始化 ES 的 jobs 索引(mapping 定义)

用途: 定义职位文档的字段结构 + 分词器, 全量同步前必须先跑一次。
用法:
    cd backend
    python -m scripts.init_es_index

幂等性: 索引已存在时先删除重建(开发期方便改 mapping, 生产别这么干)。
"""
from app.core.es import es_client, JOBS_INDEX

# ---------- jobs 索引的 mapping(字段结构定义) ----------
# 设计原则(对应 MySQL 查询场景):
#   - 要"搜索"的字段(title/description/company_name) → text + ik 分词
#   - 要"精确筛选"的字段(city/skills/学历/经验)     → keyword(不分词, 整体匹配)
#   - 要"范围比较"的字段(薪资/发布时间)              → integer/date
MAPPING = {
    "settings": {
        "number_of_shards": 1,        # 单机单分片够用
        "number_of_replicas": 0,      # 没有副本节点, 0 才是 green
    },
    "mappings": {
        "properties": {
            # ---------- 全文搜索字段(text + IK 中文分词) ----------
            "title": {
                "type": "text",
                "analyzer": "ik_max_word",        # 入库时最细粒度分词
                "search_analyzer": "ik_smart",   # 搜索时智能分词(减少噪音)
            },
            "description_text": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
            },
            "company_name": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "fields": {                       # 子字段: 兼顾精确匹配
                    "keyword": {"type": "keyword"}
                }
            },

            # ---------- 精确筛选字段(keyword, 不分词整体匹配) ----------
            # 对应 MySQL 的 WHERE city='北京' / education_req='本科'
            "skills":         {"type": "keyword"},   # 技能名数组(归一后的标准名)
            "city":           {"type": "keyword"},
            "district":       {"type": "keyword"},
            "industry_code":  {"type": "keyword"},   # 一级行业 code(如 IT)
            "experience_req": {"type": "keyword"},   # 已归一的 5 档
            "education_req":  {"type": "keyword"},   # 已归一的 5 档
            "source":         {"type": "keyword"},   # boss/liepin/official

            # ---------- 范围字段(对应薪资区间筛选/时间排序) ----------
            "salary_min":  {"type": "integer"},
            "salary_max":  {"type": "integer"},
            "publish_at":  {"type": "date", "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis||strict_date_optional_time"},
            "job_status":  {"type": "keyword"},      # active/closed(过滤下架)
        }
    }
}


def main():
    # 已存在先删(开发期改 mapping 方便; 生产要用 alias 平滑迁移)
    if es_client.indices.exists(index=JOBS_INDEX):
        es_client.indices.delete(index=JOBS_INDEX)
        print(f"🗑️  已删除旧索引 {JOBS_INDEX}")

    es_client.indices.create(index=JOBS_INDEX, **MAPPING)
    print(f"✅ 索引 {JOBS_INDEX} 创建成功")

    # 验证 mapping 生效
    resp = es_client.indices.get_mapping(index=JOBS_INDEX)
    fields = list(resp[JOBS_INDEX]["mappings"]["properties"].keys())
    print(f"   字段数: {len(fields)}")
    print(f"   字段: {fields}")


if __name__ == "__main__":
    main()
