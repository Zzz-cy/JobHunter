# -*- coding: utf-8 -*-
"""
简历解析准确率评测

流程: 上传测试简历 → 等待 LLM 解析 → 从数据库读解析结果 → 与标准答案逐字段比对 → 生成报告

前置条件:
    1. 主后端(8000)已启动
    2. LLM 服务(8001)已启动 —— 解析靠它
    3. 先跑过 gen_resumes.py 生成测试简历和标准答案

评分规则:
    - name / gender / city / education: 完全一致算对
    - age / work_years: 允许 ±1 (LLM 按年份推算有合理误差)
    - phone: 后 4 位一致算对 (LLM 可能脱敏返回 138****xxxx)
    - email: 忽略大小写完全一致
    - skills: 召回率≥0.8 算该字段通过(单独报告精确率/召回率)
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import httpx
import pymysql

from common import API_BASE, client, load_db_config, login

EVAL_DIR = Path(__file__).resolve().parent


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def compare_field(field: str, gt, got) -> bool:
    """单个字段比对, 按上面注释的评分规则。"""
    if got is None:
        return False
    if field in ("name", "city", "education"):
        return str(got).strip() == str(gt).strip()
    if field == "gender":
        return int(got) == int(gt)
    if field in ("age", "work_years"):
        return abs(int(got) - int(gt)) <= 1
    if field == "phone":
        g, p = digits(str(gt)), digits(str(got))
        return bool(p) and p[-4:] == g[-4:]
    if field == "email":
        return str(got).strip().lower() == str(gt).strip().lower()
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default="admin@jobhunter.local")
    parser.add_argument("--password", default="123456")
    args = parser.parse_args()

    gt_list = json.loads((EVAL_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    resumes_dir = EVAL_DIR / "test_resumes"
    token = login(args.account, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    db_cfg = load_db_config()
    # autocommit=True: 每次查询都是新事务, 否则 REPEATABLE READ 快照看不到后端新插入的简历行
    conn = pymysql.connect(**db_cfg, charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor)

    results = []          # 每份简历的明细
    field_stat = {}       # 字段 → [对, 总] (除 skills 外的 7 个标量字段)
    skill_recalls, skill_precisions = [], []
    mapping = []          # file → resume_id, 给匹配评测用

    print(f"\n开始评测, 共 {len(gt_list)} 份简历(LLM 解析每份约 10~30 秒, 请耐心)\n")

    for idx, gt in enumerate(gt_list, 1):
        pdf_path = resumes_dir / gt["file"]
        print(f"[{idx}/{len(gt_list)}] {gt['name']} ({gt['intent']}) ...", end=" ", flush=True)

        # ---- 1. 上传(接口同步等解析) ----
        try:
            with open(pdf_path, "rb") as f:
                resp = client.post(
                    f"{API_BASE}/resumes/upload",
                    headers=headers,
                    files={"file": (pdf_path.name, f, "application/pdf")},
                    data={"title": f"评测-{gt['name']}"},
                )
            body = resp.json()
            if body.get("code") != 0:
                print(f"上传失败: {body.get('message')}")
                results.append({"name": gt["name"], "error": body.get("message")})
                continue
            upload = body["data"]
        except Exception as exc:
            print(f"上传异常: {exc}")
            results.append({"name": gt["name"], "error": str(exc)})
            continue

        resume_id = upload["id"]
        mapping.append({"file": gt["file"], "resume_id": resume_id, "name": gt["name"]})

        # ---- 2. 解析失败直接记录 ----
        if upload["parse_status"] != "done":
            print(f"解析失败: {upload.get('parse_error')}")
            results.append({"name": gt["name"], "resume_id": resume_id, "error": upload.get("parse_error")})
            for field in ("name", "gender", "age", "phone", "email", "city", "work_years", "education"):
                field_stat.setdefault(field, [0, 0])[1] += 1
            skill_recalls.append(0.0)
            skill_precisions.append(0.0)
            continue

        # ---- 3. 从库里取解析结果 ----
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, gender, age, phone, email, city, work_years, education "
                "FROM resumes WHERE id = %s", (resume_id,))
            row = cur.fetchone()
            cur.execute(
                "SELECT s.name FROM resume_skills rs JOIN skills s ON rs.skill_id = s.id "
                "WHERE rs.resume_id = %s", (resume_id,))
            got_skills = [r["name"] for r in cur.fetchall()]

        # ---- 4. 标量字段比对 ----
        row_detail = {}
        for field in ("name", "gender", "age", "phone", "email", "city", "work_years", "education"):
            got = (row or {}).get(field)
            ok = compare_field(field, gt[field], got)
            field_stat.setdefault(field, [0, 0])
            field_stat[field][0] += int(ok)
            field_stat[field][1] += 1
            row_detail[field] = {"期望": gt[field], "实际": got, "通过": ok}

        # ---- 5. 技能比对(集合交并) ----
        gt_set, got_set = set(gt["skills"]), set(got_skills)
        hit = gt_set & got_set
        recall = len(hit) / len(gt_set) if gt_set else 1.0
        precision = len(hit) / len(got_set) if got_set else 0.0
        skill_recalls.append(recall)
        skill_precisions.append(precision)
        skill_pass = recall >= 0.8

        results.append({
            "name": gt["name"], "resume_id": resume_id, "intent": gt["intent"],
            "fields": row_detail,
            "skills": {"期望": sorted(gt_set), "实际": sorted(got_set),
                       "命中": sorted(hit), "召回率": round(recall, 2),
                       "精确率": round(precision, 2), "通过": skill_pass},
        })
        print(f"标量 {sum(1 for f in row_detail.values() if f['通过'])}/8, "
              f"技能召回 {recall:.0%} (命中 {len(hit)}/{len(gt_set)})")

    conn.close()

    # ================= 统计与报告 =================
    total_ok = sum(v[0] for v in field_stat.values())
    total_all = sum(v[1] for v in field_stat.values())
    scalar_acc = total_ok / total_all if total_all else 0
    skill_field_pass = sum(1 for r in results if r.get("skills", {}).get("通过"))
    done_count = sum(1 for r in results if "fields" in r)
    avg_recall = sum(skill_recalls) / len(skill_recalls) if skill_recalls else 0
    avg_precision = sum(skill_precisions) / len(skill_precisions) if skill_precisions else 0
    overall = (total_ok + skill_field_pass) / (total_all + len(gt_list)) if gt_list else 0

    lines = [
        "# 简历解析准确率评测报告",
        "",
        f"- 评测时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 样本数量: {len(gt_list)} 份(解析成功 {done_count} 份)",
        f"- 评分规则: 标量字段允许 age/work_years ±1, phone 比后 4 位, skills 召回≥0.8 记通过",
        "",
        "## 总体指标",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| **综合字段准确率** | **{overall:.1%}** |",
        f"| 标量字段准确率 | {scalar_acc:.1%} ({total_ok}/{total_all}) |",
        f"| 技能字段通过率 | {skill_field_pass}/{len(gt_list)} |",
        f"| 技能平均召回率 | {avg_recall:.1%} |",
        f"| 技能平均精确率 | {avg_precision:.1%} |",
        "",
        "## 分字段准确率",
        "",
        "| 字段 | 准确率 |",
        "|---|---|",
    ]
    for field in ("name", "gender", "age", "phone", "email", "city", "work_years", "education"):
        ok, tot = field_stat.get(field, [0, 0])
        lines.append(f"| {field} | {ok / tot:.1%} ({ok}/{tot}) |" if tot else f"| {field} | - |")

    lines += ["", "## 每份简历明细", ""]
    for r in results:
        if "error" in r:
            lines.append(f"### {r['name']} ❌ 失败: {r['error']}")
            continue
        lines.append(f"### {r['name']}({r['intent']})")
        lines.append("")
        lines.append("| 字段 | 期望 | 实际 | 通过 |")
        lines.append("|---|---|---|---|")
        for f, d in r["fields"].items():
            lines.append(f"| {f} | {d['期望']} | {d['实际']} | {'✅' if d['通过'] else '❌'} |")
        sk = r["skills"]
        lines.append(f"| skills | {sk['期望']} | {sk['实际']} | {'✅' if sk['通过'] else '❌'} 召回{sk['召回率']} |")
        lines.append("")

    report = EVAL_DIR / "report_parse.md"
    report.write_text("\n".join(lines), encoding="utf-8")

    (EVAL_DIR / "parse_results.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 50)
    print(f"综合字段准确率: {overall:.1%}")
    print(f"标量字段准确率: {scalar_acc:.1%} | 技能平均召回: {avg_recall:.1%}")
    print(f"报告: {report}")
    print(f"resume_id 映射: {EVAL_DIR / 'parse_results.json'}")


if __name__ == "__main__":
    main()
