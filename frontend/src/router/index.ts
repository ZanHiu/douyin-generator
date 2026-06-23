import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'
import { useAuth } from '../lib/auth'
import HomePage from '../pages/HomePage.vue'
import EditorJobPage from '../pages/EditorJobPage.vue'
import EditorLandingPage from '../pages/EditorLandingPage.vue'
import JobPage from '../pages/JobPage.vue'
import JobsPage from '../pages/JobsPage.vue'
import LoginPage from '../pages/LoginPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginPage,
      meta: {
        guestOnly: true
      }
    },
    {
      path: '/',
      component: AppLayout,
      meta: {
        requiresAuth: true
      },
      children: [
        { path: '', name: 'home', component: HomePage },
        {
          path: 'jobs',
          name: 'jobs',
          component: JobsPage
        },
        { path: 'jobs/:jobId', name: 'job', component: JobPage },
        {
          path: 'editor',
          name: 'editor',
          component: EditorLandingPage
        },
        { path: 'editor/:jobId', name: 'editor-job', component: EditorJobPage },
        {
          path: 'settings',
          name: 'settings',
          component: SettingsPage
        }
      ]
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  await auth.initialize()

  if (to.meta.requiresAuth && !auth.isAuthenticated.value) {
    return {
      name: 'login',
      query: {
        redirect: to.fullPath
      }
    }
  }

  if (to.meta.guestOnly && auth.isAuthenticated.value) {
    return { name: 'home' }
  }

  return true
})
