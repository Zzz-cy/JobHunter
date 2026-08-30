# -*- coding: utf-8 -*-
"""
生成"高难度仿真"测试简历(6 份) + 追加进 ground_truth.json

模拟真实简历的六大难点(每份埋 1-2 个坑, 控制掉分幅度):
    hard_01: 隐含年限(只写起止时间, 不写"X年经验") + 非标准栏目标签
    hard_02: 无技能栏, 技能全部埋在工作描述里
    hard_03: 版式乱序(教育在最前) + 技能别名(Vue.js/Python3, gt用标准名)
    hard_04: 段落式自我介绍(无结构化栏目), 中英混杂, 口语化
    hard_05: 字段矛盾(基本情况写本科, 教育经历写硕士) + 错别字
    hard_06: 应届生, 只有实习+项目经历, 技能埋在项目描述

用法(在 backend 目录):
    .venv\\Scripts\\python.exe evaluation\\gen_resumes_hard.py
    (先跑 gen_resumes.py 生成简单集, 本脚本在其基础上追加)
"""
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

EVAL_DIR = Path(__file__).resolve().parent
OUT_DIR = EVAL_DIR / "test_resumes"
GT_PATH = EVAL_DIR / "ground_truth.json"

# ============================================================
# 6 份困难简历(gT 字段 = 期望解析结果; PDF 内容故意"绕着写")
# ============================================================
HARD = [
    {
        # 坑1: 全文不写"4年经验", 只给起止时间 2020.07-2024.08, 要 LLM 自己算
        # 坑2: 栏目标签非标准(基本情况/教育背景/工作背景/技能特长)
        "file": "hard_01_hejun.pdf", "name": "何骏", "gender": 0, "age": 30,
        "phone": "15811110001", "email": "hejun@example.com",
        "city": "杭州", "work_years": 4, "education": "本科",
        "intent": "Go 后端开发工程师",
        "skills": ["Go", "MySQL", "Redis", "Docker", "Kubernetes"],
        "exp_count": 2, "latest_company": "某电商平台",
        "pdf": [
            ("t", "何骏的个人简历"),
            ("h", "一、基本情况"),
            ("p", "男, 1995年3月生, 现居杭州, 手机 15811110001, 邮箱 hejun@example.com"),
            ("h", "二、教育背景"),
            ("p", "2014.09-2018.06 某工业大学 计算机科学与技术 本科"),
            ("h", "三、工作背景"),
            ("p", "2022.09-至今 某电商平台 后端开发工程师: 主导订单服务重构, 使用 Go 编写高并发微服务, MySQL 分库分表, Redis 缓存架构, 服务部署于 Kubernetes 集群"),
            ("p", "2020.07-2022.08 某软件公司 开发工程师: 参与物流系统开发, Go 后端接口, Docker 容器化交付"),
            ("h", "四、技能特长"),
            ("p", "Golang / MySQL 调优 / Redis / 容器化(Docker, K8s)"),
        ],
    },
    {
        # 坑: 没有技能栏, 技能全埋在工作描述句子里
        "file": "hard_02_shenshuyao.pdf", "name": "沈书瑶", "gender": 1, "age": 27,
        "phone": "15922220002", "email": "shensy@example.com",
        "city": "深圳", "work_years": 4, "education": "本科",
        "intent": "前端开发工程师",
        "skills": ["React", "TypeScript", "Node.js", "Webpack", "Vue"],
        "exp_count": 2, "latest_company": "某互联网公司",
        "pdf": [
            ("t", "沈书瑶"),
            ("p", "女 / 27岁 / 深圳 / 15922220002 / shensy@example.com / 求职意向: 前端开发工程师"),
            ("h", "教育经历"),
            ("p", "2016.09-2020.06 某大学 软件工程 本科"),
            ("h", "工作经历"),
            ("p", "2022.03-至今 某互联网公司 前端工程师: 负责中后台系统, 使用 React 和 TypeScript 开发组件库, 搭建 Node.js BFF 层聚合接口, Webpack 构建性能优化使打包时间缩短 40%"),
            ("p", "2020.07-2022.02 某科技公司 前端开发: 参与移动端 H5 项目, 基于 Vue 完成活动页开发与埋点"),
        ],
    },
    {
        # 坑1: 版式乱序(教育在最前, 技能在最后)
        # 坑2: 技能写别名 Vue.js / Python3, gt 用字典标准名(测归一化缺口)
        "file": "hard_03_gaoyichen.pdf", "name": "高逸辰", "gender": 0, "age": 26,
        "phone": "15733330003", "email": "gaoyc@example.com",
        "city": "成都", "work_years": 3, "education": "本科",
        "intent": "全栈开发工程师",
        "skills": ["Python", "Vue", "MySQL", "Docker"],
        "exp_count": 1, "latest_company": "某创业公司",
        "pdf": [
            ("t", "高逸辰 - 求职全栈开发"),
            ("h", "教育经历"),
            ("p", "2018.09-2022.06 某电子科大 计算机应用 本科"),
            ("h", "基本信息"),
            ("p", "男, 26岁, 成都, 15733330003, gaoyc@example.com"),
            ("h", "工作经历"),
            ("p", "2022.07-至今 某创业公司 全栈工程师: 后端用 Python3 和 FastAPI 写接口, 前端页面用 Vue.js 组件化开发, 数据存 MySQL, Docker 部署上线"),
            ("h", "技能"),
            ("p", "Python3 / Vue.js / MySQL / Docker"),
        ],
    },
    {
        # 坑: 段落式自我介绍, 无结构化栏目, 口语化+中英混杂
        "file": "hard_04_songyutong.pdf", "name": "宋雨桐", "gender": 1, "age": 26,
        "phone": "15644440004", "email": "songyt@example.com",
        "city": "上海", "work_years": 4, "education": "大专",
        "intent": "Java 后端开发",
        "skills": ["Java", "Spring Boot", "MySQL", "Redis"],
        "exp_count": 2, "latest_company": "某外包公司",
        "pdf": [
            ("t", "个人简历"),
            ("p", "我叫宋雨桐, 女, 今年26岁, 坐标上海。做 Java 开发 4 年多了, 手机 15644440004, 邮箱 songyt@example.com。大专学历, 学的软件技术专业。"),
            ("p", "刚毕业在一家小公司写增删改查, 后来去外包公司接触了 Spring Boot 微服务项目, 天天和 MySQL、Redis 打交道, 也带过两个新人。想找个 Java 后端的坑, 踏实肯干不摸鱼。"),
        ],
    },
    {
        # 坑1: 字段矛盾(基本情况写"本科", 教育经历写"硕士") → gt 以教育经历为准
        # 坑2: 错别字("熟熟悉") → 测容错
        "file": "hard_05_luojianhao.pdf", "name": "罗健豪", "gender": 0, "age": 29,
        "phone": "15555550005", "email": "luojh@example.com",
        "city": "北京", "work_years": 6, "education": "硕士",
        "intent": "算法工程师",
        "skills": ["Python", "PyTorch", "机器学习", "SQL"],
        "exp_count": 2, "latest_company": "某AI公司",
        "pdf": [
            ("t", "罗健豪"),
            ("p", "男 / 29岁 / 北京 / 15555550005 / luojh@example.com / 学历: 本科 / 求职: 算法工程师"),
            ("h", "教育经历"),
            ("p", "2015.09-2018.06 某大学 计算机技术 硕士"),
            ("p", "2011.09-2015.06 某大学 软件工程 本科"),
            ("h", "工作经历"),
            ("p", "2020.07-至今 某AI公司 算法工程师: 熟熟悉 PyTorch, 负责 CTR 模型迭代, 使用 Python 离线训练, SQL 拉取样本, 上线后点击率提升明显"),
            ("p", "2018.07-2020.06 某互联网公司 机器学习工程师: 参与推荐系统特征工程"),
        ],
    },
    {
        # 坑: 应届生, 无正式工作, 技能埋在实习/项目描述里
        "file": "hard_06_dengshihan.pdf", "name": "邓诗涵", "gender": 1, "age": 22,
        "phone": "15466660006", "email": "dengsh@example.com",
        "city": "武汉", "work_years": 0, "education": "本科",
        "intent": "测试工程师",
        "skills": ["Python", "Selenium", "MySQL", "Postman"],
        "exp_count": 1, "latest_company": "某科技公司(实习)",
        "pdf": [
            ("t", "邓诗涵的简历"),
            ("p", "女 / 22岁 / 武汉 / 15466660006 / dengsh@example.com / 2025届本科毕业生 / 求职意向: 软件测试工程师"),
            ("h", "教育经历"),
            ("p", "2021.09-2025.06 某大学 软件工程 本科"),
            ("h", "实习与项目"),
            ("p", "2024.06-2024.09 某科技公司(实习) 测试实习生: 编写 Python 自动化脚本(Selenium 驱动浏览器回归测试), 用 Postman 做接口验证, SQL 核对数据落库"),
            ("p", "毕业设计: 电商测试平台, 包含用例管理和缺陷跟踪模块"),
        ],
    },
]


def _styles():
    return {
        "t": ParagraphStyle("t", fontName="STSong-Light", fontSize=18, leading=24, spaceAfter=6),
        "h": ParagraphStyle("h", fontName="STSong-Light", fontSize=12.5, leading=18,
                            spaceBefore=8, spaceAfter=3, textColor="#1a1a1a"),
        "p": ParagraphStyle("p", fontName="STSong-Light", fontSize=10.5, leading=17, textColor="#333333"),
    }


def build_one(r: dict) -> None:
    doc = SimpleDocTemplate(
        str(OUT_DIR / r["file"]), pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=15*mm, bottomMargin=15*mm,
    )
    st = _styles()
    story = []
    for kind, text in r["pdf"]:
        story.append(Paragraph(text, st[kind]))
        story.append(Spacer(1, 2*mm) if kind == "p" else Spacer(1, 1*mm))
    doc.build(story)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for r in HARD:
        build_one(r)
        print(f"  ✅ {r['file']}  {r['name']}({r['education']}/{r['work_years']}年) 坑:{r['file'].split('_')[1]}")

    # 追加进 ground_truth.json(与简单集共用一个文件, eval 一次跑全部)
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    existing = {g["file"] for g in gt}
    for r in HARD:
        if r["file"] not in existing:
            gt.append({k: v for k, v in r.items() if k != "pdf"})
    GT_PATH.write_text(json.dumps(gt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nground_truth.json 合并完成: 共 {len(gt)} 份(简单+困难)")


if __name__ == "__main__":
    main()
