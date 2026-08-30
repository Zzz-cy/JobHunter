"""
批量生成 10 份仿真测试简历(测完即删, 已 gitignore)

用途:
    测试简历解析链路(LLM解析 + 学历/经验归一化 + 技能归一)。
    内容虚构但格式真实, 且故意埋了"脏数据"验证归一化:
      - resume_03: 学历写"统招本科"      → 应归一为"本科"
      - resume_05: 经验写"3年以上"        → 应归一为"3-5年"
      - resume_07: 技能写"Python3/py"     → 应归一命中字典"Python"
      - resume_09: 缺邮箱/缺城市          → 验证解析容错(不崩, 存null)

用法:
    cd backend && python gen_batch_resumes.py
    → 生成 test_resumes/resume_01.pdf ~ resume_10.pdf
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ---------- 中文字体 ----------
FONT_PATHS = {
    "SimSun": r"C:\Windows\Fonts\simsun.ttc",
    "SimHei": r"C:\Windows\Fonts\simhei.ttf",
}
for name, path in FONT_PATHS.items():
    if Path(path).exists():
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception:
            pass
BODY = "SimSun" if Path(FONT_PATHS["SimSun"]).exists() else "Helvetica"
TITLE = "SimHei" if Path(FONT_PATHS["SimHei"]).exists() else "Helvetica-Bold"

OUT_DIR = Path("test_resumes")

# ============================================================
# 10 份简历数据(多样性: 岗位方向/年限/学历/脏数据测试点)
# ============================================================
RESUMES = [
    {
        "file": "resume_01.pdf", "name": "陈嘉伟", "gender": "男", "age": 26,
        "edu": "本科", "exp": "3年", "city": "北京", "phone": "13800001001",
        "email": "chenjw@example.com", "target": "Python 后端工程师",
        "skills": ["Python", "Django", "MySQL", "Redis", "Docker"],
        "works": [
            ("某互联网公司", "Python 开发工程师", "2022.07 - 至今",
             "负责后台服务开发, 使用 Django 构建 RESTful API, Redis 缓存热点数据, 参与容器化部署"),
            ("某软件外包公司", "Python 开发工程师", "2021.03 - 2022.06",
             "参与企业管理系统开发, 负责报表模块和数据导入导出功能"),
        ],
        "school": ("某理工大学", "软件工程", "2017.09 - 2021.06"),
    },
    {
        "file": "resume_02.pdf", "name": "林晓婷", "gender": "女", "age": 24,
        "edu": "本科", "exp": "1年", "city": "上海", "phone": "13900002002",
        "email": "linxt@example.com", "target": "前端开发工程师",
        "skills": ["Vue", "JavaScript", "CSS", "HTML", "Webpack"],
        "works": [
            ("某电商平台", "前端开发工程师", "2024.07 - 至今",
             "负责商城活动页面开发, 使用 Vue3 组件化开发, 配合 Webpack 打包优化首屏加载"),
        ],
        "school": ("某师范大学", "计算机科学与技术", "2020.09 - 2024.06"),
    },
    {
        "file": "resume_03.pdf", "name": "王浩然", "gender": "男", "age": 29,
        "edu": "统招本科",   # ← 测试点: 应归一为"本科"
        "exp": "5年", "city": "深圳", "phone": "13600003003",
        "email": "wanghr@example.com", "target": "Java 后端工程师",
        "skills": ["Java", "Spring Boot", "MySQL", "Redis", "RabbitMQ"],
        "works": [
            ("某金融科技公司", "Java 开发工程师", "2021.05 - 至今",
             "负责支付网关模块, 使用 Spring Boot 构建微服务, Redis 分布式锁, RabbitMQ 异步解耦"),
            ("某银行外包", "Java 开发工程师", "2019.07 - 2021.04",
             "参与信贷系统开发, 负责对账模块和批处理任务"),
        ],
        "school": ("某财经大学", "信息管理与信息系统", "2015.09 - 2019.06"),
    },
    {
        "file": "resume_04.pdf", "name": "苏梦琪", "gender": "女", "age": 27,
        "edu": "硕士", "exp": "3年", "city": "杭州", "phone": "13700004004",
        "email": "sumq@example.com", "target": "数据分析师",
        "skills": ["Python", "SQL", "Pandas", "Tableau", "Excel"],
        "works": [
            ("某零售集团", "数据分析师", "2022.08 - 至今",
             "负责销售数据分析, 使用 Python+Pandas 清洗数据, SQL 提取数仓数据, Tableau 制作可视化看板"),
            ("某咨询公司", "数据专员", "2023.03 - 2024.07",
             "参与市场调研项目, 使用 Excel 和 SQL 完成数据整理和报告"),
        ],
        "school": ("某统计大学", "应用统计学", "2019.09 - 2022.06"),
    },
    {
        "file": "resume_05.pdf", "name": "赵子轩", "gender": "男", "age": 31,
        "edu": "本科", "exp": "8年",  # 测试点: 数字归一(应归到5-10年)
        "city": "北京", "phone": "13500005005",
        "email": "zhaozx@example.com", "target": "运维工程师",
        "skills": ["Linux", "Docker", "Kubernetes", "Shell", "Jenkins"],
        "works": [
            ("某云计算公司", "运维开发工程师", "2019.03 - 至今",
             "负责集群运维和发布系统, K8s 集群管理, Jenkins 流水线维护, 编写 Shell 自动化脚本"),
            ("某游戏公司", "系统运维工程师", "2016.07 - 2019.02",
             "负责服务器日常巡检和应用部署, 参与 Docker 容器化改造"),
        ],
        "school": ("某工业大学", "网络工程", "2012.09 - 2016.06"),
    },
    {
        "file": "resume_06.pdf", "name": "黄雅雯", "gender": "女", "age": 23,
        "edu": "本科", "exp": "应届", "city": "广州", "phone": "13400006006",
        "email": "huangyw@example.com", "target": "测试工程师",
        "skills": ["Python", "Selenium", "Postman", "MySQL", "JMeter"],
        "works": [],   # 应届无工作经历 → 测空经历容错
        "school": ("某大学", "软件工程", "2021.09 - 2025.06"),
        "campus": ("校项目经历: 毕业设计开发了电商平台测试系统, 使用 Selenium 自动化测试, Postman 接口测试, JMeter 压力测试"),
    },
    {
        "file": "resume_07.pdf", "name": "周天佑", "gender": "男", "age": 28,
        "edu": "本科", "exp": "4年", "city": "成都", "phone": "13300007007",
        "email": "zhouty@example.com", "target": "全栈开发工程师",
        "skills": ["Python3", "py", "Vue", "MySQL", "Docker"],
        #              ↑↑↑ 测试点: 技能别名, 应归一命中字典的"Python"
        "works": [
            ("某创业公司", "全栈开发工程师", "2021.07 - 至今",
             "独立负责产品从开发到部署, 后端使用 Python3(py) + FastAPI, 前端 Vue3, Docker 部署"),
        ],
        "school": ("某电子科技大学", "计算机应用技术", "2017.09 - 2021.06"),
    },
    {
        "file": "resume_08.pdf", "name": "吴思远", "gender": "男", "age": 33,
        "edu": "博士", "exp": "5年", "city": "北京", "phone": "13200008008",
        "email": "wusy@example.com", "target": "算法工程师",
        "skills": ["Python", "PyTorch", "机器学习", "深度学习", "SQL"],
        "works": [
            ("某人工智能公司", "算法工程师", "2021.06 - 至今",
             "负责推荐算法优化, 使用 PyTorch 训练深度学习模型, 线上效果点击率提升 8%"),
            ("某研究院", "研究助理", "2018.07 - 2021.05",
             "参与机器学习课题研究, 发表论文 2 篇"),
        ],
        "school": ("某交通大学", "计算机科学与技术(博士)", "2015.09 - 2018.06"),
    },
    {
        "file": "resume_09.pdf", "name": "郑安妮", "gender": "女", "age": 25,
        "edu": "大专", "exp": "2年", "city": None,  # ← 测试点: 缺城市
        "phone": "13100009009",
        "email": None,                              # ← 测试点: 缺邮箱
        "target": "UI 设计转前端",
        "skills": ["HTML", "CSS", "JavaScript", "Figma", "Vue"],
        "works": [
            ("某设计公司", "UI 设计师", "2023.06 - 至今",
             "负责产品界面设计, 使用 Figma 输出设计稿, 自学前端参与页面实现"),
        ],
        "school": ("某职业技术学院", "数字媒体艺术", "2020.09 - 2023.06"),
    },
    {
        "file": "resume_10.pdf", "name": "冯梓涵", "gender": "男", "age": 30,
        "edu": "硕士", "exp": "3年以上",  # ← 测试点: 应归一为"3-5年"
        "city": "南京", "phone": "13000001010",
        "email": "fengzh@example.com", "target": "大数据开发工程师",
        "skills": ["Spark", "Hadoop", "Hive", "Python", "Kafka"],
        "works": [
            ("某数据公司", "大数据开发工程师", "2022.02 - 至今",
             "负责离线数仓建设, Spark 任务开发, Hive 数据建模, Kafka 实时数据接入"),
            ("某互联网公司", "数据开发工程师", "2021.07 - 2022.01",
             "参与用户行为日志采集和处理流程开发"),
        ],
        "school": ("某航空航天大学", "计算机技术(硕士)", "2018.09 - 2021.06"),
    },
]


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("T", fontName=TITLE, fontSize=20, leading=26, spaceAfter=4))
    s.add(ParagraphStyle("S", fontName=TITLE, fontSize=12.5, leading=18,
                         textColor=colors.HexColor("#1a1a1a"), spaceBefore=9, spaceAfter=3))
    s.add(ParagraphStyle("B", fontName=BODY, fontSize=10.5, leading=17,
                         textColor=colors.HexColor("#333333")))
    s.add(ParagraphStyle("I", fontName=TITLE, fontSize=10.5, leading=15))
    return s


def build_one(r: dict) -> None:
    doc = SimpleDocTemplate(
        str(OUT_DIR / r["file"]), pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=15*mm, bottomMargin=15*mm,
    )
    st = _styles()
    story = [Paragraph(r["name"], st["T"])]

    # 基本信息行(缺的字段自动跳过 → 测容错)
    base = [r["gender"], f"{r['age']}岁", f"{r['exp']}经验", r["edu"]]
    contacts = [f"电话: {r['phone']}"]
    if r.get("email"):
        contacts.append(f"邮箱: {r['email']}")
    if r.get("city"):
        contacts.append(f"城市: {r['city']}")
    t = Table([[Paragraph(" | ".join(base), st["B"]),
                Paragraph("  ".join(contacts), st["B"])]], colWidths=[80*mm, 95*mm])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [t, Spacer(1, 3*mm),
              Paragraph(f"求职意向: {r['target']}", st["B"])]

    # 技能
    story += [Spacer(1, 3*mm), Paragraph("专业技能", st["S"])]
    story.append(Paragraph("・" + " / ".join(r["skills"]), st["B"]))

    # 工作经历(应届则用校园经历)
    story += [Spacer(1, 3*mm), Paragraph("工作经历" if r["works"] else "项目经历", st["S"])]
    if r["works"]:
        for company, title, period, desc in r["works"]:
            story += [
                Paragraph(f"{company} | {title} | {period}", st["I"]),
                Paragraph(desc, st["B"]), Spacer(1, 2.5*mm),
            ]
    else:
        story.append(Paragraph(r.get("campus", ""), st["B"]))

    # 教育
    school, major, period = r["school"]
    story += [Spacer(1, 3*mm), Paragraph("教育经历", st["S"]),
              Paragraph(f"{school} | {major} | {period}", st["I"])]

    doc.build(story)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for r in RESUMES:
        build_one(r)
        print(f"  ✅ {r['file']}  {r['name']}({r['edu']}/{r['exp']}) - {r['target']}")
    print(f"\n完成: {OUT_DIR.resolve()}")
    print("测试点: 03统招本科 / 05经验8年 / 06应届无工作 / 07技能别名Python3 / 09缺城市邮箱 / 10经验3年以上")


if __name__ == "__main__":
    main()
