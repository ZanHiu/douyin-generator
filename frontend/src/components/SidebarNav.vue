<script setup lang="ts">
import {
  ChevronUp,
  Clapperboard,
  LogOut,
  ListChecks,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  UserCircle2,
  WandSparkles
} from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../lib/auth'

const isCollapsed = ref(false)
const isAccountMenuOpen = ref(false)
const sidebarSessionRef = ref<HTMLElement | null>(null)
const router = useRouter()
const auth = useAuth()
const currentUserLabel = computed(() => auth.user.value?.email || 'Signed in')
const currentUserDisplayName = computed(() => {
  const email = auth.user.value?.email?.trim() || ''
  if (!email) return 'Signed in'
  return email.split('@')[0] || email
})
const currentUserInitials = computed(() => {
  const email = auth.user.value?.email?.trim() || ''
  if (!email) return 'DG'
  const localPart = email.split('@')[0] || email
  const tokens = localPart
    .split(/[._-]+/)
    .map((token) => token.trim())
    .filter(Boolean)

  if (tokens.length >= 2) {
    return `${tokens[0][0] || ''}${tokens[1][0] || ''}`.toUpperCase()
  }

  return localPart.slice(0, 2).toUpperCase()
})

const navItems = [
  {
    to: '/',
    label: 'Generate',
    icon: WandSparkles
  },
  {
    to: '/jobs',
    label: 'Jobs',
    icon: ListChecks
  },
  {
    to: '/editor',
    label: 'Editor',
    icon: Clapperboard
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: Settings
  }
]

async function handleLogout() {
  isAccountMenuOpen.value = false
  await auth.signOut()
  await router.replace('/login')
}

async function handleOpenAccount() {
  isAccountMenuOpen.value = false
  await router.push({ name: 'settings', query: { section: 'account' } })
}

async function handleOpenSettings() {
  isAccountMenuOpen.value = false
  await router.push({ name: 'settings' })
}

function toggleAccountMenu() {
  isAccountMenuOpen.value = !isAccountMenuOpen.value
}

function closeAccountMenu() {
  isAccountMenuOpen.value = false
}

function handleDocumentPointerDown(event: MouseEvent) {
  if (!isAccountMenuOpen.value) return
  const target = event.target
  if (!(target instanceof Node)) return
  if (sidebarSessionRef.value?.contains(target)) return
  closeAccountMenu()
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeAccountMenu()
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleDocumentPointerDown)
  document.addEventListener('keydown', handleDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocumentPointerDown)
  document.removeEventListener('keydown', handleDocumentKeydown)
})
</script>

<template>
  <aside :class="['sidebar', { 'sidebar-collapsed': isCollapsed }]">
    <RouterLink class="brand" to="/">
      <span class="brand-mark">DG</span>
      <span class="brand-copy">
        <strong>DouyinGenerator</strong>
        <small>Video localization</small>
      </span>
    </RouterLink>

    <nav class="sidebar-nav" aria-label="Primary navigation">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        class="nav-item"
        :to="item.to"
        :aria-label="item.label"
        :title="item.label"
      >
        <span class="nav-icon" aria-hidden="true">
          <component :is="item.icon" :size="18" :stroke-width="2" />
        </span>
        <span class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <button
        class="sidebar-toggle"
        type="button"
        :aria-label="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="isCollapsed = !isCollapsed"
      >
        <PanelLeftOpen v-if="isCollapsed" :size="20" :stroke-width="2" aria-hidden="true" />
        <PanelLeftClose v-else :size="18" :stroke-width="2" aria-hidden="true" />
        <span>{{ isCollapsed ? 'Expand' : 'Collapse' }}</span>
      </button>

      <div ref="sidebarSessionRef" class="sidebar-session">
        <button
          class="sidebar-session-trigger"
          type="button"
          :title="currentUserLabel"
          :aria-expanded="isAccountMenuOpen"
          aria-haspopup="menu"
          @click="toggleAccountMenu"
        >
          <span class="sidebar-session-avatar" aria-hidden="true">{{ currentUserInitials }}</span>
          <div class="sidebar-session-copy">
            <strong>{{ currentUserDisplayName }}</strong>
            <small>Private operator</small>
          </div>
          <ChevronUp
            class="sidebar-session-chevron"
            :class="{ 'sidebar-session-chevron-open': isAccountMenuOpen }"
            :size="16"
            :stroke-width="2.2"
            aria-hidden="true"
          />
        </button>
        <div v-if="isAccountMenuOpen" class="sidebar-session-popover" role="menu">
          <div class="sidebar-session-menu">
            <div class="sidebar-session-menu-group" role="group" aria-label="Workspace">
              <p class="sidebar-session-menu-heading">Workspace</p>
              <button class="sidebar-session-popover-button" type="button" @click="handleOpenAccount">
                <UserCircle2 :size="16" :stroke-width="2.1" aria-hidden="true" />
                <span>Account</span>
              </button>
              <button class="sidebar-session-popover-button" type="button" @click="handleOpenSettings">
                <Settings :size="16" :stroke-width="2.1" aria-hidden="true" />
                <span>Settings</span>
              </button>
            </div>

            <div class="sidebar-session-menu-divider" aria-hidden="true" />

            <div class="sidebar-session-menu-group" role="group" aria-label="Session">
              <p class="sidebar-session-menu-heading">Session</p>
              <button class="sidebar-session-popover-button sidebar-session-popover-button-danger" type="button" @click="handleLogout">
                <LogOut :size="16" :stroke-width="2.1" aria-hidden="true" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>
