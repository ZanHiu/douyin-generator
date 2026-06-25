import type {
  AuthSessionResponse,
  JobCreateRequest,
  JobCreateResponse,
  JobEditorStateResponse,
  JobEditDetailResponse,
  JobEditListItem,
  JobEditListParams,
  JobEditListResponse,
  JobEditRenderRequest,
  JobEditRenderResponse,
  JobListItem,
  JobListParams,
  JobListResponse,
  JobLogItem,
  JobStatusResponse
  ,LoginRequest
  ,JobUploadRequest
  ,UserSettings
  ,UserSettingsResponse
} from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

function toApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return API_BASE_URL ? `${API_BASE_URL}${normalizedPath}` : normalizedPath
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== 'undefined' && init?.body instanceof FormData
  const headers = new Headers(init?.headers)
  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(toApiUrl(path), {
    ...init,
    credentials: 'include',
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(', ')
      : detail || 'Request failed'
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function resolveApiAssetUrl(path: string | null | undefined): string {
  if (!path) {
    return ''
  }
  return toApiUrl(path)
}

export function login(payload: LoginRequest): Promise<AuthSessionResponse> {
  return request<AuthSessionResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function logout(): Promise<void> {
  return request<void>('/api/auth/logout', {
    method: 'POST'
  })
}

export function getCurrentSession(): Promise<AuthSessionResponse> {
  return request<AuthSessionResponse>('/api/auth/me')
}

export function getMySettings(): Promise<UserSettingsResponse> {
  return request<UserSettingsResponse>('/api/settings/me')
}

export function saveMySettings(payload: UserSettings): Promise<UserSettingsResponse> {
  return request<UserSettingsResponse>('/api/settings/me', {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function createJob(payload: JobCreateRequest): Promise<JobCreateResponse> {
  return request<JobCreateResponse>('/api/jobs', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function createUploadedJob(payload: JobUploadRequest): Promise<JobCreateResponse> {
  const formData = new FormData()
  formData.set('source_file', payload.source_file)
  formData.set('voice_id', payload.voice_id)
  formData.set('burn_subtitle', String(payload.burn_subtitle))
  formData.set('mix_original_audio', String(payload.mix_original_audio))
  return request<JobCreateResponse>('/api/jobs/upload', {
    method: 'POST',
    body: formData
  })
}

export function getJob(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/jobs/${jobId}`)
}

export function cancelJob(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/jobs/${jobId}/cancel`, {
    method: 'POST'
  })
}

export function retryJob(jobId: string): Promise<JobCreateResponse> {
  return request<JobCreateResponse>(`/api/jobs/${jobId}/retry`, {
    method: 'POST'
  })
}

export function getJobEditorState(jobId: string): Promise<JobEditorStateResponse> {
  return request<JobEditorStateResponse>(`/api/jobs/${jobId}/editor-state`)
}

export function getJobEditDetail(jobId: string, editId: string): Promise<JobEditDetailResponse> {
  return request<JobEditDetailResponse>(`/api/jobs/${jobId}/edits/${editId}`)
}

function buildJobsQuery(params: JobListParams) {
  const query = new URLSearchParams()
  query.set('page', String(params.page || 1))
  query.set('page_size', String(params.page_size || 20))

  if (params.search?.trim()) {
    query.set('search', params.search.trim())
  }

  if (params.status && params.status !== 'all') {
    query.set('status', params.status)
  }

  if (params.sort) {
    query.set('sort', params.sort)
  }

  return query.toString()
}

export function listJobsPage(params: JobListParams = {}): Promise<JobListResponse> {
  return request<JobListResponse>(`/api/jobs?${buildJobsQuery(params)}`)
}

export async function listAllJobs(params: JobListParams = {}): Promise<JobListItem[]> {
  const firstPage = await listJobsPage({ ...params, page: 1, page_size: 100 })

  if (firstPage.total_pages <= 1) {
    return firstPage.items
  }

  const remainingPages = await Promise.all(
    Array.from({ length: firstPage.total_pages - 1 }, (_, index) =>
      listJobsPage({
        ...params,
        page: index + 2,
        page_size: firstPage.page_size
      })
    )
  )

  return [firstPage.items, ...remainingPages.map((page) => page.items)].flat()
}

export async function listJobs(limit = 10): Promise<JobListItem[]> {
  const response = await listJobsPage({ page: 1, page_size: limit, sort: 'newest' })
  return response.items
}

export function getJobLogs(jobId: string): Promise<JobLogItem[]> {
  return request<JobLogItem[]>(`/api/jobs/${jobId}/logs`)
}

export function renderEditedVideo(
  jobId: string,
  payload: JobEditRenderRequest,
  options?: { overwriteEditId?: string | null }
): Promise<JobEditRenderResponse> {
  const query = new URLSearchParams()
  if (options?.overwriteEditId) {
    query.set('overwrite_edit_id', options.overwriteEditId)
  }
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request<JobEditRenderResponse>(`/api/jobs/${jobId}/edits/render${suffix}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

function buildJobEditsQuery(params: JobEditListParams) {
  const query = new URLSearchParams()
  query.set('page', String(params.page || 1))
  query.set('page_size', String(params.page_size || 20))

  if (params.search?.trim()) {
    query.set('search', params.search.trim())
  }

  if (params.tool && params.tool !== 'all') {
    query.set('tool', params.tool)
  }

  if (params.sort && params.sort !== 'newest') {
    query.set('sort', params.sort)
  }

  return query.toString()
}

export function listJobEditsPage(params: JobEditListParams = {}): Promise<JobEditListResponse> {
  return request<JobEditListResponse>(`/api/jobs/edits?${buildJobEditsQuery(params)}`)
}

export async function listAllJobEdits(params: JobEditListParams = {}): Promise<JobEditListItem[]> {
  const firstPage = await listJobEditsPage({ ...params, page: 1, page_size: 100 })

  if (firstPage.total_pages <= 1) {
    return firstPage.items
  }

  const remainingPages = await Promise.all(
    Array.from({ length: firstPage.total_pages - 1 }, (_, index) =>
      listJobEditsPage({
        ...params,
        page: index + 2,
        page_size: firstPage.page_size
      })
    )
  )

  return [firstPage.items, ...remainingPages.map((page) => page.items)].flat()
}
