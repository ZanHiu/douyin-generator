<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getMySettings, saveMySettings } from '../lib/api'
import type { UserSettings } from '../lib/types'
import { voiceOptions } from '../lib/voices'

const defaultSettings: UserSettings = {
  default_voice_id: 'banmai',
  default_burn_subtitle: true,
  default_mix_original_audio: false,
  default_voice_volume_percent: 100,
  default_original_volume_percent: 35,
  default_subtitle_font_size: 18,
  default_subtitle_position: 'bottom',
  default_subtitle_text_color: '#FFFFFF'
}

const form = ref<UserSettings>({ ...defaultSettings })
const initialSettings = ref<UserSettings>({ ...defaultSettings })
const isVoiceMenuOpen = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const isDirty = computed(
  () => JSON.stringify(form.value) !== JSON.stringify(initialSettings.value)
)

function selectedVoice() {
  return voiceOptions.find((voice) => voice.id === form.value.default_voice_id) || voiceOptions[0]
}

function selectVoice(nextVoiceId: string) {
  form.value.default_voice_id = nextVoiceId
  isVoiceMenuOpen.value = false
}

async function loadSettings() {
  try {
    const response = await getMySettings()
    form.value = { ...response.settings }
    initialSettings.value = { ...response.settings }
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not load settings.'
  }
}

function resetDefaults() {
  form.value = { ...defaultSettings }
  successMessage.value = ''
  errorMessage.value = ''
}

async function submit() {
  if (!isDirty.value) {
    return
  }

  isSubmitting.value = true
  successMessage.value = ''
  try {
    const response = await saveMySettings(form.value)
    form.value = { ...response.settings }
    initialSettings.value = { ...response.settings }
    errorMessage.value = ''
    successMessage.value = 'Settings saved. New jobs will use these defaults.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not save settings.'
  } finally {
    isSubmitting.value = false
  }
}

watch(
  form,
  () => {
    if (successMessage.value && isDirty.value) {
      successMessage.value = ''
    }
  },
  { deep: true }
)

onMounted(loadSettings)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">Settings</p>
        <h1>Operator defaults</h1>
        <p>
          Save the defaults used to prefill Generate and to snapshot new editor baselines.
        </p>
      </div>
    </div>

    <form class="surface form-panel settings-form" @submit.prevent="submit">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Generate</p>
          <h2>New job defaults</h2>
        </div>
        <div class="settings-actions">
          <button class="secondary-button compact-button" type="button" @click="resetDefaults">
            Reset
          </button>
          <button
            class="primary-button compact-button"
            type="submit"
            :disabled="isSubmitting || !isDirty"
          >
            {{ isSubmitting ? 'Saving...' : 'Save settings' }}
          </button>
        </div>
      </div>

      <div class="settings-grid">
        <div class="field">
          <span>Default voice</span>
          <div class="voice-select">
            <button
              class="voice-trigger"
              type="button"
              :aria-expanded="isVoiceMenuOpen"
              aria-haspopup="listbox"
              @click="isVoiceMenuOpen = !isVoiceMenuOpen"
            >
              <span>
                <strong>{{ selectedVoice().name }}</strong>
                <small>{{ selectedVoice().meta }}</small>
              </span>
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M7 9.5 12 14.5 17 9.5H7Z" />
              </svg>
            </button>

            <div v-if="isVoiceMenuOpen" class="voice-menu" role="listbox">
              <button
                v-for="voice in voiceOptions"
                :key="voice.id"
                :class="['voice-option', { 'voice-option-selected': voice.id === form.default_voice_id }]"
                type="button"
                role="option"
                :aria-selected="voice.id === form.default_voice_id"
                @click="selectVoice(voice.id)"
              >
                <span>
                  <strong>{{ voice.name }}</strong>
                  <small>{{ voice.meta }}</small>
                </span>
                <span v-if="voice.id === form.default_voice_id" class="voice-check">Selected</span>
              </button>
            </div>
          </div>
        </div>

        <label class="field">
          <span>Voice volume</span>
          <input v-model.number="form.default_voice_volume_percent" type="number" min="0" max="200" />
        </label>

        <label class="field">
          <span>Original volume</span>
          <input
            v-model.number="form.default_original_volume_percent"
            type="number"
            min="0"
            max="200"
          />
        </label>
      </div>

      <div class="option-grid">
        <label class="check-row">
          <input v-model="form.default_burn_subtitle" type="checkbox" />
          <span>
            <strong>Burn subtitles by default</strong>
            <small>Prefill new jobs to render Vietnamese captions into the final video.</small>
          </span>
        </label>

        <label class="check-row">
          <input v-model="form.default_mix_original_audio" type="checkbox" />
          <span>
            <strong>Mix original audio by default</strong>
            <small>Prefill new jobs to keep source audio quietly under the Vietnamese voice.</small>
          </span>
        </label>
      </div>

      <div class="section-heading">
        <div>
          <p class="eyebrow">Rendering</p>
          <h2>Editor baseline defaults</h2>
        </div>
      </div>

      <div class="settings-grid settings-grid-wide">
        <label class="field">
          <span>Subtitle font size</span>
          <input v-model.number="form.default_subtitle_font_size" type="number" min="14" max="48" />
        </label>

        <label class="field">
          <span>Subtitle position</span>
          <div class="select-field">
            <span>Position</span>
            <select v-model="form.default_subtitle_position">
              <option value="bottom">Bottom</option>
              <option value="lower_third">Lower third</option>
              <option value="top">Top</option>
            </select>
          </div>
        </label>

        <label class="field">
          <span>Subtitle text color</span>
          <div class="settings-color-field">
            <strong>{{ form.default_subtitle_text_color }}</strong>
            <input v-model="form.default_subtitle_text_color" type="color" />
          </div>
        </label>
      </div>

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-if="successMessage" class="success-message">{{ successMessage }}</p>
    </form>
  </section>
</template>
