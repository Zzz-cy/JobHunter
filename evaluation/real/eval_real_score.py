# -*- coding: utf-8 -*-
"""真实简历准确率评测: 人工标注答案 vs 库里解析结果。

与 eval_parse.py 同一套评分规则。真实简历以上传过(标题 真实-xxx),
按标题「真实-{文件名去扩展名}」直接命中, 没有的才补传。

前置: 8000(主后端)已启动; 8001 仅在需要补传时才要。
"""
from datetime import datetime
from pathlib import Path
import sys

import json
import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # common.py 在 evaluation/
from common import API_BASE, client, load_db_config, login, compare_field

EVAL_DIR = Path(__file__).resolve().parent
RESUMES_DIR = EVAL_DIR / "resumes"
FIELDS = ("name", "gender", "age", "phone", "email", "city", "work_years", "education")


def main():
    token = None
    for account in ("admin@jobhunter.local", "13800000000"):
        try:
            token = login(account, "123456")
            break
        except SystemExit:
            continue
    if not token:
        return
    headers = {"Authorization": f"Bearer {token}"}

    gt_list = json.loads((EVAL_DIR / "ground_truth_real.json").read_text(encoding="utf-8"))

    db_cfg = load_db_config()
    conn = pymysql.connect(**db_cfg, charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()

    results = []
    field_stat = {}      # 字段 → [对, 总]
    skill_recalls, skill_precisions = [], []

    print(f"\n真实简历准确率评测, 共 {len(gt_list)} 份(只读库比对, 不重新解析)\n")

    for idx, gt in enumerate(gt_list, 1):
        stem = Path(gt["file"]).stem
        cur.execute(
            "SELECT id, parse_status, name, gender, age, phone, email, city, "
            "work_years, education FROM resumes WHERE title = %s ORDER BY id DESC LIMIT 1",
            (f"真实-{stem}",))
        row = cur.fetchone()

        # 没传过的补传一次，走完整解析链路
        if row is None:
            pdf = RESUMES_DIR / gt["file"]
            print(f"[{idx}/{len(gt_list)}] {gt['file']} 未上传, 补传中 ...", end=" ", flush=True)
            with open(pdf, "rb") as f:
                resp = client.post(
                    f"{API_BASE}/resumes/upload", headers=headers,
                    files={"file": (pdf.name, f, "application/pdf")},
                    data={"title": f"真实-{stem}"})
            body = resp.json()
            if body.get("code") != 0 or body["data"]["parse_status"] != "done":
                print(f"解析失败: {body.get('message') or body['data'].get('parse_error')}")
                results.append({"file": gt["file"], "error": body.get("message")})
                continue
            cur.execute("SELECT id, parse_status, name, gender, age, phone, email, city, "
                        "work_years, education FROM resumes WHERE id = %s", (body["data"]["id"],))
            row = cur.fetchone()
            print("OK", end=" ")

        cur.execute(
            "SELECT s.name FROM resume_skills rs JOIN skills s ON rs.skill_id = s.id "
            "WHERE rs.resume_id = %s", (row["id"],))
        got_skills = sorted(r["name"] for r in cur.fetchall())

        # 标量字段: 标注为 null 的跳过
        detail = {}
        for field in FIELDS:
            if gt.get(field) is None:
                detail[field] = {"标注": None, "实际": row.get(field), "跳过": True}
                continue
            ok = compare_field(field, gt[field], row.get(field))
            field_stat.setdefault(field, [0, 0])
            field_stat[field][0] += int(ok)
            field_stat[field][1] += 1
            detail[field] = {"标注": gt[field], "实际": row.get(field), "通过": ok}

        # 技能: 标注空数组也跳过
        if gt.get("skills"):
            gt_set, got_set = set(gt["skills"]), set(got_skills)
            hit = gt_set & got_set
            recall = len(hit) / len(gt_set)
            precision = len(hit) / len(got_set) if got_set else 0.0
            skill_recalls.append(recall)
            skill_precisions.append(precision)
            skill_pass = recall >= 0.8
            field_stat.setdefault("skills", [0, 0])
            field_stat["skills"][0] += int(skill_pass)
            field_stat["skills"][1] += 1
            detail["skills"] = {"标注": sorted(gt_set), "实际": sorted(got_set),
                                "命中": sorted(hit), "召回率": round(recall, 2), "通过": skill_pass}
        else:
            detail["skills"] = {"标注": [], "实际": got_skills, "跳过": True}

        results.append({"file": gt["file"], "detail": detail})
        # 只统计"已标注且参与比对"的项, 分子分母口径一致
        scored = [d for d in detail.values() if not d.get("跳过")]
        ok_n = sum(1 for d in scored if d.get("通过"))
        print(f"[{idx}/{len(gt_list)}] {gt['file']}: {ok_n}/{len(scored)} 通过")

    conn.close()

    # 报告
    total_ok = sum(v[0] for v in field_stat.values())
    total_all = sum(v[1] for v in field_stat.values())
    overall = total_ok / total_all if total_all else 0
    n_recall = len(skill_recalls)
    avg_recall = sum(skill_recalls) / n_recall if n_recall else 0
    avg_precision = sum(skill_precisions) / n_recall if n_recall else 0
    unannotated = sum(1 for r in results for d in r.get("detail", {}).values() if d.get("跳过"))

    lines = [
        "# 真实简历解析准确率评测报告",
        "",
        f"- 评测时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 样本: 老师提供的真实简历 {len(gt_list)} 份, 人工标注答案(ground_truth_real.json)",
        f"- 评分规则: 与合成简历评测一致(age/work_years ±1, phone 比4位, 技能召回≥0.8 通过)",
        f"- 未标注字段 {unannotated} 项已跳过(不计分母)",
        "",
        "## 总体指标",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| **综合准确率(真实简历)** | **{overall:.1%}** ({total_ok}/{total_all}) |",
    ]
    if n_recall:
        lines += [
            f"| 技能平均召回率 | {avg_recall:.1%} |",
            f"| 技能平均精确率 | {avg_precision:.1%} |",
            "",
            "> 精确率口径说明: 标注只列了核心技能, 系统多抽出的真技能(如 Dreamweaver/CAD/神经网络)",
            "> 未逐一标注, 会拉低该值; 技能质量以召回率为准(通过线 0.8)。",
        ]
    lines += ["", "## 分字段", "", "| 字段 | 准确率 |", "|---|---|"]
    for field in FIELDS + ("skills",):
        ok, tot = field_stat.get(field, [0, 0])
        lines.append(f"| {field} | {ok / tot:.1%} ({ok}/{tot}) |" if tot else f"| {field} | 未标注 |")

    lines += ["", "## 逐份明细(仅列出未通过项)", ""]
    any_fail = False
    for r in results:
        fails = [f"{f}(标注:{d['标注']}/实际:{d['实际']})"
                 for f, d in r.get("detail", {}).items() if not d.get("跳过") and not d.get("通过")]
        if "error" in r:
            any_fail = True
            lines.append(f"- ❌ {r['file']}: {r['error']}")
        elif fails:
            any_fail = True
            lines.append(f"- ⚠ {r['file']}: " + "; ".join(fails))
    if not any_fail:
        lines.append("- 全部通过 🎉")

    report = EVAL_DIR / "report_real_accuracy.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "=" * 50)
    print(f"真实简历综合准确率: {overall:.1%} ({total_ok}/{total_all})")
    if n_recall:
        print(f"技能平均召回: {avg_recall:.1%} | 精确: {avg_precision:.1%}")
    print(f"报告: {report}")


if __name__ == "__main__":
    main()
