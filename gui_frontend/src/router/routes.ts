import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/scanner',
  },
  { path: '/scanner', component: () => import('@/pages/ScannerPage.vue') },
  { path: '/calculator', component: () => import('@/pages/CalculatorPage.vue') },
  { path: '/history', component: () => import('@/pages/HistoryPage.vue') },
  { path: '/settings', component: () => import('@/pages/SettingsPage.vue') },
  {
    path: '/:catchAll(.*)*',
    component: () => import('@/pages/ErrorNotFound.vue'),
  },
]

export default routes
