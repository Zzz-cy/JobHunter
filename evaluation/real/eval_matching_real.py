# -*- coding: utf-8 -*-
"""真实简历人岗匹配评测

用法:
  python eval_matching_real.py            # 第一步: 调推荐接口生成待标注文件(约2-5分钟)
  python eval_matching_real.py --score    # 第二步: 标注完 matching_real_answers.json 后打分

前置: 8000(主后端)已启动; 简历已上传(标题 真实-xxx)。
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # common.py 在 evaluation/
from common import API_BASE, client, load_db_config, login

EVAL_DIR = Path(__file__).resolve().parent
ANSWERS = EVAL_DIR / "matching_real_answers.json"
TOP_K = 5


def fetch_real_resumes(conn):
    """取 13 份真实简历(id/标题/姓名/技能)。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, name FROM resumes "
        "WHERE title LIKE '真实-%%' AND parse_status = 'done' ORDER BY id")
    rows = cur.fetchall()
    for r in rows:
        cur.execute(
            "SELECT s.name FROM resume_skills rs JOIN skills s ON rs.skill_id = s.id "
            "WHERE rs.resume_id = %s", (r["id"],))
        r["skills"] = sorted(x["name"] for x in cur.fetchall())
    return rows


def gen_candidates(headers):
    """第一步: 调推荐接口, 生成待标注 JSON + 阅读用 markdown。

    有 excluded_reason 的样本(库内无对口岗)不重新生成, 保留原条目。
    """
    conn = pymysql.connect(**load_db_config(), charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor)
    resumes = fetch_real_resumes(conn)
    cur = conn.cursor()

    old = json.loads(ANSWERS.read_text(encoding="utf-8")) if ANSWERS.exists() else []
    keep = [d for d in old if d.get("excluded_reason")]
    skip_ids = {d["resume_id"] for d in keep}
    resumes = [r for r in resumes if r["id"] not in skip_ids]
    print(f"\n生成推荐候选, 共 {len(resumes)} 份简历(每份含 LLM 重排, 稍等)\n")

    data = list(keep)
    for idx, r in enumerate(resumes, 1):
        print(f"[{idx}/{len(resumes)}] {r['title']} ...", end=" ", flush=True)
        try:
            resp = client.get(f"{API_BASE}/recommend",
                              params={"resume_id": r["id"]}, headers=headers)
            body = resp.json()
            if body.get("code") != 0:
                print("推荐失败:", body.get("message"))
                continue
            items = body["data"]["items"][:TOP_K]
        except Exception as exc:
            print("异常:", exc)
            continue

        cands = []
        for rank, it in enumerate(items, 1):
            jid = it["job"]["id"]
            cur.execute(
                "SELECT j.title, j.city, j.salary_min, j.salary_max, c.name company "
                "FROM jobs j LEFT JOIN companies c ON c.id = j.company_id WHERE j.id = %s", (jid,))
            job = cur.fetchone() or {}
            cur.execute(
                "SELECT s.name FROM job_skills js JOIN skills s ON js.skill_id = s.id "
                "WHERE js.job_id = %s", (jid,))
            job_skills = sorted(x["name"] for x in cur.fetchall())
            salary = f"{job['salary_min'] // 1000}-{job['salary_max'] // 1000}K" \
                if job.get("salary_min") and job.get("salary_max") else "-"
            cands.append({
                "rank": rank,
                "job_id": jid,
                "title": job.get("title"),
                "company": job.get("company") or "-",
                "city": job.get("city") or "-",
                "salary": salary,
                "job_skills": job_skills,
                "match_score": str(it.get("score")),
                "reason": it.get("reason") or "-",
                "relevant": None,   # ← 人工标注: true / false / null(跳过)
            })
        data.append({
            "resume_id": r["id"], "resume": r["title"],
            "candidate": r["name"], "resume_skills": r["skills"],
            "candidates": cands,
        })
        print(f"Top{len(cands)} 已生成")
    conn.close()

    ANSWERS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 阅读用 markdown(不用于标注, 纯方便看)
    lines = ["# 真实简历人岗匹配 · 标注参考", "",
             "标注请在 matching_real_answers.json 里改 relevant: true/false",
             ""]
    for d in data:
        lines += [f"## {d['candidate']}({d['resume']})", "",
                  f"简历技能: {', '.join(d['resume_skills'])}", ""]
        for c in d["candidates"]:
            lines += [
                f"### {c['rank']}. {c['title']} | {c['company']} | {c['city']} | {c['salary']} "
                f"| 匹配分 {c['match_score']}",
                f"- 岗位要求: {', '.join(c['job_skills']) or '-'}",
                f"- 推荐理由: {c['reason']}",
                ""]
    (EVAL_DIR / "matching_real_标注参考.md").write_text("\n".join(lines), encoding="utf-8")

    total = sum(len(d["candidates"]) for d in data)
    print(f"\n候选已写入: {ANSWERS}(共 {total} 条待标注)")
    print(f"阅读参考: {EVAL_DIR / 'matching_real_标注参考.md'}")


def score():
    """第二步: 按人工标注算 P@5 / Top1 相关率 / MRR。"""
    data = json.loads(ANSWERS.read_text(encoding="utf-8"))

    total_marked = total_rel = 0
    top1_hits = 0
    rr_sum = 0.0
    n_resume = 0
    per_resume = []
    excluded = []

    for d in data:
        # 纳入标准: 库内需存在对口岗位(语料无相关文档测不了检索精度, 单列覆盖度)
        if d.get("excluded_reason"):
            excluded.append({"resume": d["resume"], "reason": d["excluded_reason"]})
            # 明细表也给一行, 13 份一眼齐(不计分)
            per_resume.append({"resume": d["resume"], "note": "单列(库内无对口岗)"})
            continue
        marked = [c for c in d["candidates"] if c["relevant"] is not None]
        if not marked:
            per_resume.append({"resume": d["resume"], "note": "未标注, 跳过"})
            continue
        n_resume += 1
        rel_n = sum(1 for c in marked if c["relevant"])
        rel_ranks = [c["rank"] for c in marked if c["relevant"]]
        p5 = rel_n / len(marked)
        rr = 1 / min(rel_ranks) if rel_ranks else 0.0
        total_marked += len(marked)
        total_rel += rel_n
        top1_hits += int(any(c["rank"] == 1 and c["relevant"] for c in marked))
        rr_sum += rr
        per_resume.append({
            "resume": d["resume"], "candidate": d["candidate"],
            "P@5": round(p5, 2), "MRR": round(rr, 2),
            "rel": rel_n, "marked": len(marked),
        })

    p_overall = total_rel / total_marked if total_marked else 0
    top1_rate = top1_hits / n_resume if n_resume else 0
    mrr = rr_sum / n_resume if n_resume else 0

    lines = [
        "# 真实简历人岗匹配评测报告(人工标注)",
        "",
        f"- 评测时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 样本: {n_resume}/{len(data)} 份真实简历(未标注的跳过), 每份评判系统 Top{TOP_K} 推荐",
        f"- 指标口径: **人工二元标注**(岗位适合该候选人=true), 未标注(null)不计入",
        "",
        "## 总体指标",
        "",
        "| 指标 | 定义 | 数值 |",
        "|---|---|---|",
        f"| **Precision@5** | 推荐出的岗位中人工判定相关的占比 | **{p_overall:.1%}** ({total_rel}/{total_marked}) |",
        f"| Top1 相关率 | 系统排第 1 的岗位被人工判定相关的简历占比 | {top1_rate:.1%} ({top1_hits}/{n_resume}) |",
        f"| MRR | 第一个相关岗位排名倒数的平均值(越接近 1 越好) | {mrr:.2f} |",
    ]
    if excluded:
        lines += [
            "",
            "## 单列样本(不计入检索精度)",
            "",
            "纳入标准: 语料库中需存在对口岗位。以下样本因库内无对口岗位单列——",
            "这是语料覆盖度问题(推荐器无法推荐不存在的岗位), 不是检索精度问题:",
            "",
        ]
        for e in excluded:
            lines.append(f"- {e['resume']}: {e['reason']}")
    lines += [
        "",
        "## 逐份明细",
        "",
        "| 简历 | 候选人 | 相关/已标注 | P@5 | MRR |",
        "|---|---|---|---|---|",
    ]
    for r in per_resume:
        if "note" in r:
            lines.append(f"| {r['resume']} | - | {r['note']} | - | - |")
        else:
            lines.append(f"| {r['resume']} | {r['candidate']} | {r['rel']}/{r['marked']} | {r['P@5']:.0%} | {r['MRR']:.2f} |")

    report = EVAL_DIR / "report_matching_real.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "=" * 50)
    print(f"P@5: {p_overall:.1%} | Top1相关率: {top1_rate:.1%} | MRR: {mrr:.2f}")
    print(f"报告: {report}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", action="store_true", help="标注完成后打分(默认生成候选)")
    args = parser.parse_args()

    if args.score:
        if not ANSWERS.exists():
            print(f"先跑生成: python {Path(__file__).name}")
            return
        score()
        return

    token = None
    for account in ("admin@jobhunter.local", "13800000000"):
        try:
            token = login(account, "123456")
            break
        except SystemExit:
            continue
    if not token:
        return
    gen_candidates({"Authorization": f"Bearer {token}"})


if __name__ == "__main__":
    main()
