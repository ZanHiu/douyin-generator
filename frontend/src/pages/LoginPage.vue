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
    <div class="login-orb login-orb-left" aria-hidden="true"></div>
    <div class="login-orb login-orb-right" aria-hidden="true"></div>

    <div class="login-shell">
      <section class="login-stage">
        <div class="login-brand">
          <span class="brand-mark">DG</span>
          <div>
            <strong>DouyinGenerator</strong>
            <small>Operator workspace</small>
          </div>
        </div>

        <div class="login-panel">
          <section class="surface login-card">
            <div class="section-heading login-card-heading">
              <div class="login-card-copy">
                <p class="eyebrow">Secure login</p>
                <h1>Sign in to continue work.</h1>
                <p>Access dubbing jobs, editor handoff, and rendering defaults from one workspace.</p>
              </div>
              <span class="login-card-icon" aria-hidden="true">
                <LockKeyhole :size="18" :stroke-width="2.2" />
              </span>
            </div>

            <form class="form-panel" @submit.prevent="submit">
              <label class="field">
                <span>Email</span>
                <input
                  v-model="email"
                  type="email"
                  autocomplete="email"
                  placeholder="admin@example.com"
                />
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
                    <EyeOff
                      v-if="isPasswordVisible"
                      :size="18"
                      :stroke-width="2.2"
                      aria-hidden="true"
                    />
                    <Eye v-else :size="18" :stroke-width="2.2" aria-hidden="true" />
                    <span>{{ isPasswordVisible ? 'Hide' : 'Show' }}</span>
                  </button>
                </div>
              </label>

              <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

              <button class="primary-button login-submit icon-button" type="submit" :disabled="isSubmitting">
                <LogIn :size="16" :stroke-width="2.2" aria-hidden="true" />
                <span>{{ isSubmitting ? 'Signing in...' : 'Sign in' }}</span>
              </button>
            </form>
          </section>

          <aside class="login-context">
            <article class="login-context-card">
              <span class="login-context-icon" aria-hidden="true">
                <ShieldCheck :size="18" :stroke-width="2.2" />
              </span>
              <div>
                <strong>Restricted access</strong>
                <p>Only approved operator accounts can open the production workspace.</p>
              </div>
            </article>

            <article class="login-context-card">
              <span class="login-context-icon" aria-hidden="true">
                <Workflow :size="18" :stroke-width="2.2" />
              </span>
              <div>
                <strong>Active workflow</strong>
                <p>Track jobs, continue editor revisions, and keep delivery settings aligned.</p>
              </div>
            </article>

            <article class="login-context-card login-context-card-accent">
              <span class="login-context-icon" aria-hidden="true">
                <Sparkles :size="18" :stroke-width="2.2" />
              </span>
              <div>
                <strong>Focused entry point</strong>
                <p>A cleaner authentication view built to prioritize the form instead of the hero.</p>
              </div>
            </article>
          </aside>
        </div>
      </section>
    </div>
  </section>
</template>
