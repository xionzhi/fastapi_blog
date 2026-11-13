import { onScopeDispose } from 'vue'

/** Cancel both the timer and in-flight request when a newer task supersedes it. */
export function useDebouncedTask(delay: number) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | undefined

  function cancel(): void {
    clearTimeout(timer)
    controller?.abort()
    controller = undefined
  }

  function schedule(task: (signal: AbortSignal) => Promise<void>): void {
    cancel()
    const current = new AbortController()
    controller = current
    timer = setTimeout(() => {
      void task(current.signal).catch((error: unknown) => {
        if (!current.signal.aborted) console.error('Unhandled background task failure', error)
      })
    }, delay)
  }

  onScopeDispose(cancel)
  return { schedule, cancel }
}
