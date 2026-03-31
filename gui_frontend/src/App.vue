<template>
  <div class="flex h-screen flex-col">
    <!-- Header -->
    <header class="sticky top-0 z-40 flex h-14 items-center gap-4 border-b bg-primary px-6 text-primary-foreground">
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
      <nav class="flex w-[120px] flex-col items-center gap-1 border-r bg-muted/40 p-2 overflow-y-auto scrollbar-hidden">
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
      <main class="flex-1 overflow-auto scrollbar-hidden p-4">
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

    <!-- Update notifier -->
    <UpdateNotifier />
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
import { Radar, ScanLine, Calculator, Settings } from 'lucide-vue-next'
import { onSidecarEvent } from '@/lib/tauriClient'
import * as ipc from '@/lib/ipcClient'

const configStore = useConfigStore()
const allianceStore = useAllianceStore()
const honorStore = useHonorStore()
const seedStore = useSeedStore()

const darkMode = useDark()
const toggleDarkMode = useToggle(darkMode)

const navItems = [
  { to: '/scanner', label: 'Scanners', icon: markRaw(ScanLine) },
  { to: '/calculator', label: 'Calculators', icon: markRaw(Calculator) },
  { to: '/settings', label: 'Settings', icon: markRaw(Settings) },
]

// Confirm dialog state
const confirmDialogOpen = ref(false)
const confirmDialogMessage = ref('')
let confirmDialogResolve: ((value: boolean) => void) | null = null

const showConfirmDialog = (message: string): void => {
  confirmDialogMessage.value = message
  confirmDialogOpen.value = true
}

const handleConfirmDialogResponse = (confirmed: boolean) => {
  confirmDialogOpen.value = false
  if (confirmDialogResolve) {
    confirmDialogResolve(confirmed)
    confirmDialogResolve = null
  }
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
    const govStr = typeof governorData === 'string' ? governorData : JSON.stringify(governorData)
    const extraStr = typeof extraData === 'string' ? extraData : JSON.stringify(extraData)
    switch (parsed.data.type) {
      case 'Alliance':
        allianceStore.lastGovernor = BatchGovernorDataListSchema.parse(JSON.parse(govStr))
        allianceStore.status = BatchAdditionalDataSchema.parse(JSON.parse(extraStr))
        break
      case 'Honor':
        honorStore.lastGovernor = BatchGovernorDataListSchema.parse(JSON.parse(govStr))
        honorStore.status = BatchAdditionalDataSchema.parse(JSON.parse(extraStr))
        break
      case 'Seed':
        seedStore.lastGovernor = BatchGovernorDataListSchema.parse(JSON.parse(govStr))
        seedStore.status = BatchAdditionalDataSchema.parse(JSON.parse(extraStr))
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
    } else {
      console.warn('Failed to parse loaded config:', parsed.error)
    }
  }))

  unlisteners.push(await onSidecarEvent('presets_loaded', (data) => {
    const parsed = KingdomPresetListSchema.safeParse(data)
    if (parsed.success && parsed.data.length > 0) configStore.availableScanPresets = parsed.data
  }))

  unlisteners.push(await onSidecarEvent('batch_scan_id', (data) => {
    const d = data as Record<string, unknown>
    handleBatchScanId(d.id as string, d.type as string)
  }))

  unlisteners.push(await onSidecarEvent('batch_update', (data) => {
    const d = data as Record<string, unknown>
    handleBatchUpdate(d.gov, d.extra, d.type as string)
  }))

  unlisteners.push(await onSidecarEvent('batch_state_update', (data) => {
    const d = data as Record<string, unknown>
    handleBatchStateUpdate(d.msg as string, d.type as string)
  }))

  unlisteners.push(await onSidecarEvent('batch_ask_confirm', (data) => {
    const d = data as Record<string, unknown>
    showConfirmDialog(d.msg as string)
    confirmDialogResolve = (confirmed: boolean) => {
      const typeVal = d.type as string
      const parsed = BatchTypeSchema.safeParse(typeof typeVal === 'string' ? JSON.parse(typeVal) : typeVal)
      if (parsed.success) ipc.confirmBatchScan(confirmed, JSON.stringify(parsed.data))
    }
  }))

  unlisteners.push(await onSidecarEvent('batch_scan_finished', (data) => {
    handleBatchScanFinished(typeof data === 'string' ? data : JSON.stringify(data))
  }))

  // Global error handler for sidecar errors
  unlisteners.push(await onSidecarEvent('error', (data) => {
    console.error('Sidecar error:', data)
    toast({
      title: 'Backend Error',
      description: String(data),
      variant: 'destructive',
    })
  }))

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
