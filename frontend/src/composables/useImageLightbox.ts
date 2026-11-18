import { computed, onMounted, onScopeDispose, reactive, ref } from 'vue'

type Point = { x: number; y: number }

/** Zoom in original-image pixels, keeping the focal point and pan within the viewport. */
export function useImageLightbox() {
  const viewport = ref<HTMLElement>()
  const size = reactive({ width: 0, height: 0 })
  const natural = reactive({ width: 0, height: 0 })
  const offset = reactive({ x: 0, y: 0 })
  const scale = ref(1)
  const fitted = ref(true)
  const failed = ref(false)
  const dragging = ref(false)
  const ready = computed(() => natural.width > 0 && natural.height > 0)
  const fitScale = computed(() =>
    ready.value && size.width && size.height
      ? Math.min(1, size.width / natural.width, size.height / natural.height)
      : 1,
  )
  const minScale = computed(() => Math.min(0.25, fitScale.value))
  const canPan = computed(
    () =>
      natural.width * scale.value > size.width + 1 ||
      natural.height * scale.value > size.height + 1,
  )
  const imageStyle = computed(() => ({
    width: `${natural.width}px`,
    height: `${natural.height}px`,
    transform: `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px) scale(${scale.value})`,
  }))
  const pointers = new Map<number, Point>()
  let moved = false
  let startedOnImage = false
  let pressPoint: Point = { x: 0, y: 0 }
  let observer: ResizeObserver | undefined

  function clamp(): void {
    const x = Math.max(0, (natural.width * scale.value - size.width) / 2)
    const y = Math.max(0, (natural.height * scale.value - size.height) / 2)
    offset.x = Math.max(-x, Math.min(x, offset.x))
    offset.y = Math.max(-y, Math.min(y, offset.y))
  }
  function fit(): void {
    scale.value = fitScale.value
    fitted.value = true
    offset.x = offset.y = 0
  }
  function zoom(value: number, anchor: Point = { x: 0, y: 0 }): void {
    if (!ready.value || !Number.isFinite(value)) return
    const next = Math.max(minScale.value, Math.min(4, value))
    const ratio = next / scale.value
    offset.x = anchor.x - (anchor.x - offset.x) * ratio
    offset.y = anchor.y - (anchor.y - offset.y) * ratio
    scale.value = next
    fitted.value = false
    clamp()
  }
  function original(): void {
    offset.x = offset.y = 0
    zoom(1)
  }
  function loaded(event: Event): void {
    const image = event.target as HTMLImageElement
    natural.width = image.naturalWidth
    natural.height = image.naturalHeight
    failed.value = !ready.value
    fit()
  }
  function point(event: { clientX: number; clientY: number }): Point {
    const rect = viewport.value!.getBoundingClientRect()
    return {
      x: event.clientX - rect.left - rect.width / 2,
      y: event.clientY - rect.top - rect.height / 2,
    }
  }
  function toggle(event: MouseEvent): void {
    if (moved) return
    if (scale.value > fitScale.value + 0.01) fit()
    else zoom(Math.max(1, fitScale.value * 2), point(event))
  }
  function wheel(event: WheelEvent): void {
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? size.height : 1
    const delta = Math.max(-120, Math.min(120, event.deltaY * unit))
    zoom(scale.value * Math.exp(-delta * 0.0025), point(event))
  }
  function gesture() {
    const values = [...pointers.values()]
    const first = values[0]!
    const second = values[1] ?? first
    return {
      center: { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 },
      distance: Math.max(1, Math.hypot(second.x - first.x, second.y - first.y)),
    }
  }
  function pointerDown(event: PointerEvent): void {
    if (event.button !== 0 || !ready.value) return
    if (!pointers.size) {
      moved = false
      startedOnImage = event.target instanceof HTMLImageElement
      pressPoint = point(event)
    }
    pointers.set(event.pointerId, point(event))
    if (pointers.size > 1) moved = true
    viewport.value?.setPointerCapture(event.pointerId)
    dragging.value = canPan.value
  }
  function pointerMove(event: PointerEvent): void {
    const previous = pointers.get(event.pointerId)
    if (!previous) return
    const before = gesture()
    const next = point(event)
    pointers.set(event.pointerId, next)
    if (Math.hypot(next.x - pressPoint.x, next.y - pressPoint.y) > 4) moved = true
    const after = gesture()
    if (pointers.size > 1) zoom((scale.value * after.distance) / before.distance, before.center)
    offset.x += after.center.x - before.center.x
    offset.y += after.center.y - before.center.y
    clamp()
    dragging.value = canPan.value
  }
  function pointerUp(event: PointerEvent): void {
    pointers.delete(event.pointerId)
    dragging.value = pointers.size > 0 && canPan.value
  }
  function click(event: MouseEvent): boolean {
    if (moved) return false
    if (startedOnImage || event.target instanceof HTMLImageElement) {
      toggle(event)
      return false
    }
    return event.target === viewport.value
  }
  function keyboard(event: KeyboardEvent): void {
    if (event.ctrlKey || event.metaKey || event.altKey) return
    const step: Record<string, Point> = {
      ArrowLeft: { x: 80, y: 0 },
      ArrowRight: { x: -80, y: 0 },
      ArrowUp: { x: 0, y: 80 },
      ArrowDown: { x: 0, y: -80 },
    }
    if (event.key === '+' || event.key === '=') zoom(scale.value * 1.25)
    else if (event.key === '-') zoom(scale.value / 1.25)
    else if (event.key === '0') fit()
    else if (event.key === '1') original()
    else if (step[event.key]) {
      offset.x += step[event.key]!.x
      offset.y += step[event.key]!.y
      clamp()
    } else return
    event.preventDefault()
    event.stopPropagation()
  }
  onMounted(() => {
    observer = new ResizeObserver(() => {
      const rect = viewport.value?.getBoundingClientRect()
      if (!rect) return
      size.width = rect.width
      size.height = rect.height
      if (fitted.value) fit()
      else clamp()
    })
    if (viewport.value) observer.observe(viewport.value)
  })
  onScopeDispose(() => {
    observer?.disconnect()
    pointers.clear()
  })
  return {
    viewport,
    scale,
    minScale,
    imageStyle,
    ready,
    failed,
    dragging,
    canPan,
    fit,
    zoom,
    original,
    loaded,
    wheel,
    pointerDown,
    pointerMove,
    pointerUp,
    click,
    keyboard,
  }
}
