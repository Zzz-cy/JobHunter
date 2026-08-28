import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', requiresAuth: false }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: { title: '首页', requiresAuth: false }
      },
      {
        path: 'jobs',
        name: 'JobList',
        component: () => import('@/views/jobs/JobList.vue'),
        meta: { title: '职位列表', requiresAuth: false }
      },
      {
        path: 'jobs/:id',
        name: 'JobDetail',
        component: () => import('@/views/jobs/JobDetail.vue'),
        meta: { title: '职位详情', requiresAuth: false }
      },
      {
        path: 'recommend',
        name: 'Recommend',
        component: () => import('@/views/ChatView.vue'),
        meta: { title: 'AI 求职顾问', requiresAuth: true }
      },
      {
        // 岗位推荐(简历→岗位匹配): 技能召回+向量召回+LLM重排
        // 注意路径用 /job-recommend, 因为 /recommend 已被 AI 求职顾问(ChatView)占用
        path: 'job-recommend',
        name: 'JobRecommend',
        component: () => import('@/views/RecommendView.vue'),
        meta: { title: '岗位推荐', requiresAuth: true }
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('@/views/AdminView.vue'),
        meta: { title: 'Agent 监控后台', requiresAuth: true, requireAdmin: true }
      },
      {
        path: 'resume',
        name: 'ResumeManage',
        component: () => import('@/views/ResumeManage.vue'),
        meta: { title: '我的简历', requiresAuth: true }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '数据分析', requiresAuth: false }
      },
      {
        // 岗位知识图谱(Neo4j): 方向画像 + 力导向图可视化
        path: 'knowledge-graph',
        name: 'KnowledgeGraph',
        component: () => import('@/views/KnowledgeGraph.vue'),
        meta: { title: '知识图谱', requiresAuth: false }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: { title: '个人中心', requiresAuth: true }
      },
      {
        path: 'data-admin',
        name: 'DataAdmin',
        component: () => import('@/views/DataAdmin.vue'),
        meta: { title: '数据管理', requiresAuth: true, requireAdmin: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

// 全局前置守卫:页面标题 + 登录态校验 + 管理员权限校验
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - JobHunter` : 'JobHunter'

  const userStore = useUserStore()
  const isLoggedIn = userStore.isLoggedIn

  // 1. 需要登录但未登录 → 跳登录页
  if (to.meta.requiresAuth && !isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  // 2. 需要管理员权限但不是管理员 → 跳首页(防止直接输 URL 访问)
  if (to.meta.requireAdmin && !userStore.isAdmin) {
    next({ name: 'Home' })
    return
  }
  next()
})

export default router
