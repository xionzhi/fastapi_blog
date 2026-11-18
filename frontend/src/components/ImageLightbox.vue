<script setup lang="ts">
import { onMounted, ref, useId } from 'vue'
import { Maximize, Minus, Plus, X } from 'lucide-vue-next'
import { useImageLightbox } from '../composables/useImageLightbox'
import { useModalFocus } from '../composables/useModalFocus'
import { useScrollLock } from '../composables/useScrollLock'

defineProps<{ src: string; alt: string }>()
const emit = defineEmits<{ close: [] }>()
const active = ref(false)
const dialog = ref<HTMLElement>()
const hintId = useId()
const close = () => emit('close')
const { keyboard: modalKeyboard } = useModalFocus(active, dialog, close)
useScrollLock(active)
const {
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
} = useImageLightbox()
function keydown(event: KeyboardEvent): void {
  modalKeyboard(event)
  if (!event.defaultPrevented) keyboard(event)
}
onMounted(() => {
  active.value = true
})
</script>

<template>
  <Teleport to="body">
    <section
      ref="dialog"
      class="image-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label="Image preview"
      :aria-describedby="hintId"
      tabindex="-1"
      @click.self="close"
      @keydown="keydown"
      @keydown.ctrl.k.stop.prevent
      @keydown.meta.k.stop.prevent
    >
      <div
        class="lightbox-toolbar"
        role="group"
        aria-label="Image controls"
      >
        <button
          type="button"
          aria-label="Zoom out"
          title="Zoom out (-)"
          :disabled="!ready || scale <= minScale + 0.001"
          @click="zoom(scale / 1.25)"
        >
          <Minus :size="19" />
        </button>
        <output aria-label="Zoom level">{{ ready ? `${Math.round(scale * 100)}%` : '—' }}</output>
        <button
          type="button"
          aria-label="Zoom in"
          title="Zoom in (+)"
          :disabled="!ready || scale >= 4"
          @click="zoom(scale * 1.25)"
        >
          <Plus :size="19" />
        </button>
        <span
          class="lightbox-divider"
          aria-hidden="true"
        />
        <button
          type="button"
          aria-label="Original size"
          title="Original size (1)"
          :disabled="!ready"
          @click="original"
        >
          1:1
        </button>
        <button
          type="button"
          aria-label="Fit to screen"
          title="Fit to screen (0)"
          :disabled="!ready"
          @click="fit"
        >
          <Maximize :size="18" />
        </button>
      </div>
      <button
        type="button"
        class="lightbox-close"
        aria-label="Close image"
        title="Close (Esc)"
        @click="close"
      >
        <X :size="22" />
      </button>
      <div
        ref="viewport"
        class="lightbox-viewport"
        :class="{ 'can-pan': canPan, dragging }"
        @wheel.prevent="wheel"
        @pointerdown="pointerDown"
        @pointermove="pointerMove"
        @pointerup="pointerUp"
        @pointercancel="pointerUp"
        @lostpointercapture="pointerUp"
        @click="click($event) && close()"
      >
        <img
          :src="src"
          :alt="alt || 'Enlarged image'"
          :style="imageStyle"
          :class="{ 'is-ready': ready }"
          draggable="false"
          decoding="async"
          @load="loaded"
          @error="failed = true"
        />
        <p
          v-if="failed"
          class="lightbox-message"
          role="alert"
        >
          This image could not be loaded.
        </p>
        <p
          v-else-if="!ready"
          class="lightbox-message"
          role="status"
        >
          Loading image…
        </p>
      </div>
      <p
        :id="hintId"
        class="lightbox-hint"
      >
        Scroll or pinch to zoom · Drag to move · Esc to close
      </p>
    </section>
  </Teleport>
</template>

<style scoped>
.image-lightbox {
  --lightbox-controls-bg: rgb(255 255 255 / 78%);
  --lightbox-controls-border: rgb(38 52 58 / 16%);
  position: fixed;
  inset: 0;
  z-index: 160;
  display: grid;
  grid-template:
    '. toolbar close' auto
    'viewport viewport viewport' minmax(0, 1fr)
    'hint hint hint' auto / minmax(44px, 1fr) auto minmax(44px, 1fr);
  align-items: center;
  row-gap: 12px;
  padding: max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right))
    max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left));
  background: rgb(248 248 245 / 72%);
  backdrop-filter: blur(18px);
  color: #26343a;
  font:
    13px 'Open Sans',
    sans-serif;
}
.image-lightbox:focus {
  outline: none;
}
.lightbox-toolbar {
  grid-area: toolbar;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px;
  border: 1px solid var(--lightbox-controls-border);
  border-radius: 12px;
  background: var(--lightbox-controls-bg);
  box-shadow: 0 3px 18px #1e2b3314;
}
.image-lightbox button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 600;
}
.image-lightbox button:not(:disabled):hover {
  background: rgb(226 231 228 / 86%);
}
.image-lightbox button:focus-visible {
  outline: 2px solid #49685c;
  outline-offset: -2px;
}
.lightbox-toolbar output {
  width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.lightbox-divider {
  height: 20px;
  width: 1px;
  margin: 0 3px;
  background: var(--lightbox-controls-border);
}
.image-lightbox .lightbox-close {
  grid-area: close;
  justify-self: end;
  width: 44px;
  height: 44px;
  border: 1px solid var(--lightbox-controls-border);
  background: var(--lightbox-controls-bg);
}
.lightbox-viewport {
  grid-area: viewport;
  align-self: stretch;
  position: relative;
  overflow: hidden;
  touch-action: none;
  user-select: none;
}
.lightbox-viewport img {
  position: absolute;
  top: 50%;
  left: 50%;
  max-width: none;
  max-height: none;
  margin: 0;
  opacity: 0;
  transform-origin: center;
  cursor: default;
}
.lightbox-viewport img.is-ready {
  opacity: 1;
}
.lightbox-viewport.can-pan,
.lightbox-viewport.can-pan img {
  cursor: grab;
}
.lightbox-viewport.dragging,
.lightbox-viewport.dragging img {
  cursor: grabbing;
}
.lightbox-message {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  padding: 24px;
  text-align: center;
}
.lightbox-hint {
  grid-area: hint;
  justify-self: center;
  margin: 0;
  text-align: center;
  font-size: 11px;
  line-height: 1.6;
  color: #34454a;
}
@media (max-width: 600px) {
  .image-lightbox {
    grid-template:
      '. close' auto
      'viewport viewport' minmax(0, 1fr)
      'toolbar toolbar' auto
      'hint hint' auto / minmax(0, 1fr) auto;
    row-gap: 8px;
  }
  .lightbox-toolbar {
    justify-self: center;
  }
}
</style>
