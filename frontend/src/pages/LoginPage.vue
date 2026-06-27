<script setup lang="ts">
import { Eye, EyeOff, LockKeyhole, LogIn, ShieldCheck, Sparkles, Workflow } from 'lucide-vue-next'
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
const isPasswordVisible = ref(false)

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
          <h1>Operator workspace for dubbing, job tracking, and final edit control.</h1>
          <p>
            A tighter sign-in flow with clearer hierarchy, trust signals, and workspace context for
            internal production use.
          </p>
        </div>

        <div class="login-highlights">
          <article class="login-highlight-card">
            <span class="login-highlight-icon" aria-hidden="true">
              <ShieldCheck :size="18" :stroke-width="2.2" />
            </span>
            <div>
              <strong>Restricted access</strong>
              <p>Only approved operator accounts can manage dubbing jobs and edited outputs.</p>
            </div>
          </article>

          <article class="login-highlight-card">
            <span class="login-highlight-icon" aria-hidden="true">
              <Workflow :size="18" :stroke-width="2.2" />
            </span>
            <div>
              <strong>Production workflow</strong>
              <p>Review queue status, continue edits, and keep rendering defaults consistent.</p>
            </div>
          </article>

          <article class="login-highlight-card">
            <span class="login-highlight-icon" aria-hidden="true">
              <Sparkles :size="18" :stroke-width="2.2" />
            </span>
            <div>
              <strong>Focused interface</strong>
              <p>Cleaner split layout, stronger emphasis, and faster scanning on desktop and mobile.</p>
            </div>
          </article>
        </div>
      </section>

      <section class="surface login-card">
        <div class="section-heading login-card-heading">
          <div class="login-card-copy">
            <p class="eyebrow">Login</p>
            <h2>Welcome back</h2>
            <p>Sign in with your operator account to continue.</p>
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
            <div class="password-field">
              <input
                v-model="password"
                :type="isPasswordVisible ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="********"
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="isPasswordVisible ? 'Hide password' : 'Show password'"
                :aria-pressed="isPasswordVisible"
                @click="isPasswordVisible = !isPasswordVisible"
              >
                <EyeOff v-if="isPasswordVisible" :size="18" :stroke-width="2.2" aria-hidden="true" />
                <Eye v-else :size="18" :stroke-width="2.2" aria-hidden="true" />
                <span>{{ isPasswordVisible ? 'Hide' : 'Show' }}</span>
              </button>
            </div>
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
