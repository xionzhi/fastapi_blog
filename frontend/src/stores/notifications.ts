import { ref } from 'vue'

export const toast = ref('')
let timeout: ReturnType<typeof setTimeout> | undefined

export function notify(message: string): void {
  clearTimeout(timeout)
  toast.value = message
  timeout = setTimeout(() => {
    toast.value = ''
  }, 4500)
}
