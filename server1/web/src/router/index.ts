import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/modules/auth/api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '工作台' },
        },
        {
          path: 'circulation',
          name: 'circulation',
          component: () => import('@/modules/circulation/CirculationView.vue'),
          meta: { title: '流转控制' },
        },
        {
          path: 'files',
          name: 'files',
          component: () => import('@/views/FilesView.vue'),
          meta: { title: '文件管理' },
        },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('@/views/ProjectsView.vue'),
          meta: { title: '项目管理' },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/TasksView.vue'),
          meta: { title: '任务管理' },
        },
        {
          path: 'audit',
          name: 'audit',
          component: () => import('@/modules/audit/AuditView.vue'),
          meta: { title: '审计追溯' },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!getToken()) return { name: 'login', query: { redirect: to.fullPath } }
  return true
})

export default router
