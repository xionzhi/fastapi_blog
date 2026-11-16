import { onScopeDispose, watch, type Ref } from 'vue'

let owners = 0
let originalOverflow = ''

/** Nested overlays share one lock and restore the pre-existing body style. */
export function useScrollLock(active: Ref<boolean>): void {
  let locked = false
  function update(open: boolean): void {
    if (locked === open) return
    locked = open
    if (open) {
      if (owners++ === 0) {
        originalOverflow = document.body.style.overflow
        document.body.style.overflow = 'hidden'
      }
    } else if (--owners === 0) {
      document.body.style.overflow = originalOverflow
    }
  }
  watch(active, update, { immediate: true, flush: 'sync' })
  onScopeDispose(() => update(false))
}
