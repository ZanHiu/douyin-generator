<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Check, ChevronDown, Eye, RefreshCw, RotateCcw, Search, X } from 'lucide-vue-next'
import { cancelJob, listAllJobs, listJobsPage, retryJob } from '../lib/api'
import type { JobListItem, JobSort, JobStatus } from '../lib/types'

type StatusFilter = 'all' | JobStatus

const route = useRoute()
const router = useRouter()

const jobs = ref<JobListItem[]>([])
const allJobs = ref<JobListItem[]>([])
const searchQuery = ref('')
const statusFilter = ref<StatusFilter>('all')
const sortKey = ref<JobSort>('newest')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const totalPages = ref(1)
const isStatusMenuOpen = ref(false)
const isSortMenuOpen = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')
const actionJobId = ref('')

const statusOptions: Array<{ label: string; value: StatusFilter }> = [
  { label: 'All', value: 'all' },
  { label: 'Queued', value: 'queued' },
  { label: 'Processing', value: 'processing' },
  { label: 'Cancelling', value: 'cancelling' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' }
]

const sortOptions: Array<{ label: string; value: JobSort }> = [
  { label: 'Newest first', value: 'newest' },
  { label: 'Oldest first', value: 'oldest' },
  { label: 'Highest progress', value: 'progress' }
]

const stats = computed(() => {
  return {
    total: allJobs.value.length,
    completed: allJobs.value.filter((job) => job.status === 'completed').length,
    failed: allJobs.value.filter((job) => job.status === 'failed').length,
    processing: allJobs.value.filter((job) => ['queued', 'processing', 'cancelling'].includes(job.status)).length
  }
})

const selectedStatusLabel = computed(() => {
  return statusOptions.find((option) => option.value === statusFilter.value)?.label || 'All'
})

const selectedSortLabel = computed(() => {
  return sortOptions.find((option) => option.value === sortKey.value)?.label || 'Newest first'
})

function formatDate(value: string | null) {
  if (!value) return 'Not available'
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function shortJobId(jobId: string) {
  return jobId.slice(0, 8)
}

function platformLabel(platform: string | null) {
  return platform || 'unknown'
}

function progressFillClass(status: JobStatus) {
  return `progress-fill-${status}`
}

function progressValueClass(status: JobStatus) {
  return `progress-value-${status}`
}

function normalizeStatus(value: unknown): StatusFilter {
  return statusOptions.some((option) => option.value === value) ? (value as StatusFilter) : 'all'
}

function normalizeSort(value: unknown): JobSort {
  return sortOptions.some((option) => option.value === value) ? (value as JobSort) : 'newest'
}

function normalizePositiveNumber(value: unknown, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback
}

function syncStateFromRoute() {
  searchQuery.value = typeof route.query.search === 'string' ? route.query.search : ''
  statusFilter.value = normalizeStatus(route.query.status)
  sortKey.value = normalizeSort(route.query.sort)
  page.value = normalizePositiveNumber(route.query.page, 1)
  pageSize.value = normalizePositiveNumber(route.query.page_size, 10)
}

async function loadJobsFromRoute() {
  syncStateFromRoute()
  isLoading.value = true
  try {
    const filters = {
      search: searchQuery.value,
      status: statusFilter.value,
      sort: sortKey.value
    }
    const [response, fullDataset] = await Promise.all([
      listJobsPage({
        page: page.value,
        page_size: pageSize.value,
        ...filters
      }),
      listAllJobs(filters)
    ])
    jobs.value = response.items
    allJobs.value = fullDataset
    total.value = response.total
    page.value = response.page
    pageSize.value = response.page_size
    totalPages.value = response.total_pages
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not load jobs.'
    allJobs.value = []
  } finally {
    isLoading.value = false
  }
}

function updateQuery(next: {
  search?: string
  status?: StatusFilter
  sort?: JobSort
  page?: number
  page_size?: number
}) {
  const query: Record<string, string> = {}
  const nextSearch = next.search ?? searchQuery.value
  const nextStatus = next.status ?? statusFilter.value
  const nextSort = next.sort ?? sortKey.value
  const nextPage = next.page ?? page.value
  const nextPageSize = next.page_size ?? pageSize.value

  if (nextSearch.trim()) query.search = nextSearch.trim()
  if (nextStatus !== 'all') query.status = nextStatus
  if (nextSort !== 'newest') query.sort = nextSort
  if (nextPage > 1) query.page = String(nextPage)
  if (nextPageSize !== 10) query.page_size = String(nextPageSize)

  void router.push({ name: 'jobs', query })
}

function applySearch() {
  updateQuery({ search: searchQuery.value, page: 1 })
}

function selectStatus(value: StatusFilter) {
  isStatusMenuOpen.value = false
  updateQuery({ status: value, page: 1 })
}

function selectSort(value: JobSort) {
  isSortMenuOpen.value = false
  updateQuery({ sort: value, page: 1 })
}

function goToPage(nextPage: number) {
  updateQuery({ page: Math.min(Math.max(1, nextPage), totalPages.value) })
}

function canCancel(job: JobListItem) {
  return ['queued', 'processing'].includes(job.status)
}

function canRetry(job: JobListItem) {
  return ['failed', 'cancelled'].includes(job.status)
}

async function handleCancelJob(jobId: string) {
  if (actionJobId.value) return
  actionJobId.value = jobId
  try {
    await cancelJob(jobId)
    await loadJobsFromRoute()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not cancel job.'
  } finally {
    actionJobId.value = ''
  }
}

async function handleRetryJob(jobId: string) {
  if (actionJobId.value) return
  actionJobId.value = jobId
  try {
    await retryJob(jobId)
    await loadJobsFromRoute()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not retry job.'
  } finally {
    actionJobId.value = ''
  }
}

onMounted(loadJobsFromRoute)
watch(() => route.fullPath, loadJobsFromRoute)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">Jobs</p>
        <h1>Job management</h1>
        <p>Review all generated jobs, track pipeline state, and reopen outputs.</p>
      </div>
      <button class="secondary-button compact-button icon-button" type="button" @click="loadJobsFromRoute">
        <RefreshCw :size="16" :stroke-width="2" aria-hidden="true" />
        <span>{{ isLoading ? 'Refreshing...' : 'Refresh' }}</span>
      </button>
    </div>

    <section class="jobs-stats">
      <article class="surface stat-card">
        <span>Total</span>
        <strong>{{ stats.total }}</strong>
      </article>
      <article class="surface stat-card">
        <span>Processing</span>
        <strong>{{ stats.processing }}</strong>
      </article>
      <article class="surface stat-card">
        <span>Completed</span>
        <strong>{{ stats.completed }}</strong>
      </article>
      <article class="surface stat-card">
        <span>Failed</span>
        <strong>{{ stats.failed }}</strong>
      </article>
    </section>

    <section class="surface jobs-panel">
      <div class="jobs-toolbar">
        <label class="search-field">
          <Search :size="18" :stroke-width="2" aria-hidden="true" />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search by job ID, URL, platform, stage..."
            @keydown.enter.prevent="applySearch"
            @blur="applySearch"
          />
        </label>

        <div class="filter-menu">
          <button
            class="filter-trigger"
            type="button"
            :aria-expanded="isStatusMenuOpen"
            @click="isStatusMenuOpen = !isStatusMenuOpen"
          >
            <span>
              <small>Status</small>
              <strong>{{ selectedStatusLabel }}</strong>
            </span>
            <ChevronDown :size="18" :stroke-width="2" aria-hidden="true" />
          </button>
          <div v-if="isStatusMenuOpen" class="filter-options">
            <button
              v-for="option in statusOptions"
              :key="option.value"
              class="filter-option"
              type="button"
              @click="selectStatus(option.value)"
            >
              <span>{{ option.label }}</span>
              <Check
                v-if="option.value === statusFilter"
                :size="16"
                :stroke-width="2.5"
                aria-hidden="true"
              />
            </button>
          </div>
        </div>

        <div class="filter-menu">
          <button
            class="filter-trigger"
            type="button"
            :aria-expanded="isSortMenuOpen"
            @click="isSortMenuOpen = !isSortMenuOpen"
          >
            <span>
              <small>Sort</small>
              <strong>{{ selectedSortLabel }}</strong>
            </span>
            <ChevronDown :size="18" :stroke-width="2" aria-hidden="true" />
          </button>
          <div v-if="isSortMenuOpen" class="filter-options">
            <button
              v-for="option in sortOptions"
              :key="option.value"
              class="filter-option"
              type="button"
              @click="selectSort(option.value)"
            >
              <span>{{ option.label }}</span>
              <Check
                v-if="option.value === sortKey"
                :size="16"
                :stroke-width="2.5"
                aria-hidden="true"
              />
            </button>
          </div>
        </div>
      </div>

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <div v-else-if="isLoading" class="empty-state large-empty-state">
        Loading jobs...
      </div>

      <div v-else-if="jobs.length" class="jobs-table" role="table" aria-label="Job management">
        <div class="jobs-table-head" role="row">
          <span>Job</span>
          <span>Source</span>
          <span>Status</span>
          <span>Progress</span>
          <span>Created</span>
          <span>Actions</span>
        </div>

        <RouterLink
          v-for="job in jobs"
          :key="job.job_id"
          class="jobs-table-row"
          :to="`/jobs/${job.job_id}`"
          role="row"
        >
          <span class="job-id-cell">
            <strong>#{{ shortJobId(job.job_id) }}</strong>
            <small>{{ platformLabel(job.platform) }}</small>
          </span>
          <span class="source-cell">
            <strong>{{ job.source_url }}</strong>
            <small>{{ job.stage || 'created' }}</small>
          </span>
          <span>
            <span :class="['status-pill', `status-${job.status}`]">{{ job.status }}</span>
          </span>
          <span class="progress-cell">
            <strong :class="progressValueClass(job.status)">{{ job.progress }}%</strong>
            <span class="mini-progress-track">
              <span
                :class="['mini-progress-fill', progressFillClass(job.status)]"
                :style="{ width: `${job.progress}%` }"
              />
            </span>
          </span>
          <span class="date-cell">
            <strong>{{ formatDate(job.created_at) }}</strong>
            <small v-if="job.completed_at">Done {{ formatDate(job.completed_at) }}</small>
          </span>
          <span class="jobs-row-actions">
            <RouterLink
              class="secondary-button compact-button icon-button"
              :to="`/jobs/${job.job_id}`"
              title="View detail"
              aria-label="View detail"
              @click.stop
            >
              <Eye :size="16" :stroke-width="2.2" aria-hidden="true" />
            </RouterLink>
            <button
              v-if="canCancel(job)"
              class="danger-button compact-button icon-button"
              type="button"
              title="Cancel job"
              aria-label="Cancel job"
              :disabled="actionJobId === job.job_id"
              @click.stop.prevent="handleCancelJob(job.job_id)"
            >
              <X :size="16" :stroke-width="2.2" aria-hidden="true" />
            </button>
            <button
              v-if="canRetry(job)"
              class="secondary-button compact-button icon-button"
              type="button"
              title="Retry job"
              aria-label="Retry job"
              :disabled="actionJobId === job.job_id"
              @click.stop.prevent="handleRetryJob(job.job_id)"
            >
              <RotateCcw :size="16" :stroke-width="2.2" aria-hidden="true" />
            </button>
          </span>
        </RouterLink>
      </div>

      <div v-else class="empty-state large-empty-state empty-screen">
        <strong>{{ total === 0 && !searchQuery && statusFilter === 'all' ? 'No jobs yet' : 'No matching jobs' }}</strong>
        <p>
          {{
            total === 0 && !searchQuery && statusFilter === 'all'
              ? 'Create the first processing job from the Generate workspace.'
              : 'Try another search term or clear the current filters.'
          }}
        </p>
        <RouterLink
          v-if="total === 0 && !searchQuery && statusFilter === 'all'"
          class="primary-button compact-button"
          to="/"
        >
          Go to Generate
        </RouterLink>
      </div>

      <div v-if="!errorMessage && !isLoading && total > 0" class="pagination-bar">
        <span>
          Showing page {{ page }} of {{ totalPages }} · {{ total }} total jobs
        </span>
        <div class="pagination-actions">
          <button
            class="secondary-button compact-button"
            type="button"
            :disabled="page <= 1"
            @click="goToPage(page - 1)"
          >
            Previous
          </button>
          <button
            class="secondary-button compact-button"
            type="button"
            :disabled="page >= totalPages"
            @click="goToPage(page + 1)"
          >
            Next
          </button>
        </div>
      </div>
    </section>
  </section>
</template>
