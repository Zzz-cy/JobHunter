import runpy


def main():
    print("=" * 50)
    print("开始初始化 Neo4j 就业知识图谱")
    print("=" * 50)

    print("\n[1/2] 导入基础岗位知识图谱...")
    runpy.run_module(
        "scripts.init_neo4j_jobs",
        run_name="__main__",
    )

    print("\n[2/2] 建立就业分析知识图谱...")
    runpy.run_module(
        "scripts.init_neo4j_analysis",
        run_name="__main__",
    )

    print("\n" + "=" * 50)
    print("Neo4j 知识图谱初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()