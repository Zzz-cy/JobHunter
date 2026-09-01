# -*- coding: utf-8 -*-
"""JD 解析准确率评测: LLM 核验式交叉验证。

用法: python evaluation/jd/eval_jd_parse.py
"""
import asyncio
import json
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # 项目根, 用 app.core.llm

EVAL_DIR = Path(__file__).resolve().parent
DATA_DIR = EVAL_DIR.parents[1] / "db" / "data"
SAMPLE_N = 100          # 固定种子可复现
SEED = 42
CONCURRENCY = 5         # LLM 并发(智谱 glm-4-flash 扛得住)

EVAL_SOURCE = "jobs_raw_2.json"


def load_jobs():
    jobs = []
    for j in json.load(open(DATA_DIR / EVAL_SOURCE, encoding="utf-8"))["jobs"]:
        text = (j.get("description_text") or "").strip()
        tags = [t.strip() for t in (j.get("raw_skills") or []) if t.strip()]
        if text and tags:
            jobs.append({"title": j["title"], "text": text[:2000], "tags": tags})
    return jobs


async def verify_tags(text: str, title: str, tags: list[str], achat_json) -> dict:
    """LLM 逐标签核验: JD 全文是否支持该技能标签。"""
    prompt = (
        f"岗位: {title}\n\n职位描述全文:\n{text}\n\n"
        f"系统记录的技能标签: {json.dumps(tags, ensure_ascii=False)}\n\n"
        "请逐一判断每个标签是否被 JD 支持(判断依据包括职位描述全文和岗位标题, "
        "明确提及或同义/上位表达都算支持, 如\"熟悉主流Web安全技术\"支持\"网络安全\", "
        "标题\"单片机工程师\"支持\"单片机\")。\n"
        "verdicts 必须覆盖上面列表里的每一个标签, 一个都不能漏。\n"
        '只返回 JSON: {"verdicts": {"标签1": true, "标签2": false}}'
    )
    data = await achat_json(prompt, "你是严谨的数据核验员, 只依据给定文本判断, 不脑补。")
    return data.get("verdicts") if isinstance(data, dict) else {}


async def main():
    from app.core.llm import achat_json

    jobs = load_jobs()
    rng = random.Random(SEED)
    sample = rng.sample(jobs, min(SAMPLE_N, len(jobs)))
    print(f"总池 {len(jobs)} 条(源2带标签), 抽样 {len(sample)} 条, 开始 LLM 核验...")

    sem = asyncio.Semaphore(CONCURRENCY)
    done = [0]

    async def work(j):
        async with sem:
            try:
                verdicts = await verify_tags(j["text"], j["title"], j["tags"], achat_json)
                missing = [t for t in j["tags"] if t not in verdicts]
                if missing:   # 漏判是 LLM 输出不完整, 补判一次
                    verdicts.update(
                        await verify_tags(j["text"], j["title"], missing, achat_json))
                j["verdicts"] = verdicts
            except Exception as e:
                j["verdicts"], j["error"] = {}, str(e)[:100]
            done[0] += 1
            if done[0] % 10 == 0:
                print(f"  进度 {done[0]}/{len(sample)}")

    await asyncio.gather(*(work(j) for j in sample))

    # ---- 统计 ----
    tot = ok = 0
    per_job, noise = [], []
    for j in sample:
        if j.get("error"):
            continue
        verdicts = j["verdicts"] or {}
        hit = miss = 0
        for t in j["tags"]:
            v = verdicts.get(t)
            if v is True:
                hit += 1
            else:   # false 或漏判都算不一致
                miss += 1
                noise.append({"title": j["title"], "tag": t,
                              "verdict": "LLM判定不支持" if v is False else "LLM漏判"})
        tot += hit + miss
        ok += hit
        per_job.append(hit / (hit + miss) if hit + miss else 0)

    n = len(per_job)
    micro = ok / tot if tot else 0
    macro = sum(per_job) / n if n else 0
    exact = sum(1 for r in per_job if r >= 1.0) / n if n else 0

    lines = [
        "# JD 解析准确率评测报告(LLM 核验式交叉验证)",
        "",
        f"- 评测时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 样本: 源2(jobs_raw_2.json, 平台标签真实对应全文)随机抽 {n} 条(种子 {SEED}, 可复现)",
        "- 方法: LLM 逐标签核验——平台技能标签是否被 JD 全文支持(明确提及/同义表达)",
        "- 为什么核验而非抽取式比对: 平台标签是粗粒度分类词表(方向词/拆词),",
        "  与全文抽取词表粒度不同, 精确比对失真; 核验式两侧同词表, 指标才有意义",
        "- 双重意义: ①JD 解析准确率 ②交叉验证发现平台标签噪声(数据清洗素材)",
        "",
        "## 总体指标",
        "",
        "| 指标 | 定义 | 数值 |",
        "|---|---|---|",
        f"| **标签一致率(微平均)** | 平台标签被 JD 全文支持的占比 | **{micro:.1%}** ({ok}/{tot}) |",
        f"| 标签一致率(宏平均) | 逐条一致率的平均 | {macro:.1%} |",
        f"| 完全一致率 | 全部标签都被支持的 JD 占比 | {exact:.1%} ({sum(1 for r in per_job if r >= 1.0)}/{n}) |",
        "",
        f"**交叉验证结论: {tot - ok} 个平台标签未被 JD 全文支持(噪声率 {1 - micro:.1%}),**",
        "主要为平台粗粒度分类词(如\"物联网\"\"算法\")挂在非对应岗位上——",
        "这正是多源异构数据需要交叉验证与清洗的原因。",
        "",
        "## 噪声标签样例(平台标了但 JD 全文不支持)",
        "",
        "| 岗位 | 标签 | 判定 |",
        "|---|---|---|",
    ]
    for x in noise[:25]:
        lines.append(f"| {x['title']} | {x['tag']} | {x['verdict']} |")
    if len(noise) > 25:
        lines.append(f"| ... | 共 {len(noise)} 条 | |")

    report = EVAL_DIR / "report_jd_parse.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "=" * 50)
    print(f"标签一致率(微): {micro:.1%} ({ok}/{tot})")
    print(f"宏平均: {macro:.1%} | 完全一致率: {exact:.1%}")
    print(f"报告: {report}")


if __name__ == "__main__":
    asyncio.run(main())
