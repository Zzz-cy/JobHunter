# JobHunter Frontend

智能求职推荐平台前端,基于 Vue 3 + Vite + Pinia + Element Plus。

## 技术栈

| 类别 | 选型 |
|---|---|
| 框架 | Vue 3 (Composition API) |
| 构建 | Vite 5 |
| 状态管理 | Pinia |
| UI 组件 | Element Plus (中文本地化) |
| 图表 | ECharts 5 |
| 路由 | Vue Router 4 |
| HTTP | axios |
| 自动按需引入 | unplugin-auto-import / unplugin-vue-components |

## 项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── jsconfig.json
└── src/
    ├── main.js                  # 入口
    ├── App.vue                  # 根组件
    ├── assets/
    │   └── main.css             # 全局样式
    ├── router/
    │   └── index.js             # 路由配置 + 守卫
    ├── stores/
    │   ├── user.js              # 用户登录态
    │   ├── job.js               # 职位查询/收藏
    │   └── resume.js            # 简历上传/解析
    ├── utils/
    │   └── request.js           # axios 实例 + 拦截器
    ├── layouts/
    │   └── MainLayout.vue       # 顶部导航 + 主体 + 底部
    ├── components/
    │   ├── layout/
    │   │   ├── AppHeader.vue
    │   │   └── AppFooter.vue
    │   └── common/
    │       ├── JobCard.vue      # 职位卡片
    │       └── SkillTag.vue     # 技能标签
    └── views/
        ├── Home.vue             # 首页(搜索 + 热门)
        ├── Login.vue
        ├── Register.vue
        ├── Profile.vue          # 个人中心(求职进度看板)
        ├── Recommend.vue        # 智能推荐
        ├── ResumeManage.vue     # 简历上传/解析
        ├── Dashboard.vue        # 数据可视化大盘
        ├── NotFound.vue         # 404
        └── jobs/
            ├── JobList.vue      # 职位列表
            └── JobDetail.vue    # 职位详情
```

## 启动开发

```bash
cd frontend
npm install           # 或 pnpm install
npm run dev           # 启动开发服务器(默认 http://localhost:5173)
npm run build         # 构建生产版本
```

## 后端联调说明

前端已配置 Vite 代理,所有 `/api` 开头的请求会转发到 `http://127.0.0.1:8000`:
- `vite.config.js` 中的 `server.proxy` 配置
- 修改后端端口需同步更新此处

所有需要后端接口的位置都标记了 `// TODO:` 注释,主要分布在:
- `src/stores/*.js` — 业务 action 实现
- `src/utils/request.js` — 拦截器响应格式适配
- `src/views/*.vue` — 各页面 onMounted 数据加载

## 页面清单

| 路由 | 页面 | 说明 | 需登录 |
|---|---|---|---|
| `/home` | 首页 | Hero 搜索 + 热门 + 平台特色 | 否 |
| `/jobs` | 职位列表 | 多维度筛选 + 分页 + 侧栏 | 否 |
| `/jobs/:id` | 职位详情 | JD + 公司 + 跳转外站投递 | 否 |
| `/recommend` | 智能推荐 | 简历选择 + 匹配度评分 + 推荐理由 | 是 |
| `/resume` | 简历管理 | 上传 + 解析进度 + 技能档案 | 是 |
| `/dashboard` | 数据分析 | 8 张 ECharts 图表 | 否 |
| `/profile` | 个人中心 | 求职进度看板 + 收藏 + 设置 | 是 |
| `/login` `/register` | 登录注册 | 短信验证码注册 | 否 |

## 产品定位

- ✅ **信息聚合**:从 Boss/猎聘/官网采集招聘信息
- ✅ **AI 推荐**:基于简历技能档案的智能匹配
- ✅ **跳转投递**:不代投,引导用户去原网站完成应聘
- ❌ **不提供**:站内直接投递、HR 沟通、在线签约
