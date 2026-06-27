<script setup lang="ts">
import Moveable from 'vue3-moveable'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Captions,
  Check,
  ChevronDown,
  Clapperboard,
  Download,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Volume2,
  VolumeX,
  X,
} from 'lucide-vue-next'
import EditorField from '../components/editor/EditorField.vue'
import EditorToggleField from '../components/editor/EditorToggleField.vue'
import { getJob, getJobEditDetail, getJobEditorState, renderEditedVideo, resolveApiAssetUrl } from '../lib/api'
import type {
  BlurMaskItem,
  JobEditRenderRequest,
  JobStatusResponse,
  JobSubtitleSegment,
  OverlayItem,
} from '../lib/types'

type OverlayPosition =
  | 'top_left'
  | 'top_center'
  | 'top_right'
  | 'bottom_left'
  | 'bottom_center'
  | 'bottom_right'
  | 'custom'

type SubtitlePosition = 'bottom' | 'lower_third' | 'top'

type EditorConfig = Omit<JobEditRenderRequest, 'subtitle_segments'> & {
  subtitle_segments: JobSubtitleSegment[]
}

type ChangeSummary = {
  total: number
  groups: {
    video: string[]
    audio: string[]
    captions: string[]
  }
  tools: {
    trim: string[]
    blur: string[]
    overlay: string[]
    audio: string[]
    style: string[]
    editor: string[]
  }
}

const route = useRoute()
const router = useRouter()
const jobId = computed(() => String(route.params.jobId))
const editId = computed(() => (typeof route.query.edit === 'string' ? route.query.edit : ''))
const editorSource = computed(() => (route.query.source === 'history' ? 'history' : 'job'))

const job = ref<JobStatusResponse | null>(null)
const editedResultUrl = ref('')
const baselineConfig = ref<EditorConfig | null>(null)
const createEditorItemId = (prefix: 'blur' | 'overlay') => `${prefix}-${Math.random().toString(36).slice(2, 10)}`

const trimStartSeconds = ref(0)
const trimEndSeconds = ref<number | null>(null)
const playbackSpeed = ref(1)
const blurMasks = ref<BlurMaskItem[]>([])
const selectedBlurId = ref('')
const overlays = ref<OverlayItem[]>([])
const selectedOverlayId = ref('')
const voiceVolumePercent = ref(100)
const originalVolumePercent = ref(35)
const burnAudio = ref(true)
const burnOriginalAudio = ref(true)
const burnSubtitle = ref(true)
const subtitleFontSize = ref(18)
const subtitlePosition = ref<SubtitlePosition>('bottom')
const subtitleTextColor = ref('#FFFFFF')
const subtitleSegments = ref<JobSubtitleSegment[]>([])

const isToolbarOpen = ref(false)
const activeGroup = ref<'video' | 'audio' | 'captions' | ''>('video')
const activeVideoTool = ref<'blur' | 'trim' | 'overlay'>('trim')
const activeCaptionsTool = ref<'style' | 'editor'>('style')
const selectedPreviewTool = ref<'' | 'blur' | 'overlay'>('')
const isSubtitlePositionMenuOpen = ref(false)
const isLoading = ref(false)
const isRendering = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const renderStatusMessage = ref('')
const previewFrameRef = ref<HTMLElement | null>(null)
const previewVideoRef = ref<HTMLVideoElement | null>(null)
const blurTargetRefs = ref<Record<string, HTMLElement | null>>({})
const overlayTargetRefs = ref<Record<string, HTMLElement | null>>({})
const blurMoveableRef = ref<InstanceType<typeof Moveable> | null>(null)
const overlayMoveableRef = ref<InstanceType<typeof Moveable> | null>(null)
const previewWidth = ref(0)
const previewHeight = ref(0)
const previewDuration = ref(0)
const previewCurrentTime = ref(0)
const previewPlaying = ref(false)
const previewMuted = ref(false)
let previewResizeObserver: ResizeObserver | null = null
let previewAnimationFrame = 0

const subtitlePositionOptions: Array<{ label: string; value: SubtitlePosition }> = [
  { label: 'Bottom', value: 'bottom' },
  { label: 'Lower third', value: 'lower_third' },
  { label: 'Top', value: 'top' },
]

const canEdit = computed(() => job.value?.status === 'completed')
const previewUrl = computed(() => resolveApiAssetUrl(editedResultUrl.value || job.value?.result_url || ''))
const backTarget = computed(() => (editorSource.value === 'history' ? '/editor' : `/jobs/${jobId.value}`))
const backLabel = computed(() => (editorSource.value === 'history' ? 'Back to Edit History' : 'Back to Job Detail'))
const isVideoGroupOpen = computed(() => isToolbarOpen.value && activeGroup.value === 'video')
const isAudioGroupOpen = computed(() => isToolbarOpen.value && activeGroup.value === 'audio')
const isCaptionsGroupOpen = computed(() => isToolbarOpen.value && activeGroup.value === 'captions')
const selectedSubtitlePositionLabel = computed(() => {
  return subtitlePositionOptions.find((option) => option.value === subtitlePosition.value)?.label || 'Bottom'
})

const currentConfig = computed<EditorConfig>(() => ({
  trim_start_seconds: trimStartSeconds.value,
  trim_end_seconds: trimEndSeconds.value,
  playback_speed: playbackSpeed.value,
  blur_original_subtitles: blurMasks.value.some((item) => item.enabled),
  blur_x_ratio: blurMasks.value[0]?.x_ratio ?? 0,
  blur_y_ratio: blurMasks.value[0]?.y_ratio ?? 0.78,
  blur_width_ratio: blurMasks.value[0]?.width_ratio ?? 1,
  blur_height_ratio: blurMasks.value[0]?.height_ratio ?? 0.22,
  blur_strength: blurMasks.value[0]?.strength ?? 11,
  blur_masks: blurMasks.value.map((item) => ({ ...item })),
  voice_volume_percent: voiceVolumePercent.value,
  original_volume_percent: originalVolumePercent.value,
  burn_audio: burnAudio.value,
  burn_original_audio: burnOriginalAudio.value,
  burn_subtitle: burnSubtitle.value,
  subtitle_font_size: subtitleFontSize.value,
  subtitle_position: subtitlePosition.value,
  subtitle_text_color: subtitleTextColor.value,
  subtitle_segments: subtitleSegments.value.map((segment) => ({ ...segment })),
  overlay_enabled: overlays.value.some((item) => item.enabled && item.text.trim()),
  overlay_text: overlays.value[0]?.text ?? '',
  overlay_position: overlays.value[0]?.position ?? 'top_right',
  overlay_x_ratio: overlays.value[0]?.x_ratio ?? 0,
  overlay_y_ratio: overlays.value[0]?.y_ratio ?? 0,
  overlay_font_size: overlays.value[0]?.font_size ?? 18,
  overlay_text_color: overlays.value[0]?.text_color ?? '#FFFFFF',
  overlays: overlays.value.map((item) => ({ ...item })),
}))

const dirtySummary = computed<ChangeSummary>(() => {
  if (!baselineConfig.value) {
    return emptySummary()
  }
  return buildChangeSummary(baselineConfig.value, currentConfig.value)
})

const hasPendingChanges = computed(() => dirtySummary.value.total > 0)
const renderSummaryTitle = computed(() => {
  const entries = [
    ...dirtySummary.value.groups.video,
    ...dirtySummary.value.groups.audio,
    ...dirtySummary.value.groups.captions,
  ]
  return entries.length ? entries.join(', ') : 'No pending changes'
})

const selectedBlurItem = computed(() => {
  return blurMasks.value.find((item) => item.id === selectedBlurId.value) || blurMasks.value[0] || null
})
const selectedOverlayItem = computed(() => {
  return overlays.value.find((item) => item.id === selectedOverlayId.value) || overlays.value[0] || null
})
const selectedBlurTargetRef = computed(() => {
  return selectedBlurItem.value ? blurTargetRefs.value[selectedBlurItem.value.id] || null : null
})
const selectedOverlayTargetRef = computed(() => {
  return selectedOverlayItem.value ? overlayTargetRefs.value[selectedOverlayItem.value.id] || null : null
})
const blurBoxStyle = (item: BlurMaskItem) => ({
  left: `${item.x_ratio * previewWidth.value}px`,
  top: `${item.y_ratio * previewHeight.value}px`,
  width: `${item.width_ratio * previewWidth.value}px`,
  height: `${item.height_ratio * previewHeight.value}px`,
  '--editor-preview-blur-strength': `${Math.max(item.strength, 2)}px`,
})

const showBlurMoveable = computed(() => {
  return !!selectedBlurItem.value?.enabled && selectedPreviewTool.value === 'blur'
})

const showOverlayMoveable = computed(() => {
  return !!selectedOverlayItem.value?.enabled && selectedPreviewTool.value === 'overlay'
})

const moveableBounds = computed(() => ({
  left: 0,
  top: 0,
  right: previewWidth.value,
  bottom: previewHeight.value,
}))

const overlayPreviewStyle = (item: OverlayItem) => {
  const base = {
    fontSize: `${item.font_size}px`,
    color: item.text_color,
  } as Record<string, string>

  if (item.position === 'custom') {
    return {
      ...base,
      left: `${item.x_ratio * previewWidth.value}px`,
      top: `${item.y_ratio * previewHeight.value}px`,
      right: 'auto',
      bottom: 'auto',
      transform: 'none',
    }
  }

  const presets: Record<Exclude<OverlayPosition, 'custom'>, Record<string, string>> = {
    top_left: { left: '36px', top: '36px', right: 'auto', bottom: 'auto', transform: 'none' },
    top_center: { left: '50%', top: '36px', right: 'auto', bottom: 'auto', transform: 'translateX(-50%)' },
    top_right: { left: 'auto', top: '36px', right: '36px', bottom: 'auto', transform: 'none' },
    bottom_left: { left: '36px', top: 'auto', right: 'auto', bottom: '96px', transform: 'none' },
    bottom_center: { left: '50%', top: 'auto', right: 'auto', bottom: '96px', transform: 'translateX(-50%)' },
    bottom_right: { left: 'auto', top: 'auto', right: '36px', bottom: '96px', transform: 'none' },
  }

  return { ...base, ...presets[item.position as Exclude<OverlayPosition, 'custom'>] }
}

const moveableElementGuidelines = computed(() => {
  const blurElements = Object.entries(blurTargetRefs.value)
    .filter(([id, element]) => id !== selectedBlurId.value && Boolean(element))
    .map(([, element]) => element as HTMLElement)
  const overlayElements = Object.entries(overlayTargetRefs.value)
    .filter(([id, element]) => id !== selectedOverlayId.value && Boolean(element))
    .map(([, element]) => element as HTMLElement)
  return [...blurElements, ...overlayElements]
})

const activeBlurStrength = computed({
  get: () => selectedBlurItem.value?.strength ?? 11,
  set: (value: number) => {
    if (!selectedBlurItem.value) {
      return
    }
    selectedBlurItem.value.strength = value
  },
})

const activeOverlayText = computed({
  get: () => selectedOverlayItem.value?.text ?? '',
  set: (value: string) => {
    if (!selectedOverlayItem.value) {
      return
    }
    selectedOverlayItem.value.text = value
  },
})

const activeOverlayFontSize = computed({
  get: () => selectedOverlayItem.value?.font_size ?? 18,
  set: (value: number) => {
    if (!selectedOverlayItem.value) {
      return
    }
    selectedOverlayItem.value.font_size = value
  },
})

const activeOverlayTextColor = computed({
  get: () => selectedOverlayItem.value?.text_color ?? '#FFFFFF',
  set: (value: string) => {
    if (!selectedOverlayItem.value) {
      return
    }
    selectedOverlayItem.value.text_color = value
  },
})

async function loadEditorWorkspace() {
  isLoading.value = true
  try {
    errorMessage.value = ''
    successMessage.value = ''
    renderStatusMessage.value = ''
    const [jobResponse, editorState, editDetail] = await Promise.all([
      getJob(jobId.value),
      getJobEditorState(jobId.value),
      editId.value ? getJobEditDetail(jobId.value, editId.value) : Promise.resolve(null),
    ])
    job.value = jobResponse
    const defaultSegments = editorState.subtitle_segments.map((segment) => ({ ...segment }))
    const generatedConfig = normalizeEditorConfig(editorState.render_config, defaultSegments)

    if (editDetail) {
      const savedConfig = normalizeEditorConfig(editDetail.config, defaultSegments)
      setEditorRefsFromConfig(savedConfig)
      baselineConfig.value = cloneEditorConfig(savedConfig)
      editedResultUrl.value = editDetail.render_status === 'completed' && editDetail.result_url
        ? resolveApiAssetUrl(`${editDetail.result_url}?t=${Date.now()}`)
        : ''
      if (editDetail.render_status === 'queued' || editDetail.render_status === 'processing') {
        renderStatusMessage.value = 'Edited video is rendering...'
        void pollRenderedEdit(editDetail.edit_id).catch((error) => {
          renderStatusMessage.value = ''
          errorMessage.value = error instanceof Error ? error.message : 'Could not render edited video.'
        })
      } else if (editDetail.render_status === 'failed') {
        renderStatusMessage.value = ''
        errorMessage.value = editDetail.error_message || 'Could not render edited video.'
      } else {
        renderStatusMessage.value = ''
      }
    } else {
      setEditorRefsFromConfig(generatedConfig)
      baselineConfig.value = cloneEditorConfig(generatedConfig)
      editedResultUrl.value = ''
    }
    await nextTick()
    updatePreviewMetrics()
    syncPreviewState()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not load editor workspace.'
  } finally {
    isLoading.value = false
  }
}

async function renderEdit() {
  if (!hasPendingChanges.value) {
    return
  }

  errorMessage.value = ''
  successMessage.value = ''
  renderStatusMessage.value = ''
  isRendering.value = true
  try {
    const payload = cloneEditorConfig(currentConfig.value)
    const response = await renderEditedVideo(jobId.value, payload, {
      overwriteEditId: editorSource.value === 'history' ? editId.value || null : null,
    })
    void router.replace({
      name: 'editor-job',
      params: { jobId: jobId.value },
      query: {
        edit: response.edit_id,
        source: editorSource.value,
      },
    })
    renderStatusMessage.value = 'Edited video is rendering...'
    await pollRenderedEdit(response.edit_id, payload)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not render edited video.'
  } finally {
    isRendering.value = false
  }
}

async function pollRenderedEdit(editIdToWatch: string, expectedConfig?: EditorConfig) {
  const startedAt = Date.now()
  const timeoutMs = 5 * 60 * 1000
  const intervalMs = 2500

  while (Date.now() - startedAt < timeoutMs) {
    const detail = await getJobEditDetail(jobId.value, editIdToWatch)
    if (detail.render_status === 'completed' && detail.result_url) {
      renderStatusMessage.value = ''
      successMessage.value = 'Edited video rendered.'
      editedResultUrl.value = resolveApiAssetUrl(`${detail.result_url}?t=${Date.now()}`)
      if (expectedConfig) {
        baselineConfig.value = cloneEditorConfig(expectedConfig)
      }
      return
    }
    if (detail.render_status === 'failed') {
      renderStatusMessage.value = ''
      throw new Error(detail.error_message || 'Could not render edited video.')
    }
    await delay(intervalMs)
  }

  renderStatusMessage.value = ''
  throw new Error('Timed out while waiting for edited video render.')
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function setTrimEndFromEvent(event: Event) {
  const target = event.target as HTMLInputElement | null
  trimEndSeconds.value = target?.value ? Number(target.value) : null
}

function updateSubtitleText(index: number, value: string) {
  subtitleSegments.value[index] = {
    ...subtitleSegments.value[index],
    text_vi: value,
  }
}

function updateSubtitleStart(index: number, value: string) {
  subtitleSegments.value[index] = {
    ...subtitleSegments.value[index],
    start: Number(value || 0),
  }
}

function updateSubtitleEnd(index: number, value: string) {
  subtitleSegments.value[index] = {
    ...subtitleSegments.value[index],
    end: Number(value || 0),
  }
}

function formatSegmentTime(value: number) {
  return `${value.toFixed(2)}s`
}

function selectSubtitlePosition(value: SubtitlePosition) {
  subtitlePosition.value = value
  isSubtitlePositionMenuOpen.value = false
}

function openVideoTool(tool: 'trim' | 'blur' | 'overlay') {
  isToolbarOpen.value = true
  activeGroup.value = 'video'
  activeVideoTool.value = tool
  selectedPreviewTool.value = tool === 'trim' ? '' : tool
}

function activatePreviewTool(tool: 'blur' | 'overlay', id?: string) {
  isToolbarOpen.value = true
  activeGroup.value = 'video'
  activeVideoTool.value = tool
  selectedPreviewTool.value = tool
  if (tool === 'blur' && id) {
    selectedBlurId.value = id
  }
  if (tool === 'overlay' && id) {
    selectedOverlayId.value = id
  }
}

function clearPreviewSelection() {
  selectedPreviewTool.value = ''
  blurMoveableRef.value?.updateRect()
  overlayMoveableRef.value?.updateRect()
}

function clearPendingChanges() {
  if (!baselineConfig.value) {
    return
  }
  setEditorRefsFromConfig(cloneEditorConfig(baselineConfig.value))
}

function addBlurMask() {
  const item: BlurMaskItem = {
    id: createEditorItemId('blur'),
    enabled: true,
    x_ratio: 0,
    y_ratio: 0.78,
    width_ratio: 1,
    height_ratio: 0.22,
    strength: 11,
  }
  blurMasks.value = [...blurMasks.value, item]
  selectedBlurId.value = item.id
  activatePreviewTool('blur', item.id)
}

function removeBlurMask(id: string) {
  blurMasks.value = blurMasks.value.filter((item) => item.id !== id)
  delete blurTargetRefs.value[id]
  if (selectedBlurId.value === id) {
    selectedBlurId.value = blurMasks.value[0]?.id || ''
  }
}

function addOverlayItem() {
  const item: OverlayItem = {
    id: createEditorItemId('overlay'),
    enabled: true,
    text: '',
    position: 'top_right',
    x_ratio: 0,
    y_ratio: 0,
    font_size: 18,
    text_color: '#FFFFFF',
  }
  overlays.value = [...overlays.value, item]
  selectedOverlayId.value = item.id
  activatePreviewTool('overlay', item.id)
}

function removeOverlayItem(id: string) {
  overlays.value = overlays.value.filter((item) => item.id !== id)
  delete overlayTargetRefs.value[id]
  if (selectedOverlayId.value === id) {
    selectedOverlayId.value = overlays.value[0]?.id || ''
  }
}

function getBlurLabel(item: BlurMaskItem) {
  return `Blur ${blurMasks.value.findIndex((entry) => entry.id === item.id) + 1}`
}

function getOverlayLabel(item: OverlayItem) {
  const fallback = `Overlay ${overlays.value.findIndex((entry) => entry.id === item.id) + 1}`
  return item.text?.trim() ? item.text.slice(0, 18) : fallback
}

function setBlurTargetRef(id: string, element: Element | ComponentPublicInstance | null) {
  blurTargetRefs.value[id] = element instanceof HTMLElement ? element : null
}

function setOverlayTargetRef(id: string, element: Element | ComponentPublicInstance | null) {
  overlayTargetRefs.value[id] = element instanceof HTMLElement ? element : null
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function updatePreviewMetrics() {
  if (!previewFrameRef.value) {
    previewWidth.value = 0
    previewHeight.value = 0
    return
  }
  const rect = previewFrameRef.value.getBoundingClientRect()
  previewWidth.value = rect.width
  previewHeight.value = rect.height
  blurMoveableRef.value?.updateRect()
  overlayMoveableRef.value?.updateRect()
}

function syncPreviewState() {
  if (!previewVideoRef.value) {
    if (previewAnimationFrame) {
      cancelAnimationFrame(previewAnimationFrame)
      previewAnimationFrame = 0
    }
    previewDuration.value = 0
    previewCurrentTime.value = 0
    previewPlaying.value = false
    previewMuted.value = false
    return
  }

  const video = previewVideoRef.value
  previewDuration.value = Number.isFinite(video.duration) ? video.duration : 0
  previewCurrentTime.value = video.currentTime || 0
  previewPlaying.value = !video.paused && !video.ended
  previewMuted.value = video.muted || video.volume === 0
  if (previewPlaying.value && !previewAnimationFrame) {
    startPreviewTicker()
  } else if (!previewPlaying.value && previewAnimationFrame) {
    cancelAnimationFrame(previewAnimationFrame)
    previewAnimationFrame = 0
  }
}

function startPreviewTicker() {
  const tick = () => {
    if (!previewVideoRef.value) {
      previewAnimationFrame = 0
      return
    }
    previewCurrentTime.value = previewVideoRef.value.currentTime || 0
    previewDuration.value = Number.isFinite(previewVideoRef.value.duration) ? previewVideoRef.value.duration : 0
    previewPlaying.value = !previewVideoRef.value.paused && !previewVideoRef.value.ended
    if (!previewPlaying.value) {
      previewAnimationFrame = 0
      return
    }
    previewAnimationFrame = requestAnimationFrame(tick)
  }
  previewAnimationFrame = requestAnimationFrame(tick)
}

function togglePreviewPlayback() {
  const video = previewVideoRef.value
  if (!video) {
    return
  }
  if (video.paused || video.ended) {
    void video.play()
  } else {
    video.pause()
  }
}

function togglePreviewMute() {
  const video = previewVideoRef.value
  if (!video) {
    return
  }
  video.muted = !video.muted
  syncPreviewState()
}

function seekPreview(event: Event) {
  const video = previewVideoRef.value
  const target = event.target as HTMLInputElement | null
  if (!video || !target) {
    return
  }
  video.currentTime = Number(target.value || 0)
  syncPreviewState()
}

function formatPreviewTime(value: number) {
  const safe = Math.max(0, Math.floor(value))
  const minutes = Math.floor(safe / 60)
  const seconds = safe % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function onBlurDrag(event: { left: number; top: number }) {
  if (!previewWidth.value || !previewHeight.value || !selectedBlurItem.value) {
    return
  }
  selectedBlurItem.value.x_ratio = clamp(event.left / previewWidth.value, 0, 1 - selectedBlurItem.value.width_ratio)
  selectedBlurItem.value.y_ratio = clamp(event.top / previewHeight.value, 0, 1 - selectedBlurItem.value.height_ratio)
  if (selectedBlurTargetRef.value) {
    selectedBlurTargetRef.value.style.left = `${selectedBlurItem.value.x_ratio * previewWidth.value}px`
    selectedBlurTargetRef.value.style.top = `${selectedBlurItem.value.y_ratio * previewHeight.value}px`
  }
}

function onBlurResize(event: { width: number; height: number; drag: { beforeTranslate: number[] } }) {
  if (!previewWidth.value || !previewHeight.value || !selectedBlurItem.value) {
    return
  }
  const [left, top] = event.drag.beforeTranslate
  const nextWidthRatio = clamp(event.width / previewWidth.value, 0.05, 1)
  const nextHeightRatio = clamp(event.height / previewHeight.value, 0.05, 1)
  const nextXRatio = clamp(left / previewWidth.value, 0, 1 - nextWidthRatio)
  const nextYRatio = clamp(top / previewHeight.value, 0, 1 - nextHeightRatio)

  selectedBlurItem.value.x_ratio = nextXRatio
  selectedBlurItem.value.y_ratio = nextYRatio
  selectedBlurItem.value.width_ratio = clamp(nextWidthRatio, 0.05, 1 - nextXRatio)
  selectedBlurItem.value.height_ratio = clamp(nextHeightRatio, 0.05, 1 - nextYRatio)
  if (selectedBlurTargetRef.value) {
    selectedBlurTargetRef.value.style.left = `${selectedBlurItem.value.x_ratio * previewWidth.value}px`
    selectedBlurTargetRef.value.style.top = `${selectedBlurItem.value.y_ratio * previewHeight.value}px`
    selectedBlurTargetRef.value.style.width = `${selectedBlurItem.value.width_ratio * previewWidth.value}px`
    selectedBlurTargetRef.value.style.height = `${selectedBlurItem.value.height_ratio * previewHeight.value}px`
  }
}

function onOverlayDragStart() {
  if (selectedOverlayItem.value?.position !== 'custom') {
    syncOverlayPresetToCustom()
  }
}

function onOverlayDrag(event: { left: number; top: number }) {
  if (!previewWidth.value || !previewHeight.value || !selectedOverlayItem.value) {
    return
  }
  selectedOverlayItem.value.position = 'custom'
  selectedOverlayItem.value.x_ratio = clamp(event.left / previewWidth.value, 0, 1)
  selectedOverlayItem.value.y_ratio = clamp(event.top / previewHeight.value, 0, 1)
  if (selectedOverlayTargetRef.value) {
    selectedOverlayTargetRef.value.style.left = `${selectedOverlayItem.value.x_ratio * previewWidth.value}px`
    selectedOverlayTargetRef.value.style.top = `${selectedOverlayItem.value.y_ratio * previewHeight.value}px`
    selectedOverlayTargetRef.value.style.right = 'auto'
    selectedOverlayTargetRef.value.style.bottom = 'auto'
    selectedOverlayTargetRef.value.style.transform = 'none'
  }
}

function onOverlayResizeStart() {
  if (selectedOverlayItem.value?.position !== 'custom') {
    syncOverlayPresetToCustom()
  }
}

function onOverlayResize(event: { width: number; height: number; drag: { beforeTranslate: number[] } }) {
  if (!previewWidth.value || !previewHeight.value || !selectedOverlayItem.value) {
    return
  }

  const [left, top] = event.drag.beforeTranslate
  selectedOverlayItem.value.position = 'custom'
  selectedOverlayItem.value.x_ratio = clamp(left / previewWidth.value, 0, 0.95)
  selectedOverlayItem.value.y_ratio = clamp(top / previewHeight.value, 0, 0.95)
  selectedOverlayItem.value.font_size = clamp(Math.round(event.height * 0.62), 14, 72)

  if (selectedOverlayTargetRef.value) {
    selectedOverlayTargetRef.value.style.left = `${selectedOverlayItem.value.x_ratio * previewWidth.value}px`
    selectedOverlayTargetRef.value.style.top = `${selectedOverlayItem.value.y_ratio * previewHeight.value}px`
    selectedOverlayTargetRef.value.style.right = 'auto'
    selectedOverlayTargetRef.value.style.bottom = 'auto'
    selectedOverlayTargetRef.value.style.transform = 'none'
    selectedOverlayTargetRef.value.style.fontSize = `${selectedOverlayItem.value.font_size}px`
  }
}

function syncOverlayPresetToCustom() {
  if (!selectedOverlayItem.value) {
    return
  }
  const presetRatios: Record<Exclude<OverlayPosition, 'custom'>, { x: number; y: number }> = {
    top_left: { x: 0.03, y: 0.04 },
    top_center: { x: 0.5, y: 0.04 },
    top_right: { x: 0.82, y: 0.04 },
    bottom_left: { x: 0.03, y: 0.8 },
    bottom_center: { x: 0.5, y: 0.8 },
    bottom_right: { x: 0.82, y: 0.8 },
  }
  const preset = presetRatios[selectedOverlayItem.value.position as Exclude<OverlayPosition, 'custom'>]
  if (!preset) {
    return
  }
  selectedOverlayItem.value.x_ratio = preset.x
  selectedOverlayItem.value.y_ratio = preset.y
  selectedOverlayItem.value.position = 'custom'
}

function setEditorRefsFromConfig(config: EditorConfig) {
  trimStartSeconds.value = config.trim_start_seconds
  trimEndSeconds.value = config.trim_end_seconds
  playbackSpeed.value = config.playback_speed
  blurMasks.value = (config.blur_masks ?? []).map((item) => ({ ...item }))
  selectedBlurId.value = blurMasks.value[0]?.id || ''
  voiceVolumePercent.value = config.voice_volume_percent
  originalVolumePercent.value = config.original_volume_percent
  burnAudio.value = config.burn_audio
  burnOriginalAudio.value = config.burn_original_audio
  burnSubtitle.value = config.burn_subtitle
  subtitleFontSize.value = config.subtitle_font_size
  subtitlePosition.value = config.subtitle_position
  subtitleTextColor.value = config.subtitle_text_color
  overlays.value = (config.overlays ?? []).map((item) => ({ ...item }))
  selectedOverlayId.value = overlays.value[0]?.id || ''
  subtitleSegments.value = config.subtitle_segments.map((segment) => ({ ...segment }))
}

function normalizeEditorConfig(config: Record<string, unknown>, defaultSegments: JobSubtitleSegment[]): EditorConfig {
  const normalizedBlurMasks = asBlurMasks(
    config.blur_masks,
    asBoolean(config.blur_original_subtitles, false)
      ? [
          {
            id: createEditorItemId('blur'),
            enabled: true,
            x_ratio: asNumber(config.blur_x_ratio, 0),
            y_ratio: asNumber(config.blur_y_ratio, 0.78),
            width_ratio: asNumber(config.blur_width_ratio, 1),
            height_ratio: asNumber(config.blur_height_ratio, 0.22),
            strength: Math.min(asNumber(config.blur_strength, 11), 11),
          },
        ]
      : [],
  )
  const normalizedOverlays = asOverlays(
    config.overlays,
    asBoolean(config.overlay_enabled, false) && asString(config.overlay_text, '').trim()
      ? [
          {
            id: createEditorItemId('overlay'),
            enabled: true,
            text: asString(config.overlay_text, ''),
            position: asOverlayPosition(config.overlay_position, 'top_right'),
            x_ratio: asNumber(config.overlay_x_ratio, 0),
            y_ratio: asNumber(config.overlay_y_ratio, 0),
            font_size: asNumber(config.overlay_font_size, 18),
            text_color: asColor(config.overlay_text_color, '#FFFFFF'),
          },
        ]
      : [],
  )

  return {
    trim_start_seconds: asNumber(config.trim_start_seconds, 0),
    trim_end_seconds: asNullableNumber(config.trim_end_seconds),
    playback_speed: asNumber(config.playback_speed, 1),
    blur_original_subtitles: normalizedBlurMasks.some((item) => item.enabled),
    blur_x_ratio: normalizedBlurMasks[0]?.x_ratio ?? 0,
    blur_y_ratio: normalizedBlurMasks[0]?.y_ratio ?? 0.78,
    blur_width_ratio: normalizedBlurMasks[0]?.width_ratio ?? 1,
    blur_height_ratio: normalizedBlurMasks[0]?.height_ratio ?? 0.22,
    blur_strength: normalizedBlurMasks[0]?.strength ?? 11,
    blur_masks: normalizedBlurMasks,
    voice_volume_percent: asNumber(config.voice_volume_percent, 100),
    original_volume_percent: asNumber(config.original_volume_percent, 35),
    burn_audio: asBoolean(config.burn_audio, true),
    burn_original_audio: asBoolean(config.burn_original_audio, true),
    burn_subtitle: asBoolean(config.burn_subtitle, true),
    subtitle_font_size: asNumber(config.subtitle_font_size, 18),
    subtitle_position: asSubtitlePosition(config.subtitle_position, 'bottom'),
    subtitle_text_color: asColor(config.subtitle_text_color, '#FFFFFF'),
    subtitle_segments: asSubtitleSegments(config.subtitle_segments, defaultSegments),
    overlay_enabled: normalizedOverlays.some((item) => item.enabled && item.text.trim()),
    overlay_text: normalizedOverlays[0]?.text ?? '',
    overlay_position: normalizedOverlays[0]?.position ?? 'top_right',
    overlay_x_ratio: normalizedOverlays[0]?.x_ratio ?? 0,
    overlay_y_ratio: normalizedOverlays[0]?.y_ratio ?? 0,
    overlay_font_size: normalizedOverlays[0]?.font_size ?? 18,
    overlay_text_color: normalizedOverlays[0]?.text_color ?? '#FFFFFF',
    overlays: normalizedOverlays,
  }
}

function cloneEditorConfig(config: EditorConfig): EditorConfig {
  return {
    ...config,
    blur_masks: (config.blur_masks ?? []).map((item) => ({ ...item })),
    subtitle_segments: config.subtitle_segments.map((segment) => ({ ...segment })),
    overlays: (config.overlays ?? []).map((item) => ({ ...item })),
  }
}

function emptySummary(): ChangeSummary {
  return {
    total: 0,
    groups: {
      video: [],
      audio: [],
      captions: [],
    },
    tools: {
      trim: [],
      blur: [],
      overlay: [],
      audio: [],
      style: [],
      editor: [],
    },
  }
}

function buildChangeSummary(baseline: EditorConfig, current: EditorConfig): ChangeSummary {
  const summary = emptySummary()
  if (
    hasAnyChanged(
      [baseline.trim_start_seconds, baseline.trim_end_seconds, baseline.playback_speed],
      [current.trim_start_seconds, current.trim_end_seconds, current.playback_speed],
    )
  ) {
    summary.tools.trim.push('Trim/Speed')
  }

  if (
    hasAnyChanged(
      [
        JSON.stringify(baseline.blur_masks),
      ],
      [
        JSON.stringify(current.blur_masks),
      ],
    )
  ) {
    summary.tools.blur.push('Blur/Mask')
  }

  if (
    hasAnyChanged(
      [
        JSON.stringify(baseline.overlays),
      ],
      [
        JSON.stringify(current.overlays),
      ],
    )
  ) {
    summary.tools.overlay.push('Overlay')
  }

  if (
    hasAnyChanged(
      [
        baseline.burn_subtitle,
        baseline.subtitle_font_size,
        baseline.subtitle_position,
        baseline.subtitle_text_color,
      ],
      [
        current.burn_subtitle,
        current.subtitle_font_size,
        current.subtitle_position,
        current.subtitle_text_color,
      ],
    )
  ) {
    summary.tools.style.push('Style/Position')
  }

  if (
    hasAnyChanged(
      [
        baseline.voice_volume_percent,
        baseline.original_volume_percent,
        baseline.burn_audio,
        baseline.burn_original_audio,
      ],
      [
        current.voice_volume_percent,
        current.original_volume_percent,
        current.burn_audio,
        current.burn_original_audio,
      ],
    )
  ) {
    summary.tools.audio.push('Voice mix')
  }

  const subtitleTextChanges = countSubtitleTextChanges(baseline.subtitle_segments, current.subtitle_segments)
  if (subtitleTextChanges > 0) {
    summary.tools.editor.push('Subtitle editor')
  }

  const subtitleTimingChanges = countSubtitleTimingChanges(baseline.subtitle_segments, current.subtitle_segments)
  if (subtitleTimingChanges > 0 && !summary.tools.editor.includes('Subtitle editor')) {
    summary.tools.editor.push('Subtitle editor')
  }

  summary.groups.video = [
    ...summary.tools.trim,
    ...summary.tools.blur,
    ...summary.tools.overlay,
  ]
  summary.groups.audio = [...summary.tools.audio]
  summary.groups.captions = [
    ...summary.tools.style,
    ...summary.tools.editor,
  ]
  summary.total =
    summary.groups.video.length +
    summary.groups.audio.length +
    summary.groups.captions.length
  return summary
}

function hasAnyChanged(baseline: unknown[], current: unknown[]) {
  return baseline.some((value, index) => !isEqual(value, current[index]))
}

function countSubtitleTextChanges(baseline: JobSubtitleSegment[], current: JobSubtitleSegment[]) {
  let count = 0
  const maxLength = Math.max(baseline.length, current.length)
  for (let index = 0; index < maxLength; index += 1) {
    const left = baseline[index]
    const right = current[index]
    if (!left || !right || left.text_vi.trim() !== right.text_vi.trim()) {
      count += 1
    }
  }
  return count
}

function countSubtitleTimingChanges(baseline: JobSubtitleSegment[], current: JobSubtitleSegment[]) {
  let count = 0
  const maxLength = Math.max(baseline.length, current.length)
  for (let index = 0; index < maxLength; index += 1) {
    const left = baseline[index]
    const right = current[index]
    if (!left || !right || !isEqual(left.start, right.start) || !isEqual(left.end, right.end)) {
      count += 1
    }
  }
  return count
}

function isEqual(left: unknown, right: unknown) {
  if (typeof left === 'number' && typeof right === 'number') {
    return Math.abs(left - right) < 0.0001
  }
  return left === right
}

function asNumber(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asNullableNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function asBoolean(value: unknown, fallback: boolean) {
  return typeof value === 'boolean' ? value : fallback
}

function asString(value: unknown, fallback: string) {
  return typeof value === 'string' ? value : fallback
}

function asColor(value: unknown, fallback: string) {
  return typeof value === 'string' && /^#[0-9A-Fa-f]{6}$/.test(value) ? value.toUpperCase() : fallback
}

function asOverlayPosition(value: unknown, fallback: OverlayPosition): OverlayPosition {
  return (
    ['top_left', 'top_center', 'top_right', 'bottom_left', 'bottom_center', 'bottom_right', 'custom'] as const
  ).includes(value as OverlayPosition)
    ? (value as OverlayPosition)
    : fallback
}

function asSubtitlePosition(value: unknown, fallback: SubtitlePosition): SubtitlePosition {
  return subtitlePositionOptions.some((option) => option.value === value) ? (value as SubtitlePosition) : fallback
}

function asSubtitleSegments(value: unknown, fallback: JobSubtitleSegment[]): JobSubtitleSegment[] {
  if (!Array.isArray(value)) {
    return fallback.map((segment) => ({ ...segment }))
  }

  const normalized: JobSubtitleSegment[] = []
  for (const item of value) {
    const parsed = parseSubtitleSegment(item)
    if (parsed) {
      normalized.push(parsed)
    }
  }

  return normalized.length ? normalized : fallback.map((segment) => ({ ...segment }))
}

function asBlurMasks(value: unknown, fallback: BlurMaskItem[]): BlurMaskItem[] {
  if (!Array.isArray(value)) {
    return fallback.map((item) => ({ ...item }))
  }

  const normalized: BlurMaskItem[] = []
  for (const item of value) {
    if (!item || typeof item !== 'object') {
      continue
    }
    const candidate = item as Partial<BlurMaskItem>
    if (typeof candidate.id !== 'string') {
      continue
    }
    normalized.push({
      id: candidate.id,
      enabled: typeof candidate.enabled === 'boolean' ? candidate.enabled : true,
      x_ratio: asNumber(candidate.x_ratio, 0),
      y_ratio: asNumber(candidate.y_ratio, 0.78),
      width_ratio: asNumber(candidate.width_ratio, 1),
      height_ratio: asNumber(candidate.height_ratio, 0.22),
      strength: Math.min(asNumber(candidate.strength, 11), 11),
    })
  }
  return normalized.length ? normalized : fallback.map((item) => ({ ...item }))
}

function asOverlays(value: unknown, fallback: OverlayItem[]): OverlayItem[] {
  if (!Array.isArray(value)) {
    return fallback.map((item) => ({ ...item }))
  }

  const normalized: OverlayItem[] = []
  for (const item of value) {
    if (!item || typeof item !== 'object') {
      continue
    }
    const candidate = item as Partial<OverlayItem>
    if (typeof candidate.id !== 'string') {
      continue
    }
    normalized.push({
      id: candidate.id,
      enabled: typeof candidate.enabled === 'boolean' ? candidate.enabled : true,
      text: asString(candidate.text, ''),
      position: asOverlayPosition(candidate.position, 'top_right'),
      x_ratio: asNumber(candidate.x_ratio, 0),
      y_ratio: asNumber(candidate.y_ratio, 0),
      font_size: asNumber(candidate.font_size, 18),
      text_color: asColor(candidate.text_color, '#FFFFFF'),
    })
  }
  return normalized.length ? normalized : fallback.map((item) => ({ ...item }))
}

function parseSubtitleSegment(value: unknown): JobSubtitleSegment | null {
  if (!value || typeof value !== "object") {
    return null
  }

  const candidate = value as Partial<JobSubtitleSegment>
  if (
    typeof candidate.id !== 'number' ||
    typeof candidate.start !== 'number' ||
    typeof candidate.end !== 'number' ||
    typeof candidate.text_vi !== 'string'
  ) {
    return null
  }

  return {
    id: candidate.id,
    start: candidate.start,
    end: candidate.end,
    text_vi: candidate.text_vi,
    text_zh: typeof candidate.text_zh === 'string' ? candidate.text_zh : null,
  }
}

onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') {
    previewResizeObserver = new ResizeObserver(() => {
      updatePreviewMetrics()
    })
  }
  loadEditorWorkspace()
})
watch(() => route.fullPath, loadEditorWorkspace)
watch(previewFrameRef, (next, previous) => {
  if (previous && previewResizeObserver) {
    previewResizeObserver.unobserve(previous)
  }
  if (next) {
    previewResizeObserver?.observe(next)
    nextTick(() => updatePreviewMetrics())
  }
})
watch([showBlurMoveable, showOverlayMoveable, previewWidth, previewHeight], async () => {
  await nextTick()
  blurMoveableRef.value?.updateRect()
  overlayMoveableRef.value?.updateRect()
})
onBeforeUnmount(() => {
  if (previewAnimationFrame) {
    cancelAnimationFrame(previewAnimationFrame)
  }
  previewResizeObserver?.disconnect()
})
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <RouterLink class="back-link" :to="backTarget">
          <ArrowLeft :size="18" :stroke-width="2.3" aria-hidden="true" />
          {{ backLabel }}
        </RouterLink>
        <p class="eyebrow">Editor</p>
        <h1>{{ jobId }}</h1>
        <p>Preview the generated video and render an edited copy with video, audio, subtitle, and overlay updates.</p>
      </div>
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-else-if="renderStatusMessage" class="success-message">{{ renderStatusMessage }}</p>
    <p v-else-if="successMessage" class="success-message">{{ successMessage }}</p>
    <p v-if="isLoading" class="empty-state large-empty-state">Loading editor workspace...</p>

    <div class="editor-workspace" v-else-if="job">
      <section class="surface editor-preview-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Preview</p>
            <h2>Live preview</h2>
          </div>
        </div>

        <div v-if="previewUrl" class="editor-preview-stack">
          <div ref="previewFrameRef" class="video-preview editor-preview-frame">
            <video
              ref="previewVideoRef"
              :key="previewUrl"
              :src="previewUrl"
              preload="metadata"
              @loadedmetadata="syncPreviewState"
              @timeupdate="syncPreviewState"
              @play="syncPreviewState"
              @pause="syncPreviewState"
              @volumechange="syncPreviewState"
              @ended="syncPreviewState"
            />
            <div
              :class="['editor-preview-overlay', { 'editor-preview-overlay-editing': showBlurMoveable || showOverlayMoveable }]"
              aria-hidden="true"
            >
              <div
                v-for="item in blurMasks.filter((entry) => entry.enabled)"
                :key="item.id"
                class="editor-preview-blur-box"
                :class="{ 'editor-preview-item-selected': selectedBlurId === item.id && selectedPreviewTool === 'blur' }"
                :style="blurBoxStyle(item)"
                role="button"
                tabindex="0"
                :ref="(el) => setBlurTargetRef(item.id, el)"
                @click.stop="activatePreviewTool('blur', item.id)"
              >
                <span class="editor-preview-box-label">Blur {{ blurMasks.findIndex((entry) => entry.id === item.id) + 1 }}</span>
              </div>

              <div
                v-for="item in overlays.filter((entry) => entry.enabled && entry.text.trim())"
                :key="item.id"
                class="editor-preview-overlay-text"
                :class="{ 'editor-preview-item-selected': selectedOverlayId === item.id && selectedPreviewTool === 'overlay' }"
                :style="overlayPreviewStyle(item)"
                role="button"
                tabindex="0"
                :ref="(el) => setOverlayTargetRef(item.id, el)"
                @click.stop="activatePreviewTool('overlay', item.id)"
              >
                {{ item.text || 'Overlay text' }}
              </div>
            </div>
            <div class="editor-preview-controls">
              <div class="editor-preview-controls-top">
                <button class="editor-preview-control-button" type="button" @click="togglePreviewPlayback">
                  <Pause v-if="previewPlaying" :size="16" :stroke-width="2.2" aria-hidden="true" />
                  <Play v-else :size="16" :stroke-width="2.2" aria-hidden="true" />
                </button>

                <button class="editor-preview-control-button" type="button" @click="togglePreviewMute">
                  <VolumeX v-if="previewMuted" :size="16" :stroke-width="2.2" aria-hidden="true" />
                  <Volume2 v-else :size="16" :stroke-width="2.2" aria-hidden="true" />
                </button>

                <div class="editor-preview-timecode">
                  <span>{{ formatPreviewTime(previewCurrentTime) }}</span>
                  <span>/</span>
                  <span>{{ formatPreviewTime(previewDuration) }}</span>
                </div>
              </div>

              <div class="editor-preview-timeline">
                <input
                  :max="previewDuration || 0"
                  :value="previewCurrentTime"
                  type="range"
                  min="0"
                  step="0.1"
                  @input="seekPreview"
                />
              </div>
            </div>
            <Moveable
              v-if="showBlurMoveable && selectedBlurTargetRef"
              ref="blurMoveableRef"
              :target="selectedBlurTargetRef"
              :container="previewFrameRef"
              :root-container="previewFrameRef"
              :origin="false"
              :draggable="true"
              :resizable="true"
              :keep-ratio="false"
              :snappable="true"
              :snap-center="true"
              :snap-gap="true"
              :element-guidelines="moveableElementGuidelines"
              :vertical-guidelines="[0, previewWidth / 2, previewWidth]"
              :horizontal-guidelines="[0, previewHeight / 2, previewHeight]"
              :bounds="moveableBounds"
              :render-directions="['nw', 'ne', 'sw', 'se']"
              :throttle-drag="0"
              :throttle-resize="0"
              @drag="onBlurDrag"
              @resize="onBlurResize"
            />
            <Moveable
              v-if="showOverlayMoveable && selectedOverlayTargetRef"
              ref="overlayMoveableRef"
              :target="selectedOverlayTargetRef"
              :container="previewFrameRef"
              :root-container="previewFrameRef"
              :origin="false"
              :draggable="true"
              :resizable="true"
              :keep-ratio="true"
              :snappable="true"
              :snap-center="true"
              :snap-gap="true"
              :element-guidelines="moveableElementGuidelines"
              :vertical-guidelines="[0, previewWidth / 2, previewWidth]"
              :horizontal-guidelines="[0, previewHeight / 2, previewHeight]"
              :bounds="moveableBounds"
              :render-directions="['nw', 'ne', 'sw', 'se']"
              :throttle-drag="0"
              :throttle-resize="0"
              @drag-start="onOverlayDragStart"
              @drag="onOverlayDrag"
              @resize-start="onOverlayResizeStart"
              @resize="onOverlayResize"
            />
          </div>
        </div>
        <p v-else class="empty-state large-empty-state">
          This job does not have a downloadable video yet.
        </p>
      </section>

      <div v-if="!isToolbarOpen" class="editor-tool-launcher-shell">
        <button
          class="editor-tool-launcher"
          type="button"
          aria-label="Open edit tools"
          title="Open tools"
          @click="openVideoTool(selectedPreviewTool || 'trim')"
        >
          <ArrowUp :size="24" :stroke-width="2.3" aria-hidden="true" />
          <small v-if="hasPendingChanges" class="editor-tool-badge editor-tool-launcher-badge">{{ dirtySummary.total }}</small>
        </button>
      </div>

      <section v-else class="editor-tool-drawer">
        <div v-if="isVideoGroupOpen" class="editor-tool-panel">
          <div class="editor-tool-panel-heading">
            <div>
              <p class="eyebrow">Video tools</p>
              <h2>{{ activeVideoTool === 'blur' ? 'Blur/Mask' : activeVideoTool === 'trim' ? 'Trim/Speed' : 'Overlay' }}</h2>
            </div>
          </div>

          <div class="editor-tool-tabs" aria-label="Video tool options">
            <button
              :class="['editor-tool-tab', { 'editor-tool-tab-active': activeVideoTool === 'trim' }]"
              type="button"
              @click="openVideoTool('trim')"
            >
              <span>Trim/Speed</span>
              <small v-if="dirtySummary.tools.trim.length" class="editor-inline-badge">{{ dirtySummary.tools.trim.length }}</small>
            </button>
            <button
              :class="['editor-tool-tab', { 'editor-tool-tab-active': activeVideoTool === 'overlay' }]"
              type="button"
              @click="openVideoTool('overlay')"
            >
              <span>Overlay</span>
              <small v-if="dirtySummary.tools.overlay.length" class="editor-inline-badge">{{ dirtySummary.tools.overlay.length }}</small>
            </button>
            <button
              :class="['editor-tool-tab', { 'editor-tool-tab-active': activeVideoTool === 'blur' }]"
              type="button"
              @click="openVideoTool('blur')"
            >
              <span>Blur/Mask</span>
              <small v-if="dirtySummary.tools.blur.length" class="editor-inline-badge">{{ dirtySummary.tools.blur.length }}</small>
            </button>
          </div>

          <div v-if="activeVideoTool === 'trim'" class="editor-controls">
            <EditorField label="Trim start" :value="`${trimStartSeconds.toFixed(1)}s`">
              <input v-model.number="trimStartSeconds" type="number" min="0" max="180" step="0.5" />
            </EditorField>

            <EditorField label="Trim end" :value="trimEndSeconds === null ? 'End' : `${trimEndSeconds.toFixed(1)}s`">
              <input
                :value="trimEndSeconds ?? ''"
                type="number"
                min="0"
                max="180"
                step="0.5"
                placeholder="Video end"
                @input="setTrimEndFromEvent"
              />
            </EditorField>

            <EditorField label="Playback speed" :value="`${playbackSpeed.toFixed(2)}x`">
              <input v-model.number="playbackSpeed" type="range" min="0.5" max="2" step="0.05" />
            </EditorField>
          </div>

          <div v-else-if="activeVideoTool === 'blur'" class="editor-controls">
            <div class="editor-tool-items-row">
              <button class="editor-item-create-button" type="button" @click="addBlurMask">
                <Plus :size="14" :stroke-width="2.4" aria-hidden="true" />
                <span>Add blur</span>
              </button>
              <div
                v-for="item in blurMasks"
                :key="item.id"
                :class="['editor-item-chip', { 'editor-item-chip-active': selectedBlurId === item.id }]"
              >
                <button
                  class="editor-item-chip-main"
                  type="button"
                  @click="selectedBlurId = item.id; activatePreviewTool('blur', item.id)"
                >
                  <span>{{ getBlurLabel(item) }}</span>
                </button>
                <button
                  class="editor-item-chip-remove"
                  type="button"
                  :aria-label="`Remove ${getBlurLabel(item)}`"
                  :title="`Remove ${getBlurLabel(item)}`"
                  @click.stop="removeBlurMask(item.id)"
                >
                  <X :size="14" :stroke-width="2.4" aria-hidden="true" />
                </button>
              </div>
            </div>

            <template v-if="selectedBlurItem">
              <EditorField label="Blur strength" :value="String(activeBlurStrength)">
                <input v-model.number="activeBlurStrength" type="range" min="2" max="11" step="1" />
              </EditorField>
            </template>
            <p v-else class="empty-state">
              No blur mask yet. Add one to place and resize it on the preview.
            </p>
          </div>

          <div v-else class="editor-controls editor-controls-overlay">
            <div class="editor-tool-items-row">
              <button class="editor-item-create-button" type="button" @click="addOverlayItem">
                <Plus :size="14" :stroke-width="2.4" aria-hidden="true" />
                <span>Add overlay</span>
              </button>
              <div
                v-for="item in overlays"
                :key="item.id"
                :class="['editor-item-chip', { 'editor-item-chip-active': selectedOverlayId === item.id }]"
              >
                <button
                  class="editor-item-chip-main"
                  type="button"
                  @click="selectedOverlayId = item.id; activatePreviewTool('overlay', item.id)"
                >
                  <span>{{ getOverlayLabel(item) }}</span>
                </button>
                <button
                  class="editor-item-chip-remove"
                  type="button"
                  :aria-label="`Remove ${getOverlayLabel(item)}`"
                  :title="`Remove ${getOverlayLabel(item)}`"
                  @click.stop="removeOverlayItem(item.id)"
                >
                  <X :size="14" :stroke-width="2.4" aria-hidden="true" />
                </button>
              </div>
            </div>

            <template v-if="selectedOverlayItem">
              <EditorField label="Overlay text" wide>
                <textarea
                  v-model="activeOverlayText"
                  rows="3"
                  maxlength="160"
                  placeholder="Add watermark, speaker note, or label..."
                />
              </EditorField>

              <EditorField label="Font size" :value="`${activeOverlayFontSize}px`">
                <input v-model.number="activeOverlayFontSize" type="range" min="14" max="72" step="1" />
              </EditorField>

              <EditorField label="Text color" :value="activeOverlayTextColor">
                <input v-model="activeOverlayTextColor" type="color" />
              </EditorField>
            </template>
            <p v-else class="empty-state">
              No overlay yet. Add one to place, resize, and edit its text on the preview.
            </p>
          </div>
        </div>

        <div v-else-if="isAudioGroupOpen" class="editor-tool-panel">
          <div class="editor-tool-panel-heading">
            <div>
              <p class="eyebrow">Audio tools</p>
              <h2>Voice mix</h2>
            </div>
          </div>
          <div class="editor-controls">
            <EditorToggleField
              v-model="burnAudio"
              label="Burn voice"
              description="Toggle the Vietnamese voice track inside the edited video."
            />

            <EditorToggleField
              v-model="burnOriginalAudio"
              label="Burn original voice"
              description="Keep or remove the source audio track from the edited video."
            />

            <EditorField label="Voice volume" :value="`${voiceVolumePercent}%`">
              <input v-model.number="voiceVolumePercent" type="range" min="0" max="200" step="5" />
            </EditorField>

            <EditorField label="Original volume" :value="`${originalVolumePercent}%`">
              <input v-model.number="originalVolumePercent" type="range" min="0" max="200" step="5" />
            </EditorField>
          </div>
        </div>

        <div v-else-if="isCaptionsGroupOpen" class="editor-tool-panel">
          <div class="editor-tool-panel-heading">
            <div>
              <p class="eyebrow">Caption tools</p>
              <h2>{{ activeCaptionsTool === 'style' ? 'Style/Position' : 'Subtitle editor' }}</h2>
            </div>
          </div>

          <div class="editor-tool-tabs" aria-label="Caption tool options">
            <button
              :class="['editor-tool-tab', { 'editor-tool-tab-active': activeCaptionsTool === 'style' }]"
              type="button"
              @click="activeCaptionsTool = 'style'"
            >
              <span>Style/Position</span>
              <small v-if="dirtySummary.tools.style.length" class="editor-inline-badge">{{ dirtySummary.tools.style.length }}</small>
            </button>
            <button
              :class="['editor-tool-tab', { 'editor-tool-tab-active': activeCaptionsTool === 'editor' }]"
              type="button"
              @click="activeCaptionsTool = 'editor'"
            >
              <span>Subtitle editor</span>
              <small v-if="dirtySummary.tools.editor.length" class="editor-inline-badge">{{ dirtySummary.tools.editor.length }}</small>
            </button>
          </div>

          <div v-if="activeCaptionsTool === 'style'" class="editor-controls editor-controls-style">
            <EditorToggleField
              v-model="burnSubtitle"
              label="Burn subtitle"
              description="Render Vietnamese captions directly into the edited video."
            />

            <EditorField label="Font size" :value="`${subtitleFontSize}px`">
              <input v-model.number="subtitleFontSize" type="range" min="14" max="48" step="1" />
            </EditorField>

            <EditorField label="Position">
              <div class="filter-menu editor-menu-box">
                <button
                  class="filter-trigger editor-filter-trigger"
                  type="button"
                  :aria-expanded="isSubtitlePositionMenuOpen"
                  @click="isSubtitlePositionMenuOpen = !isSubtitlePositionMenuOpen"
                >
                  <strong>{{ selectedSubtitlePositionLabel }}</strong>
                  <ChevronDown :size="18" :stroke-width="2" aria-hidden="true" />
                </button>
                <div v-if="isSubtitlePositionMenuOpen" class="filter-options">
                  <button
                    v-for="option in subtitlePositionOptions"
                    :key="option.value"
                    class="filter-option"
                    type="button"
                    @click="selectSubtitlePosition(option.value)"
                  >
                    <span>{{ option.label }}</span>
                    <Check
                      v-if="option.value === subtitlePosition"
                      :size="16"
                      :stroke-width="2.5"
                      aria-hidden="true"
                    />
                  </button>
                </div>
              </div>
            </EditorField>

            <EditorField label="Text color" :value="subtitleTextColor">
              <input v-model="subtitleTextColor" type="color" />
            </EditorField>
          </div>

          <div v-else class="editor-segments-panel">
            <article
              v-for="(segment, index) in subtitleSegments"
              :key="segment.id"
              class="editor-segment-card"
            >
              <div class="editor-segment-meta">
                <strong>Segment {{ segment.id + 1 }}</strong>
                <span>{{ formatSegmentTime(segment.start) }} - {{ formatSegmentTime(segment.end) }}</span>
              </div>
              <label class="field textarea-field">
                <span>Vietnamese text</span>
                <textarea
                  :value="segment.text_vi"
                  rows="2"
                  maxlength="500"
                  @input="updateSubtitleText(index, ($event.target as HTMLTextAreaElement).value)"
                />
              </label>
              <div class="editor-segment-timing-grid">
                <EditorField label="Start" :value="formatSegmentTime(segment.start)">
                  <input
                    :value="segment.start"
                    type="number"
                    min="0"
                    max="180"
                    step="0.1"
                    @input="updateSubtitleStart(index, ($event.target as HTMLInputElement).value)"
                  />
                </EditorField>
                <EditorField label="End" :value="formatSegmentTime(segment.end)">
                  <input
                    :value="segment.end"
                    type="number"
                    min="0"
                    max="180"
                    step="0.1"
                    @input="updateSubtitleEnd(index, ($event.target as HTMLInputElement).value)"
                  />
                </EditorField>
              </div>
              <p v-if="segment.text_zh" class="editor-segment-reference">{{ segment.text_zh }}</p>
            </article>
          </div>
        </div>

        <div class="editor-dock-row">
          <div class="editor-toolbar" aria-label="Editor tools">
            <button
              :class="['editor-tool-button', { 'editor-tool-button-active': activeGroup === 'video' }]"
              type="button"
              aria-label="Video tools"
              title="Video"
              @click="activeGroup = activeGroup === 'video' ? '' : 'video'; activeVideoTool = selectedPreviewTool || 'trim'"
            >
              <Clapperboard :size="20" :stroke-width="2" aria-hidden="true" />
              <span>Video</span>
              <small v-if="dirtySummary.groups.video.length" class="editor-tool-badge">{{ dirtySummary.groups.video.length }}</small>
            </button>

            <button
              :class="['editor-tool-button', { 'editor-tool-button-active': activeGroup === 'audio' }]"
              type="button"
              aria-label="Audio tools"
              title="Audio"
              @click="activeGroup = activeGroup === 'audio' ? '' : 'audio'"
            >
              <Volume2 :size="20" :stroke-width="2" aria-hidden="true" />
              <span>Audio</span>
              <small v-if="dirtySummary.groups.audio.length" class="editor-tool-badge">{{ dirtySummary.groups.audio.length }}</small>
            </button>

            <button
              :class="['editor-tool-button', { 'editor-tool-button-active': activeGroup === 'captions' }]"
              type="button"
              aria-label="Caption tools"
              title="Captions"
              @click="activeGroup = activeGroup === 'captions' ? '' : 'captions'; activeCaptionsTool = 'style'"
            >
              <Captions :size="20" :stroke-width="2" aria-hidden="true" />
              <span>Captions</span>
              <small v-if="dirtySummary.groups.captions.length" class="editor-tool-badge">{{ dirtySummary.groups.captions.length }}</small>
            </button>

            <button
              class="editor-tool-button editor-toolbar-close"
              type="button"
              aria-label="Close edit tools"
              :title="hasPendingChanges ? renderSummaryTitle : 'Close tools'"
              @click="isToolbarOpen = false; activeGroup = ''"
            >
              <ArrowDown :size="22" :stroke-width="2.3" aria-hidden="true" />
              <small v-if="hasPendingChanges" class="editor-tool-badge">{{ dirtySummary.total }}</small>
            </button>
          </div>

          <div class="editor-action-bar" aria-label="Editor actions">
            <button
              class="editor-action-button"
              type="button"
              :disabled="!hasPendingChanges || isRendering"
              title="Clear all pending edits"
              @click="clearPendingChanges"
            >
              <RotateCcw :size="18" :stroke-width="2.2" aria-hidden="true" />
              <span>Clear</span>
            </button>

            <button
              class="editor-action-button editor-action-primary"
              type="button"
              :disabled="!canEdit || isRendering || !hasPendingChanges"
              :title="renderSummaryTitle"
              @click="renderEdit"
            >
              <Play :size="18" :stroke-width="2.3" aria-hidden="true" />
              <span>{{ isRendering ? 'Rendering...' : 'Render' }}</span>
            </button>

            <a
              class="editor-action-button"
              :href="previewUrl || undefined"
              title="Download edited video"
            >
              <Download :size="18" :stroke-width="2.3" aria-hidden="true" />
              <span>Download</span>
            </a>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>
