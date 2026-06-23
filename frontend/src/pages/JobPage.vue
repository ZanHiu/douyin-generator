<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ArrowLeft, Download, Pencil, RotateCcw, X } from 'lucide-vue-next'
import JobProgress from '../components/JobProgress.vue'
import { cancelJob, getJob, getJobLogs, resolveApiAssetUrl, retryJob } from '../lib/api'
import type { JobLogItem, JobStatusResponse } from '../lib/types'

const route = useRoute()
const jobId = computed(() => String(route.params.jobId))
const job = ref<JobStatusResponse | null>(null)
const logs = ref<JobLogItem[]>([])
const errorMessage = ref('')
const logsErrorMessage = ref('')
const actionErrorMessage = ref('')
const isCancelling = ref(false)
const isRetrying = ref(false)
let timer: number | undefined

const isTerminal = computed(() => {
  return job.value && ['completed', 'failed', 'cancelled'].includes(job.value.status)
})

const canCancel = computed(() => job.value && ['queued', 'processing'].includes(job.value.status))
const canRetry = computed(() => job.value && ['failed', 'cancelled'].includes(job.value.status))
const progressStartedAt = computed(() => {
  const logTimes = logs.value
    .map((log) => log.created_at)
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => new Date(left).getTime() - new Date(right).getTime())

  return job.value?.created_at || logTimes[0] || null
})

const progressStoppedAt = computed(() => {
  if (!job.value || !isTerminal.value) return null

  const logTimes = logs.value
    .map((log) => log.created_at)
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => new Date(left).getTime() - new Date(right).getTime())

  return job.value.completed_at || job.value.updated_at || logTimes[logTimes.length - 1] || null
})

const resultVideoUrl = computed(() => resolveApiAssetUrl(job.value?.result_url))
const subtitleDownloadUrl = computed(() => resolveApiAssetUrl(job.value?.subtitle_url))

async function loadJob() {
  try {
    job.value = await getJob(jobId.value)
    errorMessage.value = ''
    if (isTerminal.value && timer) {
      window.clearInterval(timer)
      timer = undefined
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not load job.'
  }
}

async function handleCancelJob() {
  if (!canCancel.value || isCancelling.value) return
  isCancelling.value = true
  actionErrorMessage.value = ''
  try {
    job.value = await cancelJob(jobId.value)
    await loadLogs()
  } catch (error) {
    actionErrorMessage.value = error instanceof Error ? error.message : 'Could not cancel job.'
  } finally {
    isCancelling.value = false
  }
}

async function handleRetryJob() {
  if (!canRetry.value || isRetrying.value) return
  isRetrying.value = true
  actionErrorMessage.value = ''
  try {
    await retryJob(jobId.value)
    await loadJob()
    await loadLogs()
    if (!timer) {
      timer = window.setInterval(async () => {
        await loadJob()
        await loadLogs()
      }, 2000)
    }
  } catch (error) {
    actionErrorMessage.value = error instanceof Error ? error.message : 'Could not retry job.'
  } finally {
    isRetrying.value = false
  }
}

async function loadLogs() {
  try {
    logs.value = await getJobLogs(jobId.value)
    logsErrorMessage.value = ''
  } catch (error) {
    logsErrorMessage.value = error instanceof Error ? error.message : 'Could not load logs.'
  }
}

function formatDate(value: string | null) {
  if (!value) return ''
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'short',
    timeStyle: 'medium'
  }).format(new Date(value))
}

onMounted(async () => {
  await loadJob()
  await loadLogs()
  timer = window.setInterval(async () => {
    await loadJob()
    await loadLogs()
  }, 2000)
})

onUnmounted(() => {
  if (timer) {
    window.clearInterval(timer)
  }
})
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <RouterLink class="back-link" to="/">
          <ArrowLeft :size="18" :stroke-width="2.3" aria-hidden="true" />
          Back to Generate
        </RouterLink>
        <p class="eyebrow">Job detail</p>
        <h1>{{ jobId }}</h1>
      </div>
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <div class="job-detail-layout">
      <div v-if="job && (canCancel || canRetry || actionErrorMessage)" class="job-inline-actions">
        <div class="job-inline-actions-spacer" />
        <button
          v-if="canCancel"
          class="danger-button compact-button icon-button job-action-button"
          type="button"
          :disabled="isCancelling"
          @click="handleCancelJob"
        >
          <X :size="16" :stroke-width="2.2" aria-hidden="true" />
          {{ isCancelling ? 'Cancelling...' : 'Cancel' }}
        </button>
        <button
          v-if="canRetry"
          class="secondary-button compact-button icon-button job-action-button"
          type="button"
          :disabled="isRetrying"
          @click="handleRetryJob"
        >
          <RotateCcw :size="16" :stroke-width="2.2" aria-hidden="true" />
          {{ isRetrying ? 'Retrying...' : 'Retry' }}
        </button>
      </div>

      <JobProgress
        v-if="job"
        :job="job"
        :started-at="progressStartedAt"
        :stopped-at="progressStoppedAt"
      />

      <div v-if="actionErrorMessage" class="job-inline-actions">
        <p v-if="actionErrorMessage" class="error-message">{{ actionErrorMessage }}</p>
      </div>

      <div class="job-detail-grid">
        <section class="surface">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Outputs</p>
              <h2>Downloads</h2>
            </div>
          </div>

          <div v-if="job?.status === 'completed'" class="output-stack">
            <div v-if="resultVideoUrl" class="video-preview">
              <video :src="resultVideoUrl" controls preload="metadata" />
            </div>

            <div class="download-stack">
              <RouterLink class="secondary-button icon-button" :to="`/editor/${jobId}?source=job`">
                <Pencil :size="16" :stroke-width="2.2" aria-hidden="true" />
                Open in Editor
              </RouterLink>
              <a v-if="subtitleDownloadUrl" class="secondary-button icon-button" :href="subtitleDownloadUrl">
                <Download :size="16" :stroke-width="2.2" aria-hidden="true" />
                Download subtitles
              </a>
              <a v-if="resultVideoUrl" class="primary-button icon-button" :href="resultVideoUrl">
                <Download :size="16" :stroke-width="2.2" aria-hidden="true" />
                Download final video
              </a>
            </div>
          </div>
          <p v-else class="empty-state">
            Downloads appear here when rendering is complete.
          </p>
        </section>

        <section class="surface">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Activity</p>
              <h2>Processing logs</h2>
            </div>
            <button class="secondary-button compact-button" type="button" @click="loadLogs">
              Refresh
            </button>
          </div>

          <p v-if="logsErrorMessage" class="error-message">{{ logsErrorMessage }}</p>

          <div v-if="logs.length" class="log-list">
            <article v-for="log in logs" :key="log.id" class="log-row">
              <div class="log-meta">
                <span :class="['log-level', `log-level-${log.level}`]">{{ log.level }}</span>
                <span>{{ log.stage || 'none' }}</span>
                <span>{{ formatDate(log.created_at) }}</span>
              </div>
              <p>{{ log.message }}</p>
            </article>
          </div>

          <p v-else class="empty-state">No logs yet.</p>
        </section>
      </div>
    </div>
  </section>
</template>
