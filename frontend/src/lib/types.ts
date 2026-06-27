export type JobStatus = 'queued' | 'processing' | 'cancelling' | 'completed' | 'failed' | 'cancelled'
export type JobSort = 'newest' | 'oldest' | 'progress'
export type JobEditSort = 'newest' | 'oldest'
export type JobEditToolFilter = 'all' | 'video' | 'audio' | 'captions'

export interface AuthUser {
  id: string
  email: string
  is_admin: boolean
}

export interface AuthSessionResponse {
  user: AuthUser
}

export interface LoginRequest {
  email: string
  password: string
}

export interface UserSettings {
  default_voice_id: string
  default_burn_subtitle: boolean
  default_mix_original_audio: boolean
  default_voice_volume_percent: number
  default_original_volume_percent: number
  default_subtitle_font_size: number
  default_subtitle_position: 'bottom' | 'lower_third' | 'top'
  default_subtitle_text_color: string
}

export interface UserSettingsResponse {
  settings: UserSettings
}

export interface JobCreateRequest {
  source_url: string
  voice_id: string
  burn_subtitle: boolean
  mix_original_audio: boolean
}

export interface JobUploadRequest {
  source_file: File
  voice_id: string
  burn_subtitle: boolean
  mix_original_audio: boolean
}

export interface JobCreateResponse {
  job_id: string
  status: JobStatus
}

export interface JobEditRenderRequest {
  trim_start_seconds: number
  trim_end_seconds: number | null
  playback_speed: number
  blur_original_subtitles: boolean
  blur_x_ratio: number
  blur_y_ratio: number
  blur_width_ratio: number
  blur_height_ratio: number
  blur_strength: number
  blur_masks: BlurMaskItem[] | null
  voice_volume_percent: number
  original_volume_percent: number
  burn_audio: boolean
  burn_original_audio: boolean
  burn_subtitle: boolean
  subtitle_font_size: number
  subtitle_position: 'bottom' | 'lower_third' | 'top'
  subtitle_text_color: string
  subtitle_segments: JobSubtitleSegment[] | null
  overlay_enabled: boolean
  overlay_text: string
  overlay_position:
    | 'top_left'
    | 'top_center'
    | 'top_right'
    | 'bottom_left'
    | 'bottom_center'
    | 'bottom_right'
    | 'custom'
  overlay_x_ratio: number
  overlay_y_ratio: number
  overlay_font_size: number
  overlay_text_color: string
  overlays: OverlayItem[] | null
}

export interface BlurMaskItem {
  id: string
  enabled: boolean
  x_ratio: number
  y_ratio: number
  width_ratio: number
  height_ratio: number
  strength: number
}

export interface OverlayItem {
  id: string
  enabled: boolean
  text: string
  position:
    | 'top_left'
    | 'top_center'
    | 'top_right'
    | 'bottom_left'
    | 'bottom_center'
    | 'bottom_right'
    | 'custom'
  x_ratio: number
  y_ratio: number
  font_size: number
  text_color: string
}

export interface JobSubtitleSegment {
  id: number
  start: number
  end: number
  text_vi: string
  text_zh: string | null
}

export interface JobEditRenderResponse {
  job_id: string
  edit_id: string
  result_url: string | null
  render_status: 'queued' | 'processing' | 'completed' | 'failed'
  error_message: string | null
}

export interface JobEditorStateResponse {
  job_id: string
  subtitle_segments: JobSubtitleSegment[]
  render_config: Record<string, unknown>
}

export interface JobEditDetailResponse {
  edit_id: string
  job_id: string
  version_number: number | null
  tool_summary: string
  config: Record<string, unknown>
  result_url: string | null
  render_status: 'queued' | 'processing' | 'completed' | 'failed'
  error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export interface JobEditListItem {
  edit_id: string
  job_id: string
  version_number: number | null
  tool_group: string
  tool_options: string
  result_url: string
  created_at: string | null
  updated_at: string | null
}

export interface JobEditListResponse {
  items: JobEditListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface JobEditListParams {
  page?: number
  page_size?: number
  search?: string
  tool?: JobEditToolFilter
  sort?: JobEditSort
}

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  progress: number
  stage: string | null
  error_message: string | null
  result_url: string | null
  subtitle_url: string | null
  created_at?: string | null
  updated_at?: string | null
  completed_at?: string | null
}

export interface JobListItem {
  job_id: string
  source_url: string
  platform: string | null
  status: JobStatus
  stage: string | null
  progress: number
  error_message: string | null
  created_at: string | null
  updated_at: string | null
  completed_at: string | null
}

export interface JobListResponse {
  items: JobListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface JobListParams {
  page?: number
  page_size?: number
  search?: string
  status?: 'all' | JobStatus
  sort?: JobSort
}

export interface JobLogItem {
  id: string
  level: string
  stage: string | null
  message: string
  data: Record<string, unknown> | null
  created_at: string | null
}
