# JobHunter 一键部署（Docker）

> 给跑不起环境的队友：**只需要装 Docker Desktop**，Python/Node/MySQL/ES/Neo4j 全都不用装。

## 1. 装 Docker

- Windows/Mac：装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（装完启动它）
  - Windows 注意：Settings → Resources 内存给到 **6GB** 以上（ES+Neo4j+MySQL 是内存大户）
- Linux：`sudo apt install -y docker.io docker-compose-v2`

## 2. 拿到两个不进 git 的东西

找开发者要，放到项目根目录：

```
.env              # 智谱/DeepSeek key、MySQL/Neo4j 密码
db/data/*.json    # 岗位爬虫数据(演示导入用)
```

## 3. 一键启动

```bash
docker compose up -d --build     # 首次构建约 5~10 分钟
docker compose ps                # 看 6 个容器都 Up 了没
```

## 4. 初始化数据（四库一条链路）

```bash
curl -X POST http://localhost/crawl/bootstrap
# Windows 没有 curl 就跳过这句, 改用浏览器:
# 打开 http://localhost → 登录管理员 → 数据管理页 → 点「一键同步所有库」
```

完成后打开 `http://localhost`（云服务器就是 `http://服务器IP`），用种子账号登录（见 `docs/TEST_ACCOUNTS.md`，密码 123456）。

## 常用命令

```bash
docker compose logs -f backend      # 看主后端日志
docker compose logs -f llm          # 看简历解析服务日志
docker compose down                 # 停止(数据保留在卷里)
docker compose down -v              # 停止并清空所有数据(重置演示)
```

## 上云服务器

文件原样传上去（git clone + scp 上面第 2 步的两个东西），安全组/防火墙只开 **80 端口**。

## 排错速查

| 现象 | 原因 |
|---|---|
| build 拉镜像超时 | 国内网络问题：Docker Desktop → Settings → Docker Engine 加 `"registry-mirrors": ["https://docker.1ms.run"]` |
| ES 容器一直重启 | 内存不够：Settings → Resources 内存加大；或 compose 里 ES_JAVA_OPTS 改 `-Xms256m -Xmx256m` |
| 图谱页转圈 | Neo4j 没起来没关系，页面会降级为演示数据；内存实在不够可把 compose 里 neo4j 整段注释掉 |
| 前端刷新 404 | nginx.conf 的 try_files 回退已处理，正常不应出现 |
