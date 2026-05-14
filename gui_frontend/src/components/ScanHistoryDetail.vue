<template>
  <div class="flex h-full flex-col gap-4">
    <!-- Header with back button -->
    <div class="flex items-center gap-3">
      <button
        class="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        @click="$emit('back')"
      >
        <ArrowLeft class="h-4 w-4" />
        Back
      </button>
      <div class="h-5 w-px bg-border" />
      <div class="min-w-0">
        <h2 class="text-base font-semibold truncate">{{ scanEntry?.filename ?? 'Scan Detail' }}</h2>
        <p class="text-xs text-muted-foreground">
          {{ scanEntry?.kingdom_name }} · {{ scanEntry?.date }}
        </p>
      </div>
      <div class="flex-1" />
      <!-- Actions -->
      <div class="flex items-center gap-1.5">
        <Button variant="outline" size="sm" @click="$emit('open-folder', detail.path)">
          <FolderOpen class="h-4 w-4 mr-1.5" />
          Open Folder
        </Button>
      </div>
    </div>

    <!-- Summary Stats Cards -->
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
      <div
        v-for="stat in summaryStats"
        :key="stat.label"
        class="relative overflow-hidden rounded-lg border bg-card/80 backdrop-blur-sm p-3 transition-all duration-200 hover:shadow-md hover:border-primary/20"
      >
        <div class="flex items-center gap-2 mb-1">
          <div
            class="flex h-7 w-7 items-center justify-center rounded-md"
            :class="stat.bgClass"
          >
            <component :is="stat.icon" class="h-3.5 w-3.5" :class="stat.textClass" />
          </div>
          <span class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{{ stat.label }}</span>
        </div>
        <p class="text-lg font-bold tabular-nums">{{ stat.value }}</p>
        <p v-if="stat.sub" class="text-[10px] text-muted-foreground/70 mt-0.5">{{ stat.sub }}</p>
      </div>
    </div>

    <!-- Data Table -->
    <div class="flex-1 flex flex-col min-h-0 rounded-lg border bg-card/80 backdrop-blur-sm overflow-hidden">
      <!-- Table toolbar -->
      <div class="flex items-center justify-between border-b px-4 py-2 bg-muted/30">
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted-foreground">
            {{ detail.total_rows }} rows · Page {{ detail.page }} of {{ detail.total_pages }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <!-- Sort control -->
          <Select v-model="sortColumn">
            <SelectTrigger class="h-7 w-[130px] text-xs">
              <SelectValue placeholder="Sort by..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Default order</SelectItem>
              <SelectItem v-for="col in detail.columns" :key="col" :value="col">
                {{ col }}
              </SelectItem>
            </SelectContent>
          </Select>
          <button
            v-if="sortColumn !== '__none__'"
            class="rounded p-1 hover:bg-accent transition-colors"
            @click="sortDirection = sortDirection === 'asc' ? 'desc' : 'asc'"
          >
            <ArrowUpDown class="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        </div>
      </div>

      <!-- Scrollable table -->
      <div class="flex-1 overflow-auto scrollbar-hidden">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10">
            <tr class="bg-muted/60 backdrop-blur-md border-b">
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground w-10">#</th>
              <th
                v-for="col in detail.columns"
                :key="col"
                class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap cursor-pointer hover:text-foreground transition-colors"
                @click="handleColumnSort(col)"
              >
                <span class="flex items-center gap-1">
                  {{ col }}
                  <ArrowUp v-if="sortColumn === col && sortDirection === 'asc'" class="h-3 w-3" />
                  <ArrowDown v-else-if="sortColumn === col && sortDirection === 'desc'" class="h-3 w-3" />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in sortedRows"
              :key="idx"
              class="border-b border-border/30 hover:bg-accent/30 transition-colors"
            >
              <td class="px-3 py-1.5 text-xs text-muted-foreground tabular-nums">
                {{ (detail.page - 1) * detail.page_size + idx + 1 }}
              </td>
              <td
                v-for="col in detail.columns"
                :key="col"
                class="px-3 py-1.5 text-xs whitespace-nowrap tabular-nums"
              >
                {{ formatCellValue(row[col]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="detail.total_pages > 1" class="flex items-center justify-center gap-2 border-t px-4 py-2 bg-muted/20">
        <Button
          variant="outline"
          size="sm"
          :disabled="detail.page <= 1"
          class="h-7 text-xs"
          @click="$emit('page-change', detail.page - 1)"
        >
          <ChevronLeft class="h-3.5 w-3.5 mr-0.5" />
          Previous
        </Button>

        <div class="flex items-center gap-1">
          <button
            v-for="p in visiblePages"
            :key="p"
            class="h-7 w-7 rounded text-xs font-medium transition-colors"
            :class="p === detail.page
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-accent text-muted-foreground'"
            @click="$emit('page-change', p)"
          >
            {{ p }}
          </button>
        </div>

        <Button
          variant="outline"
          size="sm"
          :disabled="detail.page >= detail.total_pages"
          class="h-7 text-xs"
          @click="$emit('page-change', detail.page + 1)"
        >
          Next
          <ChevronRight class="h-3.5 w-3.5 ml-0.5" />
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, markRaw, type Component } from 'vue'
import {
  ArrowLeft,
  FolderOpen,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  Users,
  Zap,
  TrendingUp,
  Sword,
  Skull,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ScanDetailPayload, ScanHistoryEntry } from '@/types/ScanHistory'

const props = defineProps<{
  detail: ScanDetailPayload
  scanEntry: ScanHistoryEntry | null
}>()

defineEmits<{
  back: []
  'open-folder': [path: string]
  'page-change': [page: number]
}>()

// Sort state (client-side sort within the current page)
const sortColumn = ref('__none__')
const sortDirection = ref<'asc' | 'desc'>('asc')

function handleColumnSort(col: string) {
  if (sortColumn.value === col) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortDirection.value = 'asc'
  }
}

const sortedRows = computed(() => {
  const rows = [...props.detail.rows]
  if (sortColumn.value === '__none__') return rows

  const col = sortColumn.value
  const dir = sortDirection.value === 'asc' ? 1 : -1

  return rows.sort((a, b) => {
    const va = a[col]
    const vb = b[col]
    if (va == null && vb == null) return 0
    if (va == null) return 1
    if (vb == null) return -1
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    return String(va).localeCompare(String(vb)) * dir
  })
})

// Pagination: show at most 7 page buttons
const visiblePages = computed(() => {
  const total = props.detail.total_pages
  const current = props.detail.page
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

  const pages: number[] = []
  const start = Math.max(1, current - 3)
  const end = Math.min(total, start + 6)
  for (let i = Math.max(1, end - 6); i <= end; i++) {
    pages.push(i)
  }
  return pages
})

// Summary stats cards
function formatLargeNumber(n: number | null): string {
  if (n === null || n === undefined) return '—'
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return Math.round(n).toLocaleString()
}

interface StatCard {
  label: string
  value: string
  sub?: string
  icon: Component
  bgClass: string
  textClass: string
}

const summaryStats = computed<StatCard[]>(() => {
  const s = props.detail.summary
  return [
    {
      label: 'Governors',
      value: s.total_governors.toLocaleString(),
      icon: markRaw(Users),
      bgClass: 'bg-blue-500/10 dark:bg-blue-500/15',
      textClass: 'text-blue-600 dark:text-blue-400',
    },
    {
      label: 'Avg Power',
      value: formatLargeNumber(s.avg_power),
      sub: s.max_power !== null ? `Max: ${formatLargeNumber(s.max_power)}` : undefined,
      icon: markRaw(Zap),
      bgClass: 'bg-amber-500/10 dark:bg-amber-500/15',
      textClass: 'text-amber-600 dark:text-amber-400',
    },
    {
      label: 'Total Power',
      value: formatLargeNumber(s.total_power),
      icon: markRaw(TrendingUp),
      bgClass: 'bg-emerald-500/10 dark:bg-emerald-500/15',
      textClass: 'text-emerald-600 dark:text-emerald-400',
    },
    {
      label: 'Avg KP',
      value: formatLargeNumber(s.avg_killpoints),
      sub: s.max_killpoints !== null ? `Max: ${formatLargeNumber(s.max_killpoints)}` : undefined,
      icon: markRaw(Sword),
      bgClass: 'bg-red-500/10 dark:bg-red-500/15',
      textClass: 'text-red-600 dark:text-red-400',
    },
    {
      label: 'Avg Deaths',
      value: formatLargeNumber(s.avg_deaths),
      sub: s.total_kills !== null ? `Total Kills: ${formatLargeNumber(s.total_kills)}` : undefined,
      icon: markRaw(Skull),
      bgClass: 'bg-purple-500/10 dark:bg-purple-500/15',
      textClass: 'text-purple-600 dark:text-purple-400',
    },
  ]
})

// Cell value formatting
function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  return String(value)
}
</script>
