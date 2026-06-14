import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

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
        component: () => import('@/views/Recommend.vue'),
        meta: { title: '智能推荐', requiresAuth: true }
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
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: { title: '个人中心', requiresAuth: true }
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

// 全局前置守卫:页面标题 + 登录态校验
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - JobHunter` : 'JobHunter'

  // TODO: 从 user store 读取登录态
  // const userStore = useUserStore()
  // const isLoggedIn = userStore.isLoggedIn
  const isLoggedIn = false // 占位:未接入登录逻辑前默认未登录

  if (to.meta.requiresAuth && !isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
