# -*- coding: utf-8 -*-
"""人岗匹配准确率评测: 调 /recommend 取 Top10, 和简历技能比对。

前置: 先跑过 eval_parse.py(简历已上传且解析成功)。
指标: M1 命中率(技能交集达阈值的岗位占比) / M2 平均重合度 / M3 Top1 相关率。
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

import httpx
import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # common.py 在 evaluation/
from common import API_BASE, client, load_db_config, login

EVAL_DIR = Path(__file__).resolve().parent
TOP_K = 10


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default="admin@jobhunter.local")
    parser.add_argument("--password", default="123456")
    args = parser.parse_args()

    # 简历映射 + 标准答案
    mapping = json.loads((EVAL_DIR / "parse_results.json").read_text(encoding="utf-8"))
    gt_list = {g["file"]: g for g in json.loads((EVAL_DIR / "ground_truth.json").read_text(encoding="utf-8"))}

    token = login(args.account, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    conn = pymysql.connect(**load_db_config(), charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)

    # 预加载: job_id → 技能集合(推荐结果对应的岗位技能从库里取)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT js.job_id, s.name FROM job_skills js JOIN skills s ON js.skill_id = s.id")
        job_skills = {}
        for r in cur.fetchall():
            job_skills.setdefault(r["job_id"], set()).add(r["name"])

    per_resume = []
    m1_hits, m1_total = 0, 0
    m2_sums, m2_count = 0.0, 0
    m3_hits = 0

    print(f"\n开始匹配评测, 共 {len(mapping)} 份简历\n")

    for idx, m in enumerate(mapping, 1):
        gt = gt_list[m["file"]]
        gt_skills = set(gt["skills"])
        threshold = 2 if len(gt_skills) >= 4 else 1  # 命中阈值: 简历技能多则要求≥2
        print(f"[{idx}/{len(mapping)}] {gt['name']} ({gt['intent']}) ...", end=" ", flush=True)

        try:
            resp = client.get(
                f"{API_BASE}/recommend",
                params={"resume_id": m["resume_id"]},
                headers=headers)
            body = resp.json()
            if body.get("code") != 0:
                print(f"推荐失败: {body.get('message')}")
                per_resume.append({"name": gt["name"], "error": body.get("message")})
                continue
            items = body["data"]["items"][:TOP_K]
        except Exception as exc:
            print(f"推荐异常: {exc}")
            per_resume.append({"name": gt["name"], "error": str(exc)})
            continue

        if not items:
            print("无推荐结果")
            per_resume.append({"name": gt["name"], "error": "无推荐结果"})
            continue

        strategy = body["data"].get("strategy", "?")
        job_details = []
        hit_cnt, overlap_sum = 0, 0.0

        for rank, item in enumerate(items, 1):
            job = item["job"]
            jid = job["id"]
            js = job_skills.get(jid, set())
            inter = js & gt_skills
            overlap = len(inter) / len(gt_skills) if gt_skills else 0
            is_hit = len(inter) >= threshold
            hit_cnt += int(is_hit)
            overlap_sum += overlap
            job_details.append({
                "rank": rank, "title": job.get("title"), "score": str(item.get("score")),
                "岗位技能": sorted(js), "命中技能": sorted(inter),
                "重合度": round(overlap, 2), "命中": bool(is_hit),
            })

        m1_rate = hit_cnt / len(items)
        m2_avg = overlap_sum / len(items)
        # Top1 相关: 标题含意向关键词, 或命中技能 ≥ 阈值
        top1 = job_details[0]
        intent_kw = [w for w in gt["intent"].replace("(应届)", "").replace("工程师", "").replace("开发", "")
                     .replace("师", "").split() if w] or [gt["intent"][:2]]
        top1_relevant = top1["命中"] or any(k in (top1["title"] or "") for k in intent_kw)

        m1_hits += hit_cnt
        m1_total += len(items)
        m2_sums += overlap_sum
        m2_count += len(items)
        m3_hits += int(top1_relevant)

        per_resume.append({
            "name": gt["name"], "intent": gt["intent"], "resume_id": m["resume_id"],
            "strategy": strategy, "期望技能": sorted(gt_skills),
            "命中率": round(m1_rate, 2), "平均重合度": round(m2_avg, 2),
            "top1相关": bool(top1_relevant), "jobs": job_details,
        })
        print(f"Top{len(items)} 命中 {m1_rate:.0%}, 平均重合度 {m2_avg:.0%}, 策略={strategy}")

    conn.close()

    # ================= 报告 =================
    valid = [r for r in per_resume if "error" not in r]
    M1 = m1_hits / m1_total if m1_total else 0
    M2 = m2_sums / m2_count if m2_count else 0
    M3 = m3_hits / len(valid) if valid else 0

    lines = [
        "# 人岗匹配准确率评测报告",
        "",
        f"- 评测时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 样本: {len(valid)}/{len(mapping)} 份简历, 每份取 Top{TOP_K} 推荐",
        "",
        "## 总体指标",
        "",
        "| 指标 | 定义 | 数值 |",
        "|---|---|---|",
        f"| **M1 匹配命中率** | Top10 岗位技能与简历技能交集达阈值的占比 | **{M1:.1%}** ({m1_hits}/{m1_total}) |",
        f"| M2 平均技能重合度 | 岗位技能∩简历技能 / 简历技能数 | {M2:.1%} |",
        f"| M3 Top1 相关率 | 排名第 1 岗位与简历相关的简历占比 | {M3:.1%} ({m3_hits}/{len(valid)}) |",
        "",
        "## 每份简历明细",
        "",
    ]
    for r in per_resume:
        if "error" in r:
            lines += [f"### {r['name']} ❌ {r['error']}", ""]
            continue
        lines += [
            f"### {r['name']}({r['intent']}) 命中率 {r['命中率']:.0%} · 重合度 {r['平均重合度']:.0%} · "
            f"Top1{'相关' if r['top1相关'] else '不相关'} · 策略 {r['strategy']}",
            "",
            f"简历技能: {', '.join(r['期望技能'])}",
            "",
            "| 排名 | 岗位 | 匹配分 | 命中技能 | 重合度 | 达标 |",
            "|---|---|---|---|---|---|",
        ]
        for j in r["jobs"]:
            lines.append(
                f"| {j['rank']} | {j['title']} | {j['score']} | "
                f"{', '.join(j['命中技能']) or '-'} | {j['重合度']:.0%} | {'✅' if j['命中'] else '❌'} |")
        lines.append("")

    report = EVAL_DIR / "report_matching.md"
    report.write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "=" * 50)
    print(f"M1 匹配命中率: {M1:.1%} | M2 平均技能重合度: {M2:.1%} | M3 Top1相关率: {M3:.1%}")
    print(f"报告: {report}")


if __name__ == "__main__":
    main()
