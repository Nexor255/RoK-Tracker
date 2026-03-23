import { computed, ref } from 'vue'

const TOAST_LIMIT = 3
const TOAST_REMOVE_DELAY = 5000

export type ToastVariant = 'default' | 'success' | 'destructive'

export interface Toast {
  id: string
  title?: string
  description?: string
  variant?: ToastVariant
  duration?: number
}

const toasts = ref<Toast[]>([])
let count = 0

function genId() {
  count = (count + 1) % Number.MAX_SAFE_INTEGER
  return count.toString()
}

function addToast(toast: Omit<Toast, 'id'>) {
  const id = genId()
  const newToast: Toast = { ...toast, id }
  toasts.value = [newToast, ...toasts.value].slice(0, TOAST_LIMIT)

  const duration = toast.duration ?? TOAST_REMOVE_DELAY
  setTimeout(() => {
    dismiss(id)
  }, duration)

  return id
}

function dismiss(toastId: string) {
  toasts.value = toasts.value.filter((t) => t.id !== toastId)
}

export function toast(props: Omit<Toast, 'id'>) {
  return addToast(props)
}

export function useToast() {
  return {
    toasts: computed(() => toasts.value),
    toast,
    dismiss,
  }
}
