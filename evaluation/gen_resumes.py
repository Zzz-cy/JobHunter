# -*- coding: utf-8 -*-
"""生成评测用的测试简历(PDF) + 标准答案。

技能名全取自 skills 字典表的标准写法, 方便解析后归一比对。
10 份简历覆盖不同方向/学历/年限, 保证代表性。
"""
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle

# 注册中文字体
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

EVAL_DIR = Path(__file__).resolve().parent
OUT_DIR = EVAL_DIR / "test_resumes"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 10 份简历档案(PDF 内容与标准答案的唯一数据源)
RESUMES = [
    {
        "file": "resume_01_liwei.pdf",
        "name": "李伟", "gender": 0, "age": 28,
        "phone": "13812340001", "email": "liwei@example.com",
        "city": "北京", "work_years": 5, "education": "本科",
        "intent": "Python 后端工程师",
        "educations": [
            {"school": "北京邮电大学", "major": "计算机科学与技术", "degree": "本科",
             "start_date": "2016-09", "end_date": "2020-06"},
        ],
        "experiences": [
            {"company": "字节跳动", "title": "Python 后端工程师", "start_date": "2022-04", "end_date": "至今",
             "description": "负责电商中台微服务开发, 使用 Python 和 Django 框架, 基于 MySQL 与 Redis 支撑高并发订单场景, 服务通过 Docker 容器化部署。"},
            {"company": "新浪网技术(中国)有限公司", "title": "后端开发工程师", "start_date": "2020-07", "end_date": "2022-03",
             "description": "参与内容平台接口开发, 编写 Python 脚本做数据处理, 使用 MySQL 设计业务表结构。"},
        ],
        "skills": ["Python", "Django", "MySQL", "Redis", "Docker"],
    },
    {
        "file": "resume_02_wangfang.pdf",
        "name": "王芳", "gender": 1, "age": 26,
        "phone": "13912340002", "email": "wangfang@example.com",
        "city": "上海", "work_years": 3, "education": "本科",
        "intent": "前端开发工程师",
        "educations": [
            {"school": "华东师范大学", "major": "软件工程", "degree": "本科",
             "start_date": "2017-09", "end_date": "2021-06"},
        ],
        "experiences": [
            {"company": "拼多多", "title": "前端开发工程师", "start_date": "2023-05", "end_date": "至今",
             "description": "负责营销活动页开发, 使用 Vue3 组件化开发, 配合 JavaScript 与 CSS 完成动效, 部分核心页面迁移到 React。"},
            {"company": "上海寻梦信息技术有限公司", "title": "前端开发实习生", "start_date": "2022-11", "end_date": "2023-04",
             "description": "维护后台管理系统, 使用 Vue 和 Element 组件库搭建页面。"},
        ],
        "skills": ["JavaScript", "Vue", "React", "CSS"],
    },
    {
        "file": "resume_03_zhangpeng.pdf",
        "name": "张鹏", "gender": 0, "age": 31,
        "phone": "13612340003", "email": "zhangpeng@example.com",
        "city": "深圳", "work_years": 7, "education": "硕士",
        "intent": "Java 后端开发工程师",
        "educations": [
            {"school": "华南理工大学", "major": "计算机技术", "degree": "硕士",
             "start_date": "2015-09", "end_date": "2018-06"},
            {"school": "武汉理工大学", "major": "计算机科学与技术", "degree": "本科",
             "start_date": "2011-09", "end_date": "2015-06"},
        ],
        "experiences": [
            {"company": "腾讯科技(深圳)有限公司", "title": "高级后端开发工程师", "start_date": "2021-06", "end_date": "至今",
             "description": "负责支付网关核心链路, 使用 Java 和 Spring Boot 微服务架构, MySQL 分库分表, Redis 缓存热点数据, Kafka 异步削峰。"},
            {"company": "华为技术有限公司", "title": "Java 开发工程师", "start_date": "2018-07", "end_date": "2021-05",
             "description": "参与云平台计费系统开发, 基于 Spring Boot 框架实现账单服务。"},
        ],
        "skills": ["Java", "Spring Boot", "MySQL", "Redis", "Kafka"],
    },
    {
        "file": "resume_04_chenjing.pdf",
        "name": "陈静", "gender": 1, "age": 27,
        "phone": "13712340004", "email": "chenjing@example.com",
        "city": "杭州", "work_years": 4, "education": "本科",
        "intent": "数据分析师",
        "educations": [
            {"school": "浙江工商大学", "major": "统计学", "degree": "本科",
             "start_date": "2018-09", "end_date": "2022-06"},
        ],
        "experiences": [
            {"company": "阿里巴巴集团", "title": "数据分析师", "start_date": "2024-01", "end_date": "至今",
             "description": "负责淘宝用户增长专题分析, 使用 Python 做数据清洗与建模, SQL 提取数仓数据, Tableau 制作可视化看板, 输出 Excel 分析报告。"},
            {"company": "杭州有赞科技有限公司", "title": "商业分析师", "start_date": "2022-07", "end_date": "2023-12",
             "description": "搭建商家经营指标体系, 使用 SQL 与 Excel 完成周报自动化。"},
        ],
        "skills": ["Python", "SQL", "Excel", "Tableau", "数据分析"],
    },
    {
        "file": "resume_05_liuyang.pdf",
        "name": "刘洋", "gender": 0, "age": 29,
        "phone": "13512340005", "email": "liuyang@example.com",
        "city": "北京", "work_years": 6, "education": "硕士",
        "intent": "算法工程师",
        "educations": [
            {"school": "北京大学", "major": "计算机科学与技术", "degree": "硕士",
             "start_date": "2017-09", "end_date": "2020-06"},
            {"school": "哈尔滨工业大学", "major": "计算机科学与技术", "degree": "本科",
             "start_date": "2013-09", "end_date": "2017-06"},
        ],
        "experiences": [
            {"company": "百度在线网络技术(北京)有限公司", "title": "算法工程师", "start_date": "2022-03", "end_date": "至今",
             "description": "负责搜索排序模型优化, 使用 Python 开发机器学习 pipeline, 基于 PyTorch 训练深度学习模型, 持续迭代 CTR 预估算法。"},
            {"company": "北京字节跳动科技有限公司", "title": "机器学习工程师", "start_date": "2020-07", "end_date": "2022-02",
             "description": "推荐系统召回层开发, 使用 TensorFlow 搭建离线训练任务。"},
        ],
        "skills": ["Python", "PyTorch", "机器学习", "深度学习", "TensorFlow"],
    },
    {
        "file": "resume_06_zhaolei.pdf",
        "name": "赵磊", "gender": 0, "age": 25,
        "phone": "15812340006", "email": "zhaolei@example.com",
        "city": "成都", "work_years": 3, "education": "大专",
        "intent": "测试工程师",
        "educations": [
            {"school": "成都信息工程大学", "major": "软件技术", "degree": "大专",
             "start_date": "2019-09", "end_date": "2022-06"},
        ],
        "experiences": [
            {"company": "成都极米科技股份有限公司", "title": "测试工程师", "start_date": "2023-07", "end_date": "至今",
             "description": "负责投影仪固件功能测试, 使用 Python 编写自动化测试脚本, 基于 Selenium 搭建 Web 端回归测试, 维护 Linux 测试环境。"},
            {"company": "成都尼毕鲁科技股份有限公司", "title": "游戏测试员", "start_date": "2022-07", "end_date": "2023-06",
             "description": "手游功能与兼容性测试, 编写测试用例并跟踪缺陷。"},
        ],
        "skills": ["Python", "Selenium", "自动化测试", "Linux"],
    },
    {
        "file": "resume_07_sunyue.pdf",
        "name": "孙悦", "gender": 1, "age": 28,
        "phone": "15012340007", "email": "sunyue@example.com",
        "city": "广州", "work_years": 5, "education": "本科",
        "intent": "大数据开发工程师",
        "educations": [
            {"school": "中山大学", "major": "计算机科学与技术", "degree": "本科",
             "start_date": "2016-09", "end_date": "2020-06"},
        ],
        "experiences": [
            {"company": "网易(杭州)网络有限公司", "title": "大数据开发工程师", "start_date": "2022-08", "end_date": "至今",
             "description": "负责音乐推荐数据管道建设, 使用 Spark 做离线计算, Flink 处理实时流数据, Kafka 同步埋点日志, Hadoop 集群运维与 SQL 优化。"},
            {"company": "唯品会信息技术有限公司", "title": "数据开发工程师", "start_date": "2020-07", "end_date": "2022-07",
             "description": "参与离线数仓开发, 编写 Hive SQL 脚本与调度任务。"},
        ],
        "skills": ["Hadoop", "Spark", "Flink", "Kafka", "SQL"],
    },
    {
        "file": "resume_08_zhoujie.pdf",
        "name": "周杰", "gender": 0, "age": 27,
        "phone": "15112340008", "email": "zhoujie@example.com",
        "city": "北京", "work_years": 4, "education": "本科",
        "intent": "运维开发工程师",
        "educations": [
            {"school": "北京化工大学", "major": "自动化", "degree": "本科",
             "start_date": "2017-09", "end_date": "2021-06"},
        ],
        "experiences": [
            {"company": "京东集团股份有限公司", "title": "运维开发工程师", "start_date": "2023-03", "end_date": "至今",
             "description": "负责物流系统稳定性, 使用 Kubernetes 编排容器服务, Docker 镜像流水线建设, Shell 与 Git 维护自动化运维脚本, 管理 Linux 集群。"},
            {"company": "用友网络科技股份有限公司", "title": "系统运维工程师", "start_date": "2021-07", "end_date": "2023-02",
             "description": "企业客户系统部署与巡检, 编写 Shell 巡检脚本。"},
        ],
        "skills": ["Linux", "Docker", "Kubernetes", "Shell", "Git"],
    },
    {
        "file": "resume_09_wumin.pdf",
        "name": "吴敏", "gender": 1, "age": 29,
        "phone": "18612340009", "email": "wumin@example.com",
        "city": "上海", "work_years": 6, "education": "本科",
        "intent": "产品经理",
        "educations": [
            {"school": "复旦大学", "major": "工商管理", "degree": "本科",
             "start_date": "2015-09", "end_date": "2019-06"},
        ],
        "experiences": [
            {"company": "上海哔哩哔哩科技有限公司", "title": "产品经理", "start_date": "2022-06", "end_date": "至今",
             "description": "负责创作工具产品规划, 需求分析与竞品调研, 推动项目管理和跨部门协作, 主导 3 个版本迭代上线。"},
            {"company": "携程计算机技术(上海)有限公司", "title": "助理产品经理", "start_date": "2019-07", "end_date": "2022-05",
             "description": "酒店频道需求文档撰写与项目跟进。"},
        ],
        "skills": ["产品经理", "需求分析", "项目管理"],
    },
    {
        "file": "resume_10_zhengqiang.pdf",
        "name": "郑强", "gender": 0, "age": 23,
        "phone": "13412340010", "email": "zhengqiang@example.com",
        "city": "武汉", "work_years": 0, "education": "本科",
        "intent": "C++ 开发工程师(应届)",
        "educations": [
            {"school": "华中科技大学", "major": "计算机科学与技术", "degree": "本科",
             "start_date": "2021-09", "end_date": "2025-06"},
        ],
        "experiences": [
            {"company": "小米科技有限责任公司", "title": "C++ 开发实习生", "start_date": "2024-06", "end_date": "2024-09",
             "description": "参与手机系统工具开发, 使用 C++ 编写性能优化模块, 刷题 300 道 familiar 数据结构与算法, 代码托管在 Git。"},
        ],
        "skills": ["C++", "数据结构", "算法", "Git"],
    },
]


# PDF 样式(ATS 纯文本版式: 无表格无图形, 方便 LLM 抽取)
S_NAME = ParagraphStyle("name", fontName="STSong-Light", fontSize=20, leading=26, spaceAfter=2)
S_INTENT = ParagraphStyle("intent", fontName="STSong-Light", fontSize=12, leading=18, textColor="#333333")
S_SECTION = ParagraphStyle("section", fontName="STSong-Light", fontSize=13, leading=18,
                           spaceBefore=10, spaceAfter=4, textColor="#1a1a1a")
S_BODY = ParagraphStyle("body", fontName="STSong-Light", fontSize=10.5, leading=17)
S_ITEM = ParagraphStyle("item", fontName="STSong-Light", fontSize=10.5, leading=17, leftIndent=10)


def fmt_date(d: str) -> str:
    return d.replace("-", ".")


def build_pdf(profile: dict, out_path: Path):
    story = [
        Paragraph(profile["name"], S_NAME),
        Paragraph(f"求职意向: {profile['intent']}", S_INTENT),
        Spacer(1, 4),

        Paragraph("基本信息", S_SECTION),
        Paragraph(
            f"性别: {'男' if profile['gender'] == 0 else '女'} | 年龄: {profile['age']} 岁 | "
            f"电话: {profile['phone']} | 邮箱: {profile['email']}",
            S_BODY,
        ),
        Paragraph(
            f"现居城市: {profile['city']} | 工作年限: {profile['work_years']} 年 | 最高学历: {profile['education']}",
            S_BODY,
        ),

        Paragraph("教育经历", S_SECTION),
    ]
    for edu in profile["educations"]:
        story.append(Paragraph(
            f"{edu['school']} | {edu['major']} | {edu['degree']} | "
            f"{fmt_date(edu['start_date'])} - {fmt_date(edu['end_date'])}",
            S_ITEM,
        ))

    label = "工作经历" if profile["work_years"] > 0 else "实习经历"
    story.append(Paragraph(label, S_SECTION))
    for exp in profile["experiences"]:
        end = "至今" if exp["end_date"] == "至今" else fmt_date(exp["end_date"])
        story.append(Paragraph(
            f"{exp['company']} | {exp['title']} | {fmt_date(exp['start_date'])} - {end}",
            S_ITEM,
        ))
        story.append(Paragraph(exp["description"], S_BODY))

    story.append(Paragraph("专业技能", S_SECTION))
    for sk in profile["skills"]:
        story.append(Paragraph(f"· {sk}", S_ITEM))

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"{profile['name']}的个人简历",
    )
    doc.build(story)


def main():
    for p in RESUMES:
        build_pdf(p, OUT_DIR / p["file"])
        print("生成:", p["file"], "-", p["name"], f"({p['intent']})")

    # 标准答案: 去掉 PDF 专用字段, 保留评测需要的期望值
    gt = []
    for p in RESUMES:
        gt.append({
            "file": p["file"],
            "name": p["name"],
            "gender": p["gender"],
            "age": p["age"],
            "phone": p["phone"],
            "email": p["email"],
            "city": p["city"],
            "work_years": p["work_years"],
            "education": p["education"],
            "intent": p["intent"],
            "skills": p["skills"],
            "exp_count": len(p["experiences"]),
            "latest_company": p["experiences"][0]["company"],
        })
    gt_file = EVAL_DIR / "ground_truth.json"
    gt_file.write_text(json.dumps(gt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n标准答案: {gt_file}")
    print(f"共 {len(RESUMES)} 份简历 → {OUT_DIR}")


if __name__ == "__main__":
    main()
