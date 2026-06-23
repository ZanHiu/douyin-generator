<script setup lang="ts">
import { LockKeyhole, LogIn } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../lib/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const email = ref('')
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

async function submit() {
  errorMessage.value = ''
  if (!email.value.trim() || !password.value) {
    errorMessage.value = 'Enter your email and password.'
    return
  }

  isSubmitting.value = true
  try {
    await auth.signIn({
      email: email.value.trim(),
      password: password.value
    })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not sign in.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="login-page">
    <div class="login-shell">
      <section class="login-hero">
        <div class="login-brand">
          <span class="brand-mark">DG</span>
          <div>
            <strong>DouyinGenerator</strong>
            <small>Private production workspace</small>
          </div>
        </div>

        <div class="login-copy">
          <p class="eyebrow">Protected access</p>
          <h1>Sign in to manage dubbing jobs and edited versions.</h1>
          <p>
            This environment is restricted to seeded operator accounts before public rollout.
          </p>
        </div>
      </section>

      <section class="surface login-card">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Login</p>
            <h2>Operator access</h2>
          </div>
          <span class="login-card-icon" aria-hidden="true">
            <LockKeyhole :size="18" :stroke-width="2.2" />
          </span>
        </div>

        <form class="form-panel" @submit.prevent="submit">
          <label class="field">
            <span>Email</span>
            <input v-model="email" type="email" autocomplete="email" placeholder="admin@example.com" />
          </label>

          <label class="field">
            <span>Password</span>
            <input v-model="password" type="password" autocomplete="current-password" placeholder="••••••••" />
          </label>

          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

          <button class="primary-button icon-button" type="submit" :disabled="isSubmitting">
            <LogIn :size="16" :stroke-width="2.2" aria-hidden="true" />
            <span>{{ isSubmitting ? 'Signing in...' : 'Sign in' }}</span>
          </button>
        </form>
      </section>
    </div>
  </section>
</template>
