import runpy
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def main():
    print("=" * 50)
    print("开始初始化 Neo4j 就业知识图谱")
    print("=" * 50)

    print("\n[1/3] 导入基础岗位知识图谱...")
    runpy.run_module(
        "scripts.init_neo4j_jobs",
        run_name="__main__",
    )

    print("\n[2/3] 建立就业分析知识图谱...")
    runpy.run_module(
        "scripts.init_neo4j_analysis",
        run_name="__main__",
    )

    print("\n[3/3] 补充方向-核心技能关系...")
    # 子进程隔离: 该脚本要连 MySQL, 一键同步时在后端进程内 runpy 拉起
    # 会撞上后端已占用的事件循环(Future attached to a different loop),
    # 与向量库构建同套路, 丢给子进程完全隔离
    result = subprocess.run(
        [sys.executable, "-m", "scripts.init_neo4j_skills"],
        cwd=str(ROOT_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError("init_neo4j_skills 执行失败, 详见上方输出")

    print("\n" + "=" * 50)
    print("Neo4j 知识图谱初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
