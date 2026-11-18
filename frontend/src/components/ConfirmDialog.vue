<script setup lang="ts">
import { onMounted, ref, useId } from 'vue'
import { Trash2, X } from 'lucide-vue-next'
import { useModalFocus } from '../composables/useModalFocus'
import { useScrollLock } from '../composables/useScrollLock'

const props = withDefaults(
  defineProps<{
    title: string
    itemName: string
    description: string
    busy?: boolean
    error?: string
    confirmLabel?: string
  }>(),
  { busy: false, error: '', confirmLabel: 'Delete' },
)
const emit = defineEmits<{ confirm: []; cancel: [] }>()
const active = ref(false)
const dialog = ref<HTMLElement>()
const titleId = useId()
const itemId = useId()
const descriptionId = useId()
function cancel(): void {
  if (!props.busy) emit('cancel')
}
useScrollLock(active)
const { keyboard } = useModalFocus(active, dialog, cancel)
onMounted(() => {
  active.value = true
})
</script>

<template>
  <Teleport to="body">
    <div
      class="admin admin-modal-backdrop"
      @click.self="cancel"
      @keydown="keyboard"
    >
      <section
        ref="dialog"
        class="admin-modal confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="`${itemId} ${descriptionId}`"
        :aria-busy="busy"
        tabindex="-1"
      >
        <header>
          <span
            class="confirm-icon"
            aria-hidden="true"
          >
            <Trash2 :size="22" />
          </span>
          <button
            type="button"
            class="icon-button"
            aria-label="Close confirmation"
            :disabled="busy"
            @click="cancel"
          >
            <X :size="20" />
          </button>
        </header>
        <h2 :id="titleId">{{ title }}</h2>
        <p
          :id="itemId"
          class="confirm-item"
        >
          {{ itemName }}
        </p>
        <p
          :id="descriptionId"
          class="muted"
        >
          {{ description }}
        </p>
        <p
          v-if="error"
          class="form-error"
          role="alert"
        >
          {{ error }}
        </p>
        <footer>
          <button
            type="button"
            class="button-secondary"
            :disabled="busy"
            @click="cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            class="button-primary confirm-delete"
            :disabled="busy"
            @click="!busy && emit('confirm')"
          >
            <Trash2 :size="15" />
            {{ busy ? 'Deleting…' : confirmLabel }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.confirm-dialog {
  max-height: calc(100dvh - 50px);
  overflow: auto;
}
.confirm-icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: #fbefef;
  color: #af3f48;
}
.admin .confirm-dialog h2 {
  font-size: 22px;
  margin: 0 0 12px;
}
.confirm-item {
  font-size: 15px;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.confirm-dialog footer {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 26px;
}
.admin .confirm-delete {
  background: #b6414b;
  border-color: #b6414b;
}
.admin .confirm-delete:not(:disabled):hover {
  background: #96343d;
  border-color: #96343d;
}
</style>
