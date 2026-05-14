<template>
  <div class="relative flex h-screen flex-col bg-background">
    <!-- Ambient background glow for depth -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden">
      <div class="absolute -top-[20%] -left-[10%] h-[60%] w-[60%] rounded-full bg-primary/20 dark:bg-primary/10 blur-[120px] transition-all duration-1000 ease-in-out" />
      <div class="absolute top-[40%] -right-[10%] h-[60%] w-[60%] rounded-full bg-blue-500/15 dark:bg-blue-600/10 blur-[120px] transition-all duration-1000 ease-in-out" />
    </div>

    <div class="z-10 flex flex-1 flex-col overflow-hidden">
      <!-- Header -->
      <header class="sticky top-0 z-40 flex h-14 items-center gap-4 border-b bg-primary/90 backdrop-blur-md px-6 text-primary-foreground shadow-sm">
        <div class="flex items-center gap-2">
          <Radar class="h-6 w-6" />
          <span class="text-lg font-semibold">RoK Tracker Suite</span>
        </div>
        <div class="flex-1" />
        <button
          class="theme-toggle rounded-full p-2 hover:bg-white/10 transition-colors"
          :class="{ 'theme-toggle--toggled': darkMode }"
          @click="() => toggleDarkMode()"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
            width="1.5em"
            height="1.5em"
            fill="currentColor"
            stroke-linecap="round"
            class="theme-toggle__classic"
            viewBox="0 0 32 32"
          >
            <clipPath id="theme-toggle__classic__cutout">
              <path d="M0-5h30a1 1 0 0 0 9 13v24H0Z" />
            </clipPath>
            <g clip-path="url(#theme-toggle__classic__cutout)">
              <circle cx="16" cy="16" r="9.34" />
              <g stroke="currentColor" stroke-width="1.5">
                <path d="M16 5.5v-4" />
                <path d="M16 30.5v-4" />
                <path d="M1.5 16h4" />
                <path d="M26.5 16h4" />
                <path d="m23.4 8.6 2.8-2.8" />
                <path d="m5.7 26.3 2.9-2.9" />
                <path d="m5.8 5.8 2.8 2.8" />
                <path d="m23.4 23.4 2.9 2.9" />
              </g>
            </g>
          </svg>
        </button>
      </header>

      <!-- Main content with sidebar -->
      <div class="flex flex-1 overflow-hidden">
        <!-- Sidebar Navigation -->
        <nav class="flex w-[120px] flex-col items-center gap-1 border-r bg-sidebar-background dark:bg-muted/20 backdrop-blur-md p-2 overflow-y-auto scrollbar-hidden">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex w-full flex-col items-center justify-center gap-1 rounded-md px-3 py-2.5 text-xs font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
          active-class="bg-accent text-accent-foreground"
        >
          <component :is="item.icon" class="h-5 w-5" />
          {{ item.label }}
        </router-link>
      </nav>

      <!-- Content area -->
      <main class="flex-1 overflow-auto scrollbar-hidden p-4 relative">
        <!-- Loading overlay while sidecar initializes -->
        <transition
          enter-active-class="transition-opacity duration-300"
          leave-active-class="transition-opacity duration-500"
          enter-from-class="opacity-0"
          leave-to-class="opacity-0"
        >
          <div
            v-if="!configStore.configLoaded"
            class="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/80 backdrop-blur-sm"
          >
            <svg class="h-10 w-10 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span class="text-sm text-muted-foreground">Initializing scanner backend…</span>
          </div>
        </transition>
        <router-view v-slot="{ Component, route }">
          <transition
            :enter-active-class="`${(route.meta.transitionIn as string) ?? 'slide-up'}-enter-active`"
            :leave-active-class="`${(route.meta.transitionOut as string) ?? 'slide-up'}-leave-active`"
            :enter-from-class="`${(route.meta.transitionIn as string) ?? 'slide-up'}-enter-from`"
            :leave-to-class="`${(route.meta.transitionOut as string) ?? 'slide-up'}-leave-to`"
            mode="out-in"
          >
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </main>
    </div>

    <!-- Confirm Dialog (replaces $q.dialog) -->
    <AlertDialog :open="confirmDialogOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Confirm</AlertDialogTitle>
          <AlertDialogDescription>{{ confirmDialogMessage }}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel @click="handleConfirmDialogResponse(false)">No</AlertDialogCancel>
          <AlertDialogAction @click="handleConfirmDialogResponse(true)">Yes</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Toast notifications -->
    <Toaster />

    <!-- Notifiers -->
    <UpdateNotifier />
    <ErrorNotifier />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, markRaw, onMounted, onUnmounted } from 'vue'
import { useDark, useToggle } from '@vueuse/core'
import { useConfigStore } from './stores/config-store'
import { FullConfigSchema } from './schema/FullConfig'
import { BatchGovernorDataListSchema, KingdomPresetListSchema } from './schema/SchemaUtils'
import { BatchTypeSchema } from './schema/BatchType'
import { useAllianceStore } from './stores/alliance-store'
import { BatchAdditionalDataSchema } from './schema/BatchAdditionalData'
import { useHonorStore } from './stores/honor-store'
import { useSeedStore } from './stores/seed-store'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Toaster, toast } from '@/components/ui/toast'
import UpdateNotifier from '@/components/UpdateNotifier.vue'
import ErrorNotifier from '@/components/ErrorNotifier.vue'
import { Radar, ScanLine, Calculator, Settings } from 'lucide-vue-next'
import { onSidecarEvent } from '@/lib/tauriClient'
import * as ipc from '@/lib/tauriClient'
import { useErrorStore } from '@/stores/error-store'
import { analyzeError } from '@/util/error-mapper'

const configStore = useConfigStore()
const allianceStore = useAllianceStore()
const honorStore = useHonorStore()
const seedStore = useSeedStore()
const errorStore = useErrorStore()

const darkMode = useDark()
const toggleDarkMode = useToggle(darkMode)

const navItems = [
  { to: '/scanner', label: 'Scanners', icon: markRaw(ScanLine) },
  { to: '/calculator', label: 'Calculators', icon: markRaw(Calculator) },
  { to: '/settings', label: 'Settings', icon: markRaw(Settings) },
]

// Confirm dialog state — queue-based to prevent race conditions
const confirmDialogOpen = ref(false)
const confirmDialogMessage = ref('')

interface ConfirmRequest {
  message: string
  resolve: (value: boolean) => void
}

const confirmQueue: ConfirmRequest[] = []

function processConfirmQueue() {
  if (confirmDialogOpen.value || confirmQueue.length === 0) return
  const next = confirmQueue[0]
  confirmDialogMessage.value = next.message
  confirmDialogOpen.value = true
}

const showConfirmDialog = (message: string, resolve: (value: boolean) => void): void => {
  confirmQueue.push({ message, resolve })
  processConfirmQueue()
}

const handleConfirmDialogResponse = (confirmed: boolean) => {
  confirmDialogOpen.value = false
  const current = confirmQueue.shift()
  if (current) {
    current.resolve(confirmed)
  }
  // Show next queued dialog, if any
  processConfirmQueue()
}

// ---- Batch helpers ----
const handleBatchScanId = (id: string, batchType: string) => {
  const parsed = BatchTypeSchema.safeParse(typeof batchType === 'string' ? JSON.parse(batchType) : batchType)
  if (parsed.success) {
    switch (parsed.data.type) {
      case 'Alliance': allianceStore.scanID = id; break
      case 'Honor': honorStore.scanID = id; break
      case 'Seed': seedStore.scanID = id; break
    }
  }
}

const handleBatchUpdate = (governorData: unknown, extraData: unknown, batchType: string) => {
  const parsed = BatchTypeSchema.safeParse(typeof batchType === 'string' ? JSON.parse(batchType) : batchType)
  if (parsed.success) {
    const govParsed = BatchGovernorDataListSchema.parse(governorData)
    const extraParsed = BatchAdditionalDataSchema.parse(extraData)
    switch (parsed.data.type) {
      case 'Alliance':
        allianceStore.lastGovernor = govParsed
        allianceStore.status = extraParsed
        break
      case 'Honor':
        honorStore.lastGovernor = govParsed
        honorStore.status = extraParsed
        break
      case 'Seed':
        seedStore.lastGovernor = govParsed
        seedStore.status = extraParsed
        break
    }
  }
}

const handleBatchStateUpdate = (state: string, batchType: string) => {
  const parsed = BatchTypeSchema.safeParse(typeof batchType === 'string' ? JSON.parse(batchType) : batchType)
  if (parsed.success) {
    switch (parsed.data.type) {
      case 'Alliance': allianceStore.statusMessage = state; break
      case 'Honor': honorStore.statusMessage = state; break
      case 'Seed': seedStore.statusMessage = state; break
    }
  }
}

const handleBatchScanFinished = (batchType: string) => {
  const parsed = BatchTypeSchema.safeParse(typeof batchType === 'string' ? JSON.parse(batchType) : batchType)
  if (parsed.success) {
    switch (parsed.data.type) {
      case 'Alliance':
        allianceStore.scanRunning = false
        allianceStore.startButtonDisabled = false
        break
      case 'Honor':
        honorStore.scanRunning = false
        honorStore.startButtonDisabled = false
        break
      case 'Seed':
        seedStore.scanRunning = false
        seedStore.startButtonDisabled = false
        break
    }
  }
}

// ---- Sidecar event listeners ----
const unlisteners: Array<() => void> = []

async function init() {
  unlisteners.push(await onSidecarEvent('config_loaded', (data) => {
    const parsed = FullConfigSchema.safeParse(data)
    if (parsed.success) {
      configStore.config = parsed.data
      configStore.configLoaded = true
    } else {
      console.warn('Failed to parse loaded config:', parsed.error)
    }
  }))

  unlisteners.push(await onSidecarEvent('presets_loaded', (data) => {
    const parsed = KingdomPresetListSchema.safeParse(data)
    if (parsed.success && parsed.data.length > 0) configStore.availableScanPresets = parsed.data
  }))

  unlisteners.push(await onSidecarEvent('batch_scan_id', (data) => {
    handleBatchScanId(data.id, data.type)
  }))

  unlisteners.push(await onSidecarEvent('batch_update', (data) => {
    handleBatchUpdate(data.gov, data.extra, data.type)
  }))

  unlisteners.push(await onSidecarEvent('batch_state_update', (data) => {
    handleBatchStateUpdate(data.msg, data.type)
  }))

  unlisteners.push(await onSidecarEvent('batch_ask_confirm', (data) => {
    const typeVal = data.type
    const parsed = BatchTypeSchema.safeParse(typeof typeVal === 'string' ? JSON.parse(typeVal) : typeVal)
    showConfirmDialog(data.msg, (confirmed: boolean) => {
      if (parsed.success) ipc.confirmBatchScan(confirmed, parsed.data.type)
    })
  }))

  unlisteners.push(await onSidecarEvent('batch_scan_finished', (data) => {
    handleBatchScanFinished(typeof data === 'string' ? data : JSON.stringify(data))
  }))

  // Global error handler for sidecar errors
  unlisteners.push(await onSidecarEvent('error', (data) => {
    console.error('Sidecar error:', data)
    
    // Fallback toast for the log history
    toast({
      title: 'Backend Error',
      description: String(data),
      variant: 'destructive',
    })

    // Analyze and show the smart error dialog
    const errorString = String(data)
    const { title, suggestion } = analyzeError(errorString)
    errorStore.showError(title, errorString, suggestion)
  }))

  // Surface Python stderr output in the console for debugging
  unlisteners.push(await onSidecarEvent('stderr', (data) => {
    console.warn('[sidecar stderr]', data)
  }))

  // Wait for the sidecar "ready" signal before sending any commands.
  // The Python sidecar emits {"event":"ready"} once its main loop starts.
  try {
    await new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        // If we time out, try loading anyway — sidecar may already be ready
        console.warn('[init] Sidecar ready timeout — proceeding anyway')
        resolve()
      }, 3000)

      onSidecarEvent('ready', () => {
        clearTimeout(timeout)
        resolve()
      }).then((unsub) => {
        unlisteners.push(unsub)
      })
    })
  } catch {
    // proceed anyway
  }

  // Load config and presets via sidecar
  await ipc.loadFullConfig()
  await ipc.loadScanPresets()
}

onMounted(() => {
  init()
})

onUnmounted(() => {
  unlisteners.forEach((fn) => fn())
})
</script>
