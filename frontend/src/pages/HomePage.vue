<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useRouter } from 'vue-router'
import { createJob, createUploadedJob, getMySettings, listJobs } from '../lib/api'
import type { JobListItem } from '../lib/types'
import { voiceOptions } from '../lib/voices'

const router = useRouter()

const sourceMode = ref<'url' | 'upload'>('url')
const sourceUrl = ref('')
const sourceFile = ref<File | null>(null)
const isDraggingFile = ref(false)
const voiceId = ref('banmai')
const isVoiceMenuOpen = ref(false)
const burnSubtitle = ref(true)
const mixOriginalAudio = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const recentJobs = ref<JobListItem[]>([])
const jobsErrorMessage = ref('')
const defaultsErrorMessage = ref('')

function formatDate(value: string | null) {
  if (!value) return ''
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'short',
    timeStyle: 'medium'
  }).format(new Date(value))
}

function shortJobId(jobId: string) {
  return jobId.slice(0, 8)
}

function selectedVoice() {
  return voiceOptions.find((voice) => voice.id === voiceId.value) || voiceOptions[0]
}

function selectVoice(nextVoiceId: string) {
  voiceId.value = nextVoiceId
  isVoiceMenuOpen.value = false
}

async function loadRecentJobs() {
  try {
    recentJobs.value = await listJobs(10)
    jobsErrorMessage.value = ''
  } catch (error) {
    jobsErrorMessage.value = error instanceof Error ? error.message : 'Could not load recent jobs.'
  }
}

async function loadDefaults() {
  try {
    const response = await getMySettings()
    voiceId.value = response.settings.default_voice_id
    burnSubtitle.value = response.settings.default_burn_subtitle
    mixOriginalAudio.value = response.settings.default_mix_original_audio
    defaultsErrorMessage.value = ''
  } catch (error) {
    defaultsErrorMessage.value =
      error instanceof Error ? error.message : 'Could not load saved defaults.'
  }
}

async function submitJob() {
  errorMessage.value = ''

  isSubmitting.value = true
  try {
    let job
    if (sourceMode.value === 'upload') {
      if (!sourceFile.value) {
        errorMessage.value = 'Choose a local video file.'
        return
      }
      job = await createUploadedJob({
        source_file: sourceFile.value,
        voice_id: voiceId.value,
        burn_subtitle: burnSubtitle.value,
        mix_original_audio: mixOriginalAudio.value
      })
    } else {
      if (!sourceUrl.value.trim()) {
        errorMessage.value = 'Enter a Douyin or TikTok URL.'
        return
      }
      job = await createJob({
        source_url: sourceUrl.value.trim(),
        voice_id: voiceId.value,
        burn_subtitle: burnSubtitle.value,
        mix_original_audio: mixOriginalAudio.value
      })
    }
    await loadRecentJobs()
    await router.push(`/jobs/${job.job_id}`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not create job.'
  } finally {
    isSubmitting.value = false
  }
}

function handleSourceFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  sourceFile.value = target.files?.[0] ?? null
}

function setSourceMode(mode: 'url' | 'upload') {
  sourceMode.value = mode
  errorMessage.value = ''
}

function handleFileDragOver(event: DragEvent) {
  event.preventDefault()
  isDraggingFile.value = true
}

function handleFileDragLeave(event: DragEvent) {
  event.preventDefault()
  isDraggingFile.value = false
}

function handleFileDrop(event: DragEvent) {
  event.preventDefault()
  isDraggingFile.value = false

  const file = event.dataTransfer?.files?.[0] ?? null
  if (file) {
    sourceFile.value = file
  }
}

onMounted(async () => {
  await Promise.all([loadDefaults(), loadRecentJobs()])
})
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">Generate</p>
        <h1>Vietnamese dubbing workspace</h1>
        <p>
          Create a processing job from a Douyin or TikTok link, then track each pipeline stage.
        </p>
      </div>
    </div>

    <div class="workspace-grid">
      <div class="detail-main">
        <form class="surface form-panel" @submit.prevent="submitJob">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Source</p>
              <h2>New video job</h2>
            </div>
          </div>

          <div class="source-mode-toggle" role="tablist" aria-label="Video source mode">
            <button
              :class="['source-mode-button', { 'source-mode-button-active': sourceMode === 'url' }]"
              type="button"
              role="tab"
              :aria-selected="sourceMode === 'url'"
              @click="setSourceMode('url')"
            >
              Link
            </button>
            <button
              :class="[
                'source-mode-button',
                { 'source-mode-button-active': sourceMode === 'upload' }
              ]"
              type="button"
              role="tab"
              :aria-selected="sourceMode === 'upload'"
              @click="setSourceMode('upload')"
            >
              Upload
            </button>
          </div>

          <p class="source-mode-description">
            {{
              sourceMode === 'url'
                ? 'Fetch from a Douyin or TikTok URL.'
                : 'Use a local MP4, MOV, MKV, or WebM file.'
            }}
          </p>

          <label v-if="sourceMode === 'url'" class="field">
            <span>Video URL</span>
            <input
              v-model="sourceUrl"
              type="url"
              placeholder="https://www.douyin.com/..."
              autocomplete="off"
            />
          </label>

          <label v-else class="field">
            <span>Video file</span>
            <input
              class="file-input-hidden"
              type="file"
              accept=".mp4,.mov,.mkv,.webm,video/mp4,video/quicktime,video/webm"
              @change="handleSourceFileChange"
            />
            <span
              :class="['upload-dropzone', { 'upload-dropzone-dragging': isDraggingFile }]"
              @dragover="handleFileDragOver"
              @dragleave="handleFileDragLeave"
              @drop="handleFileDrop"
            >
              <strong>{{ sourceFile ? sourceFile.name : 'Drop video here or click to browse' }}</strong>
              <small>
                {{
                  sourceFile
                    ? 'File selected for upload.'
                    : 'Accepts MP4, MOV, MKV, and WebM files.'
                }}
              </small>
            </span>
          </label>

          <div class="field">
            <span>Voice</span>
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
                  :class="['voice-option', { 'voice-option-selected': voice.id === voiceId }]"
                  type="button"
                  role="option"
                  :aria-selected="voice.id === voiceId"
                  @click="selectVoice(voice.id)"
                >
                  <span>
                    <strong>{{ voice.name }}</strong>
                    <small>{{ voice.meta }}</small>
                  </span>
                  <span v-if="voice.id === voiceId" class="voice-check">Selected</span>
                </button>
              </div>
            </div>
          </div>

          <p v-if="defaultsErrorMessage" class="error-message">{{ defaultsErrorMessage }}</p>

          <div class="option-grid">
            <label class="check-row">
              <input v-model="burnSubtitle" type="checkbox" />
              <span>
                <strong>Burn subtitles</strong>
                <small>Render captions into the final video.</small>
              </span>
            </label>

            <label class="check-row">
              <input v-model="mixOriginalAudio" type="checkbox" />
              <span>
                <strong>Mix original audio</strong>
                <small>Keep source audio quietly in the background.</small>
              </span>
            </label>
          </div>

          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

          <button class="primary-button" type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? 'Creating job...' : 'Generate video' }}
          </button>
        </form>
      </div>

      <aside class="side-stack">
        <section class="surface">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Recent</p>
              <h2>Latest jobs</h2>
            </div>
            <button class="secondary-button compact-button" type="button" @click="loadRecentJobs">
              Refresh
            </button>
          </div>

          <p v-if="jobsErrorMessage" class="error-message">{{ jobsErrorMessage }}</p>

          <div v-if="recentJobs.length" class="job-list compact-list">
            <RouterLink
              v-for="job in recentJobs.slice(0, 5)"
              :key="job.job_id"
              class="job-list-item"
              :to="`/jobs/${job.job_id}`"
            >
              <div>
                <span :class="['status-pill', `status-${job.status}`]">{{ job.status }}</span>
                <strong>#{{ shortJobId(job.job_id) }}</strong>
                <p>{{ job.source_url }}</p>
              </div>
              <div class="job-list-meta">
                <span>{{ job.progress }}%</span>
                <span>{{ formatDate(job.created_at) }}</span>
              </div>
            </RouterLink>
          </div>

          <p v-else class="empty-state">No jobs yet.</p>
        </section>
      </aside>
    </div>

    <div class="pipeline-help">
      <button class="pipeline-help-button" type="button" aria-label="Show pipeline workflow">
        ?
      </button>
      <section class="pipeline-popover">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Pipeline</p>
            <h2>Current workflow</h2>
          </div>
        </div>
        <ol class="pipeline-list">
          <li><span>01</span> Fetch source video</li>
          <li><span>02</span> Extract and transcribe audio</li>
          <li><span>03</span> Translate to Vietnamese</li>
          <li><span>04</span> Generate voice and subtitles</li>
          <li><span>05</span> Render final video</li>
        </ol>
      </section>
    </div>
  </section>
</template>
