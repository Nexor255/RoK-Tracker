<script setup lang="ts">
import { useToast } from './use-toast'
import { X, CheckCircle2, AlertCircle, Info } from 'lucide-vue-next'

const { toasts, dismiss } = useToast()

function variantClasses(variant?: string) {
  switch (variant) {
    case 'success':
      return 'border-emerald-500/30 bg-emerald-950/90 text-emerald-50'
    case 'destructive':
      return 'border-red-500/30 bg-red-950/90 text-red-50'
    default:
      return 'border-border bg-background text-foreground'
  }
}

function getIcon(variant?: string) {
  switch (variant) {
    case 'success':
      return CheckCircle2
    case 'destructive':
      return AlertCircle
    default:
      return Info
  }
}

function iconClasses(variant?: string) {
  switch (variant) {
    case 'success':
      return 'text-emerald-400'
    case 'destructive':
      return 'text-red-400'
    default:
      return 'text-muted-foreground'
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-[360px] pointer-events-none">
      <TransitionGroup
        enter-active-class="transition-all duration-300 ease-out"
        leave-active-class="transition-all duration-200 ease-in"
        enter-from-class="opacity-0 translate-y-2 scale-95"
        leave-to-class="opacity-0 translate-y-2 scale-95"
        move-class="transition-all duration-300"
      >
        <div
          v-for="t in toasts"
          :key="t.id"
          :class="[
            'pointer-events-auto relative flex items-start gap-3 rounded-lg border p-4 shadow-lg backdrop-blur-sm',
            variantClasses(t.variant),
          ]"
        >
          <component
            :is="getIcon(t.variant)"
            class="h-5 w-5 shrink-0 mt-0.5"
            :class="iconClasses(t.variant)"
          />
          <div class="flex-1 min-w-0">
            <p v-if="t.title" class="text-sm font-semibold leading-none tracking-tight">
              {{ t.title }}
            </p>
            <p v-if="t.description" class="text-sm opacity-80 mt-1">
              {{ t.description }}
            </p>
          </div>
          <button
            class="shrink-0 rounded-md p-1 opacity-50 hover:opacity-100 transition-opacity"
            @click="dismiss(t.id)"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
