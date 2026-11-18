import { nextTick, onScopeDispose, watch, type Ref } from 'vue'

/** Keep a teleported modal isolated from the application and return focus on close. */
export function useModalFocus(
  active: Ref<boolean>,
  dialog: Ref<HTMLElement | undefined>,
  close: () => void,
) {
  let previousFocus: HTMLElement | null = null
  let background: HTMLElement | null = null
  let originalInert = false
  let disposed = false

  function restore(): void {
    if (background) background.inert = originalInert
    background = null
    if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
    previousFocus = null
  }

  const focusable = (): HTMLElement[] =>
    [
      ...(dialog.value?.querySelectorAll<HTMLElement>(
        'a[href],button,input,textarea,select,[tabindex]',
      ) ?? []),
    ].filter(
      (element) =>
        element.tabIndex >= 0 &&
        !element.matches(':disabled') &&
        element.getClientRects().length > 0,
    )

  watch(
    active,
    async (open) => {
      if (!open) {
        restore()
        return
      }
      previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
      background = document.getElementById('app')
      originalInert = background?.inert ?? false
      if (background) background.inert = true
      await nextTick()
      if (!disposed && active.value) {
        const target =
          dialog.value?.querySelector<HTMLElement>(
            '[data-initial-focus]:not(:disabled), input:not(:disabled):not([hidden])',
          ) || dialog.value
        target?.focus()
      }
    },
    { flush: 'post' },
  )

  function keyboard(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      close()
    } else if (event.key === 'Tab') {
      const items = focusable()
      const first = items[0]
      const last = items.at(-1)
      if (!first) {
        event.preventDefault()
        dialog.value?.focus()
      } else if (
        event.shiftKey &&
        (document.activeElement === first || document.activeElement === dialog.value)
      ) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }

  onScopeDispose(() => {
    disposed = true
    restore()
  })
  return { keyboard }
}
