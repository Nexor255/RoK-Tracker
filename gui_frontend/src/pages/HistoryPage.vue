<template>
  <div class="flex h-full flex-col gap-4 relative">
    <!-- Compare View -->
    <template v-if="historyStore.compareResult">
      <ScanCompare
        :result="historyStore.compareResult"
        :scan-entry-a="compareEntryA"
        :scan-entry-b="compareEntryB"
        @back="historyStore.clearCompare()"
      />
    </template>

    <!-- Detail View -->
    <template v-else-if="historyStore.selectedDetail">
      <ScanHistoryDetail
        :detail="historyStore.selectedDetail"
        :scan-entry="selectedScanEntry"
        @back="historyStore.clearDetail()"
        @open-folder="handleOpenFolder"
        @page-change="handlePageChange"
      />
    </template>

    <!-- List View -->
    <div v-else class="flex flex-col gap-4 h-full">
      <TooltipProvider :delay-duration="300">
      <!-- Mount error display -->
      <div v-if="mountError" class="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
        <p class="font-semibold mb-1">History page error</p>
        <p>{{ mountError }}</p>
      </div>
      <!-- Page header with stats -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-bold tracking-tight">Scan History</h1>
          <p class="text-sm text-muted-foreground mt-0.5">
            {{ historyStore.totalCount }} scan{{ historyStore.totalCount !== 1 ? 's' : '' }} on disk
          </p>
        </div>

        <div class="flex items-center gap-2">
          <!-- Type counts -->
          <div class="hidden md:flex items-center gap-1.5 mr-2">
            <Tooltip v-for="(count, type) in historyStore.countByType" :key="type">
              <TooltipTrigger as-child>
                <div
                  v-if="count > 0"
                  class="flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium border"
                  :class="typeChipStyles[type]"
                >
                  <component :is="typeChipIcons[type]" class="h-3 w-3" />
                  {{ count }}
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p class="text-xs capitalize">{{ type }} scans</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <!-- Compare toggle -->
          <Button
            :variant="historyStore.compareMode ? 'default' : 'outline'"
            size="sm"
            @click="toggleCompareMode"
          >
            <GitCompareArrows class="h-4 w-4 mr-1.5" />
            {{ historyStore.compareMode ? 'Cancel' : 'Compare' }}
          </Button>

          <Button variant="outline" size="sm" @click="refreshHistory" :disabled="historyStore.loading">
            <RefreshCw class="h-4 w-4 mr-1.5" :class="{ 'animate-spin': historyStore.loading }" />
            Refresh
          </Button>
        </div>
      </div>

      <!-- Compare bar (shown when compare mode is active) -->
      <div
        v-if="historyStore.compareMode"
        class="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-2.5 transition-all"
      >
        <GitCompareArrows class="h-4 w-4 text-primary shrink-0" />
        <span class="text-sm text-muted-foreground">
          Select 2 <span class="font-medium text-foreground">kingdom</span> scans to compare
        </span>
        <div class="flex-1" />
        <div class="flex items-center gap-2">
          <Badge
            v-for="path in historyStore.compareSelections"
            :key="path"
            variant="secondary"
            class="text-xs"
          >
            {{ getEntryLabel(path) }}
            <button
              class="ml-1 hover:text-destructive transition-colors"
              @click="historyStore.toggleCompareSelection(path)"
            >
              ×
            </button>
          </Badge>
          <span v-if="historyStore.compareSelections.length < 2" class="text-xs text-muted-foreground">
            {{ 2 - historyStore.compareSelections.length }} more needed
          </span>
        </div>
        <Button
          size="sm"
          :disabled="historyStore.compareSelections.length !== 2"
          @click="handleCompare"
          class="h-7"
        >
          Compare Now
        </Button>
      </div>

      <!-- Filter bar -->
      <div class="flex items-center gap-3">
        <div class="relative flex-1 max-w-sm">
          <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            v-model="historyStore.searchQuery"
            placeholder="Search by name, ID..."
            class="flex h-9 w-full rounded-md border border-input bg-transparent pl-8 pr-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>

        <Select v-model="historyStore.filterType">
          <SelectTrigger class="w-[140px] h-9">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="kingdom">Kingdom</SelectItem>
            <SelectItem value="alliance">Alliance</SelectItem>
            <SelectItem value="honor">Honor</SelectItem>
            <SelectItem value="seed">Seed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <!-- Scan list (scrollable) -->
      <div class="flex-1 overflow-y-auto scrollbar-hidden -mx-1 px-1 pb-2">
          <ScanHistoryList
            :filtered-history="historyStore.filteredHistory"
            :grouped-by-date="historyStore.groupedByDate"
            :loading="historyStore.loading"
            :search-query="historyStore.searchQuery"
            :filter-type="historyStore.filterType"
            :compare-mode="historyStore.compareMode"
            :compare-selections="historyStore.compareSelections"
            @open-folder="handleOpenFolder"
            @delete="handleDelete"
            @view="handleViewDetail"
            @toggle-compare="historyStore.toggleCompareSelection($event)"
          />
      </div>
      </TooltipProvider>
    </div>

    <!-- Loading overlay -->
    <transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="historyStore.detailLoading || historyStore.compareLoading"
        class="absolute inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-background/60 backdrop-blur-sm rounded-lg"
      >
        <svg class="h-8 w-8 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span class="text-sm text-muted-foreground">
          {{ historyStore.compareLoading ? 'Comparing scans…' : 'Loading scan data…' }}
        </span>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'HistoryPage' })
import { ref, computed, onMounted, onUnmounted, markRaw } from 'vue'
import { Crown, Shield, Award, Sprout, Search, RefreshCw, GitCompareArrows } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from '@/components/ui/tooltip'
import ScanHistoryList from '@/components/ScanHistoryList.vue'
import ScanHistoryDetail from '@/components/ScanHistoryDetail.vue'
import ScanCompare from '@/components/ScanCompare.vue'
import { useHistoryStore } from '@/stores/history-store'
import { onSidecarEvent } from '@/lib/tauriClient'
import * as ipc from '@/lib/tauriClient'
import { toast } from '@/components/ui/toast'

const historyStore = useHistoryStore()

// Track which scan entry is being viewed (for header info)
const viewingPath = ref<string | null>(null)

const selectedScanEntry = computed(() => {
  if (!viewingPath.value) return null
  return historyStore.scanHistory.find((s) => s.path === viewingPath.value) ?? null
})

// Compare entry lookups
const compareEntryA = computed(() => {
  const path = historyStore.compareSelections[0]
  return path ? historyStore.scanHistory.find((s) => s.path === path) ?? null : null
})

const compareEntryB = computed(() => {
  const path = historyStore.compareSelections[1]
  return path ? historyStore.scanHistory.find((s) => s.path === path) ?? null : null
})

function getEntryLabel(path: string): string {
  const entry = historyStore.scanHistory.find((s) => s.path === path)
  if (!entry) return 'Unknown'
  return `${entry.prefix} ${entry.governor_count} · ${entry.kingdom_name}`
}

// Type chip styles for the header counters
const typeChipStyles: Record<string, string> = {
  kingdom: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  alliance: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
  honor: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
  seed: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20',
}

const typeChipIcons: Record<string, ReturnType<typeof markRaw>> = {
  kingdom: markRaw(Crown),
  alliance: markRaw(Shield),
  honor: markRaw(Award),
  seed: markRaw(Sprout),
}

function refreshHistory() {
  historyStore.loading = true
  ipc.listScanHistory()
}

function handleOpenFolder(path: string) {
  ipc.openScanFolder(path)
}

function handleDelete(path: string) {
  ipc.deleteScanFile(path)
}

function handleViewDetail(path: string) {
  viewingPath.value = path
  historyStore.detailLoading = true
  ipc.getScanDetail(path)
}

function handlePageChange(page: number) {
  if (!viewingPath.value) return
  historyStore.detailLoading = true
  ipc.getScanDetail(viewingPath.value, page)
}

function toggleCompareMode() {
  if (historyStore.compareMode) {
    historyStore.clearCompare()
  } else {
    historyStore.compareMode = true
    historyStore.compareSelections = []
  }
}

function handleCompare() {
  if (historyStore.compareSelections.length !== 2) return
  historyStore.compareLoading = true
  ipc.compareScanFiles(historyStore.compareSelections[0], historyStore.compareSelections[1])
}

// ---- Sidecar event listeners ----
const unlisteners: Array<() => void> = []
const mountError = ref<string | null>(null)

onMounted(async () => {
  try {
    // Listen for scan history list response
    unlisteners.push(
      await onSidecarEvent('scan_history_list', (data) => {
        historyStore.scanHistory = data
        historyStore.loading = false
      }),
    )

    // Listen for scan detail response
    unlisteners.push(
      await onSidecarEvent('scan_detail', (data) => {
        historyStore.selectedDetail = data
        historyStore.detailLoading = false
      }),
    )

    // Listen for compare result
    unlisteners.push(
      await onSidecarEvent('scan_compare_result', (data) => {
        historyStore.compareResult = data
        historyStore.compareLoading = false
      }),
    )

    // Listen for file deletion confirmation
    unlisteners.push(
      await onSidecarEvent('scan_file_deleted', (path) => {
        historyStore.removeScan(path)
        toast({
          title: 'Scan deleted',
          description: 'The scan file has been removed.',
        })
      }),
    )

    // Initial load
    refreshHistory()
  } catch (e) {
    console.error('[HistoryPage] mount error:', e)
    mountError.value = String(e)
    historyStore.loading = false
  }
})

onUnmounted(() => {
  unlisteners.forEach((fn) => fn())
})
</script>
