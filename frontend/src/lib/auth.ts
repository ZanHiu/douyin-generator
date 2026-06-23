import { computed, reactive } from 'vue'
import { getCurrentSession, login, logout } from './api'
import type { AuthUser, LoginRequest } from './types'

const state = reactive<{
  initialized: boolean
  loading: boolean
  user: AuthUser | null
}>({
  initialized: false,
  loading: false,
  user: null
})

let initializePromise: Promise<AuthUser | null> | null = null

async function initialize(force = false) {
  if (state.initialized && !force) {
    return state.user
  }

  if (initializePromise) {
    return initializePromise
  }

  state.loading = true
  initializePromise = getCurrentSession()
    .then((session) => {
      state.user = session.user
      state.initialized = true
      return state.user
    })
    .catch(() => {
      state.user = null
      state.initialized = true
      return null
    })
    .finally(() => {
      state.loading = false
      initializePromise = null
    })

  return initializePromise
}

async function signIn(payload: LoginRequest) {
  state.loading = true
  try {
    const session = await login(payload)
    state.user = session.user
    state.initialized = true
    initializePromise = null
    return session.user
  } finally {
    state.loading = false
  }
}

async function signOut() {
  state.loading = true
  try {
    await logout()
    state.user = null
    state.initialized = true
    initializePromise = null
  } finally {
    state.loading = false
  }
}

export function useAuth() {
  return {
    state,
    user: computed(() => state.user),
    isAuthenticated: computed(() => !!state.user),
    initialize,
    signIn,
    signOut
  }
}
