<script setup lang="ts">
import { computed } from 'vue'
import type { JobStatusResponse } from '../lib/types'

const props = defineProps<{
  job: JobStatusResponse
  startedAt?: string | null
  stoppedAt?: string | null
}>()

const stageLabels: Record<string, string> = {
  created: 'Job created',
  fetching_video: 'Fetching video',
  extracting_audio: 'Extracting audio',
  transcribing: 'Transcribing speech',
  translating: 'Translating to Vietnamese',
  generating_subtitles: 'Generating subtitles',
  generating_tts: 'Generating Vietnamese voice',
  rendering_video: 'Rendering video',
  cancelling: 'Cancelling',
  cancelled: 'Cancelled',
  completed: 'Completed',
  failed: 'Failed'
}

const progressFillClass = computed(() => `progress-fill-${props.job.status}`)
const progressValueClass = computed(() => `progress-value-${props.job.status}`)
const isActiveProgress = computed(() => ['queued', 'processing', 'cancelling'].includes(props.job.status))
const durationLabel = computed(() => {
  if (!props.startedAt) return ''

  const startMs = new Date(props.startedAt).getTime()
  const endMs = props.stoppedAt ? new Date(props.stoppedAt).getTime() : Date.now()

  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) {
    return ''
  }

  const totalSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`
  }

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }

  return `${seconds}s`
})
</script>

<template>
  <section class="surface progress-panel">
    <div class="progress-header">
      <div>
        <p class="label">Status</p>
        <h2>{{ job.status }}</h2>
      </div>
      <span :class="['progress-value', progressValueClass]">{{ job.progress }}%</span>
    </div>

    <div class="progress-track" aria-label="Job progress">
      <div
        :class="['progress-fill', progressFillClass, { 'progress-fill-live': isActiveProgress }]"
        :style="{ width: `${job.progress}%` }"
      >
        <span class="progress-fill-glow" aria-hidden="true" />
      </div>
    </div>

    <div class="progress-meta">
      <span class="stage">{{ stageLabels[job.stage || 'created'] || job.stage }}</span>
      <span v-if="durationLabel" class="progress-duration">{{ durationLabel }}</span>
    </div>

    <p v-if="job.error_message" class="error-message">
      {{ job.error_message }}
    </p>
  </section>
</template>
