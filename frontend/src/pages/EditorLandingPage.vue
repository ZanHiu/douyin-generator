<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Check, ChevronDown, Download, Pencil, RefreshCw, Search } from 'lucide-vue-next'
import { listAllJobEdits, listJobEditsPage, resolveApiDownloadUrl } from '../lib/api'
import type { JobEditListItem, JobEditSort, JobEditToolFilter } from '../lib/types'

const route = useRoute()
const router = useRouter()

const editHistory = ref<JobEditListItem[]>([])
const allEditHistory = ref<JobEditListItem[]>([])
const searchQuery = ref('')
const toolFilter = ref<JobEditToolFilter>('all')
const sortKey = ref<JobEditSort>('newest')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const totalPages = ref(1)
const isToolMenuOpen = ref(false)
const isSortMenuOpen = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')

const toolOptions: Array<{ label: string; value: JobEditToolFilter }> = [
  { label: 'All tools', value: 'all' },
  { label: 'Video', value: 'video' },
  { label: 'Audio', value: 'audio' },
  { label: 'Captions', value: 'captions' }
]

const sortOptions: Array<{ label: string; value: JobEditSort }> = [
  { label: 'Newest first', value: 'newest' },
  { label: 'Oldest first', value: 'oldest' }
]

const stats = computed(() => {
  const hasGroup = (group: string) =>
    allEditHistory.value.filter((item) => item.tool_group.split('+').map((part) => part.trim()).includes(group)).length

  return {
    total: allEditHistory.value.length,
    audio: hasGroup('Audio'),
    video: hasGroup('Video'),
    captions: hasGroup('Captions'),
    mixed: allEditHistory.value.filter((item) => item.tool_group.includes('+')).length
  }
})

const groupedEditHistory = computed(() => {
  const groups = new Map<
    string,
    {
      jobId: string
      latestUpdatedAt: string | null
      items: JobEditListItem[]
    }
  >()

  for (const item of editHistory.value) {
    const existing = groups.get(item.job_id)
    if (existing) {
      existing.items.push(item)
      continue
    }
    groups.set(item.job_id, {
      jobId: item.job_id,
      latestUpdatedAt: item.updated_at || item.created_at,
      items: [item]
    })
  }

  return Array.from(groups.values()).map((group) => ({
    ...group,
    items: group.items.sort((left, right) => (right.version_number || 0) - (left.version_number || 0))
  }))
})

const selectedToolLabel = computed(() => {
  return toolOptions.find((option) => option.value === toolFilter.value)?.label || 'All tools'
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

function formatVersion(value: number | null) {
  return value ? `v${value}` : 'Legacy'
}

function normalizeTool(value: unknown): JobEditToolFilter {
  return toolOptions.some((option) => option.value === value) ? (value as JobEditToolFilter) : 'all'
}

function normalizeSort(value: unknown): JobEditSort {
  return sortOptions.some((option) => option.value === value) ? (value as JobEditSort) : 'newest'
}

function normalizePositiveNumber(value: unknown, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback
}

function syncStateFromRoute() {
  searchQuery.value = typeof route.query.search === 'string' ? route.query.search : ''
  toolFilter.value = normalizeTool(route.query.tool)
  sortKey.value = normalizeSort(route.query.sort)
  page.value = normalizePositiveNumber(route.query.page, 1)
  pageSize.value = normalizePositiveNumber(route.query.page_size, 10)
}

async function loadEditHistoryFromRoute() {
  syncStateFromRoute()
  isLoading.value = true
  errorMessage.value = ''
  try {
    const filters = {
      search: searchQuery.value,
      tool: toolFilter.value,
      sort: sortKey.value
    }
    const [response, fullDataset] = await Promise.all([
      listJobEditsPage({
        page: page.value,
        page_size: pageSize.value,
        ...filters
      }),
      listAllJobEdits(filters)
    ])
    editHistory.value = response.items
    allEditHistory.value = fullDataset
    total.value = response.total
    page.value = response.page
    pageSize.value = response.page_size
    totalPages.value = response.total_pages
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not load edit history.'
    allEditHistory.value = []
  } finally {
    isLoading.value = false
  }
}

function updateQuery(next: {
  search?: string
  tool?: JobEditToolFilter
  sort?: JobEditSort
  page?: number
  page_size?: number
}) {
  const query: Record<string, string> = {}
  const nextSearch = next.search ?? searchQuery.value
  const nextTool = next.tool ?? toolFilter.value
  const nextSort = next.sort ?? sortKey.value
  const nextPage = next.page ?? page.value
  const nextPageSize = next.page_size ?? pageSize.value

  if (nextSearch.trim()) query.search = nextSearch.trim()
  if (nextTool !== 'all') query.tool = nextTool
  if (nextSort !== 'newest') query.sort = nextSort
  if (nextPage > 1) query.page = String(nextPage)
  if (nextPageSize !== 10) query.page_size = String(nextPageSize)

  void router.push({ name: 'editor', query })
}

function applySearch() {
  updateQuery({ search: searchQuery.value, page: 1 })
}

function selectTool(value: JobEditToolFilter) {
  isToolMenuOpen.value = false
  updateQuery({ tool: value, page: 1 })
}

function selectSort(value: JobEditSort) {
  isSortMenuOpen.value = false
  updateQuery({ sort: value, page: 1 })
}

function goToPage(nextPage: number) {
  updateQuery({ page: Math.min(Math.max(1, nextPage), totalPages.value) })
}

function openEdit(item: JobEditListItem) {
  void router.push(`/editor/${item.job_id}?edit=${item.edit_id}&source=history`)
}

onMounted(loadEditHistoryFromRoute)
watch(() => route.fullPath, loadEditHistoryFromRoute)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <p class="eyebrow">Editor</p>
        <h1>Edit history</h1>
        <p>Review edited outputs, download renders, and reopen an existing editor session.</p>
      </div>
      <button class="secondary-button compact-button icon-button" type="button" @click="loadEditHistoryFromRoute">
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
        <span>Audio</span>
        <strong>{{ stats.audio }}</strong>
      </article>
      <article class="surface stat-card">
        <span>Video</span>
        <strong>{{ stats.video }}</strong>
      </article>
      <article class="surface stat-card">
        <span>Captions</span>
        <strong>{{ stats.captions }}</strong>
      </article>
      <article class="surface stat-card">
        <span>Mixed</span>
        <strong>{{ stats.mixed }}</strong>
      </article>
    </section>

    <section class="surface jobs-panel">
      <div class="jobs-toolbar">
        <label class="search-field">
          <Search :size="18" :stroke-width="2" aria-hidden="true" />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search by job ID, edit ID, or tool..."
            @keydown.enter.prevent="applySearch"
            @blur="applySearch"
          />
        </label>

        <div class="filter-menu">
          <button
            class="filter-trigger"
            type="button"
            :aria-expanded="isToolMenuOpen"
            @click="isToolMenuOpen = !isToolMenuOpen"
          >
            <span>
              <small>Tool</small>
              <strong>{{ selectedToolLabel }}</strong>
            </span>
            <ChevronDown :size="18" :stroke-width="2" aria-hidden="true" />
          </button>
          <div v-if="isToolMenuOpen" class="filter-options">
            <button
              v-for="option in toolOptions"
              :key="option.value"
              class="filter-option"
              type="button"
              @click="selectTool(option.value)"
            >
              <span>{{ option.label }}</span>
              <Check
                v-if="option.value === toolFilter"
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
        Loading edit history...
      </div>

      <div v-else-if="editHistory.length" class="editor-history-groups">
        <section
          v-for="group in groupedEditHistory"
          :key="group.jobId"
          class="surface editor-history-group"
        >
          <div class="editor-history-group-header">
            <div>
              <p class="eyebrow">Job</p>
              <h3>#{{ shortJobId(group.jobId) }}</h3>
              <p>{{ group.items.length }} version{{ group.items.length > 1 ? 's' : '' }} in this page</p>
            </div>
            <div class="editor-history-group-meta">
              <strong>{{ formatDate(group.latestUpdatedAt) }}</strong>
              <small>Latest version update</small>
            </div>
          </div>

          <div class="jobs-table editor-history-table" role="table" :aria-label="`Edit history for job ${group.jobId}`">
            <div class="jobs-table-head editor-history-table-head" role="row">
              <span>Version</span>
              <span>Tool</span>
              <span>Edited</span>
              <span>Actions</span>
            </div>

            <article
              v-for="item in group.items"
              :key="item.edit_id"
              class="jobs-table-row editor-history-table-row interactive-row"
              role="link"
              tabindex="0"
              @click="openEdit(item)"
              @keydown.enter.prevent="openEdit(item)"
              @keydown.space.prevent="openEdit(item)"
            >
              <span class="job-id-cell">
                <strong>{{ formatVersion(item.version_number) }}</strong>
                <small>{{ item.edit_id.slice(0, 8) }}</small>
              </span>
              <span class="source-cell">
                <strong>{{ item.tool_group }}</strong>
                <small>{{ item.tool_options }}</small>
              </span>
              <span class="date-cell">
                <strong>{{ formatDate(item.updated_at || item.created_at) }}</strong>
                <small>{{ item.updated_at && item.updated_at !== item.created_at ? 'Updated version' : 'Rendered edit' }}</small>
              </span>
              <span class="editor-history-row-actions">
                <RouterLink
                  class="secondary-button compact-button icon-button"
                  :to="`/editor/${item.job_id}?edit=${item.edit_id}&source=history`"
                  title="Reopen editor"
                  aria-label="Reopen editor"
                  @click.stop
                >
                  <Pencil :size="16" :stroke-width="2.2" aria-hidden="true" />
                </RouterLink>
                <a
                  class="primary-button compact-button icon-button"
                  :href="resolveApiDownloadUrl(item.result_url)"
                  title="Download edited video"
                  aria-label="Download edited video"
                  @click.stop
                >
                  <Download :size="16" :stroke-width="2.2" aria-hidden="true" />
                </a>
              </span>
            </article>
          </div>
        </section>
      </div>

      <div v-else class="empty-state large-empty-state empty-screen">
        <strong>{{ total === 0 && !searchQuery && toolFilter === 'all' ? 'No edits yet' : 'No matching edits' }}</strong>
        <p>
          {{
            total === 0 && !searchQuery && toolFilter === 'all'
              ? 'Render an edited version from the Editor workspace to start building edit history.'
              : 'Try another search term or switch to a different tool filter.'
          }}
        </p>
        <RouterLink
          v-if="total === 0 && !searchQuery && toolFilter === 'all'"
          class="primary-button compact-button"
          to="/jobs"
        >
          Open Job management
        </RouterLink>
      </div>

      <div v-if="!errorMessage && !isLoading && total > 0" class="pagination-bar">
        <span>
          Showing page {{ page }} of {{ totalPages }} · {{ total }} total edits
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
