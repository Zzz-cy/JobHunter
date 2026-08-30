# 🕷️ JobHunter 爬虫数据需求说明

> 给爬虫队友的需求文档。明确要爬什么平台、爬哪些字段、按什么格式交付,以及关键约束。
> 对照参考:`backend/db/mysql/01_schema.sql` 的 `companies` / `jobs` / `job_skills` 表。

---

## 一、要爬哪些平台

**实际在爬的平台**(按当前数据量排序):

| 平台 | source 值 | 说明 |
|---|---|---|
| 大学生就业网(24365) | `NCSS` | **主力来源**,爬虫主目标 |
| 猎聘 | `liepin` | 第二来源 |
| 前程无忧 | `51job` | 补充来源 |
| 文化创意类 | `cultural` | 垂直补充 |
| BOSS 直聘 | `boss` | 反爬强,当前量少 |
| 公司官网 | `official` | 预留,暂未使用 |

> 爬虫项目位于 `pa/`(scrapy+playwright),入口 `run_pipeline.bat` 一条龙:
> 爬取 → 格式修复 → 转标准格式 → 拷贝到 `backend/db/data/jobs_raw.json`。

---

## 二、要爬两类数据

### 📦 类型 1:职位数据(写入 `jobs` 表)

| 字段 | 是否必填 | 类型 | 说明 / 例子 |
|---|---|---|---|
| `title` | ✅ 必填 | 字符串 | "Python 后端工程师" |
| `source_url` | ✅ 必填 | URL | 原始职位页 URL(用户点"立即投递"会跳过去) |
| `source` | ✅ 必填 | 枚举 | boss / liepin / official |
| `source_id` | ⭐ 强烈建议 | 字符串 | 平台原始职位 ID,**用于去重**(`uk_job_source` 唯一索引) |
| `city` | 推荐 | 字符串 | "北京" |
| `district` | 可选 | 字符串 | "海淀区" |
| `salary_min` / `salary_max` | 推荐 | 整数(元) | 月薪下/上限。例如 "15-25K" → 15000 / 25000 |
| `salary_unit` | 推荐 | 枚举 | month / day / year(默认 month) |
| `salary_months` | 可选 | 整数 | "13薪" → 13 |
| `experience_req` | 推荐 | 字符串 | "3-5年" / "应届" |
| `education_req` | 推荐 | 字符串 | "本科" / "硕士" |
| `job_type` | 推荐 | 枚举 | full / part / intern(默认 full) |
| `description` | 推荐 | 长文本 | JD 原文,**可含 HTML 标签** |
| `description_text` | ⭐ 强烈建议 | 长文本 | JD **纯文本**(去标签),给 ES 搜索和向量化用 |
| `highlights` | 可选 | JSON 数组 | `["弹性工作", "股票期权"]` |
| `advantage` | 可选 | 长文本 | 岗位亮点文字 |
| `work_address` | 可选 | 字符串 | 详细办公地址 |
| `longitude` / `latitude` | 可选 | 小数 | 经纬度(7 位精度) |
| `department` | 可选 | 字符串 | 部门名 |
| `publish_at` | 推荐 | 日期 | 发布时间 |
| `status` | 可选 | 枚举 | active / closed / expired(默认 active) |
| `crawl_batch` | 推荐 | 字符串 | 采集批次号,方便追踪(如 `20260719_boss_python_北京`) |
| `company_id` | 关联 | 整数 | **外键到 companies 表**,跟"公司数据"配对爬 |
| `job_code` | 内部生成 | 字符串 | 跟 user_code 一样的对外编码,**爬虫不用管**,后端落库时自动生成 |

#### ⚠️ 关于技能标签(`job_skills` 关联表)

数据库设计了职位-技能关联,但**爬虫不要硬去匹配 skill_id**(那需要 NER + 字典归一,是后端的活)。爬虫只要做一件事:

> **从 JD 里把"技能关键词"提取成字符串数组返回即可**,例如 `["Python", "MySQL", "FastAPI", "Docker"]`

后端拿到后会自己做归一化(映射到 `skills` 字典表)+ 写 `job_skills` 表。

#### ✅ 学历/经验同理:给原始值即可,后端自动归一

招聘网站的学历/经验写法五花八门(`统招本科`/`本科及以上`/`3年以上`/`经验不限`...)。
**爬虫按原样给,不要自己转** —— 后端入库时通过 `@validates` 自动归一:

| 字段 | 归一结果(5 档) | 示例转换 |
|---|---|---|
| `education_req` | 博士/硕士/本科/大专/不限 | `统招本科`→本科, `学历不限`→不限 |
| `experience_req` | 应届/1-3年/3-5年/5-10年/10年+/不限 | `3年以上`→3-5年, `经验不限`→不限 |

---

### 🏢 类型 2:公司数据(写入 `companies` 表)

每个职位都关联一家公司,所以公司数据要**跟职位一起爬**。

| 字段 | 是否必填 | 说明 |
|---|---|---|
| `name` | ✅ 必填 | 公司全名 |
| `source` | ✅ 必填 | boss / liepin / official |
| `source_url` | 推荐 | 公司主页 URL |
| `short_name` | 可选 | 简称,如 "字节" |
| `industry_code` | 可选 | 行业代码(关联 industries 表) |
| `size` | 推荐 | 规模,如 `0-20` / `20-99` / `100-499` / `10000+` |
| `stage` | 可选 | 融资阶段,如 "已上市" / "A轮" |
| `city` / `district` | 推荐 | 总部所在 |
| `address` | 可选 | 详细地址 |
| `logo_url` | 可选 | logo 图片 URL |
| `website` | 可选 | 公司官网 URL。⚠️ **能爬到就给,爬不到留空即可**(如 BOSS 直聘不显示公司官网)。公司去重主要靠 `(name, source)`,官网只是少数公司能跨平台合并的辅助手段 |
| `welfare` | 可选 | JSON 数组:`["六险一金", "免费餐"]` |
| `description` | 可选 | 公司介绍长文本 |
| `company_code` | 内部生成 | 后端落库时自动生成 |

---

## 三、交付物格式建议

让爬虫队友按这种 JSON 结构交付,后端落库最省事:

```json
{
  "crawl_batch": "20260719_boss_python_北京",
  "source": "boss",
  "jobs": [
    {
      "source_id": "Boss_123456789",
      "source_url": "https://www.zhipin.com/job/xxx",
      "title": "Python 后端工程师",
      "city": "北京",
      "district": "海淀区",
      "salary_min": 15000,
      "salary_max": 25000,
      "salary_unit": "month",
      "salary_months": 13,
      "experience_req": "3-5年",
      "education_req": "本科",
      "job_type": "full",
      "description": "<p>原始 HTML JD...</p>",
      "description_text": "去标签的纯文本 JD...",
      "highlights": ["弹性工作", "股票期权"],
      "publish_at": "2026-07-18T10:00:00",
      "raw_skills": ["Python", "MySQL", "FastAPI", "Docker"],
      "company": {
        "name": "字节跳动",
        "source": "boss",
        "short_name": "字节",
        "size": "10000+",
        "stage": "已上市",
        "city": "北京",
        "district": "海淀区",
        "logo_url": "https://...",
        "source_url": "https://www.zhipin.com/company/xxx",
        "welfare": ["六险一金", "免费餐"]
      }
    }
  ]
}
```

---

## 四、关键约束(让爬虫队友务必遵守)

1. **去重靠 `source_id`** —— 同一平台同一职位 ID 只爬一次,这是数据库唯一索引 `uk_job_source` 的要求
2. **公司去重靠 `(name, source)`** —— 同一平台同一公司名只建一条。官网 `website` 是辅助:少数公司能爬到官网时,可把不同平台的同公司合并(如 boss腾讯 和 liepin腾讯)。爬不到官网不影响去重
3. **JD 一定分两个字段**:`description` 保留 HTML(前端展示),`description_text` 纯文本(给搜索引擎和 AI 向量化),不要只给 HTML
4. **薪资统一换算成"元/月"单位**:`salary_min/max` 存的是**元**(15K → 15000),`salary_unit` 标 month/day/year
5. **公司信息嵌套在职位里一起给**:别分两批交付,后端要做关联(company_id 是外键)
6. **技能关键词给原始字符串数组即可**,不要硬编码 skill_id —— 归一化是后端做
7. **不要伪造数据**:爬不到的字段就留空(NULL),不要瞎填"未知"或 "0"。尤其注意:**别把网页上的无关文本当成字段值**(如把"看了该职位的人还会看"误抓成地址)

---

## 五、字段对照速查表

爬虫交付字段 → 数据库落库字段的对应关系:

| 爬虫交付字段 | 落库表 | 落库字段 | 备注 |
|---|---|---|---|
| `jobs[].*` | `jobs` | 同名 | job_code / id 后端生成 |
| `jobs[].company` | `companies` | 同名 | company_code / id 后端生成 |
| `jobs[].raw_skills` | `job_skills` | 不直接落 | 后端归一化后写 |
| `crawl_batch` | `jobs.crawl_batch` | 每条职位都带 | |
| `source` | `jobs.source` / `companies.source` | 每条都带 | |

---

## 六、数据从爬虫到可搜索的完整流程(实际)

```
① 爬虫一条龙(pa/ 项目)
   双击 pa/run_pipeline.bat
   → 爬取(约40分钟) → 格式修复 → 转标准格式
   → 产出 backend/db/data/jobs_raw.json

② 一键全库同步(数据管理页, 管理员)
   前端「数据管理」页点「一键同步所有库」(POST /crawl/sync-all)
   → MySQL 导入(幂等去重) → ES 同步 → ChromaDB 向量 → Neo4j 图谱
   → 四步进度实时可见(每步独立容错, 某库没启动只标红该步)

③ 数据可用
   职位搜索(ES 分词+相关度) / 智能推荐(向量) / 知识图谱 全部用上新数据
```

> 后端相关接口(`app/api/crawl.py`):
> - `GET  /crawl/preview` 预览数据文件(条数/大小/字段填充率)
> - `POST /crawl/sync-all` 一键四库同步(后台执行, 立即返回)
> - `GET  /crawl/sync-status` 同步进度轮询

> 注: `crawl_tasks` 表为早期预留, 当前未使用(进度由内存状态提供, 重启即清)。
| `error_msg` | 失败原因 |

---

## 七、对接流程建议

1. **小批量试爬**:先爬 10-20 条样本,导出 JSON,跟后端联调落库
2. **确认去重逻辑**:让后端确认 `source_id` 的格式约定(例如是否加平台前缀 `Boss_xxx`)
3. **正式爬**:大范围爬取,按 `crawl_batch` 分批交付
4. **持续更新**:定期重爬,用 `status` 字段标记已下线职位(closed/expired)
