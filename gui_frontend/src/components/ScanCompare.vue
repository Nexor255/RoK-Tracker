<template>
  <div class="flex h-full flex-col gap-4">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <button
        class="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        @click="$emit('back')"
      >
        <ArrowLeft class="h-4 w-4" />
        Back
      </button>
      <div class="h-5 w-px bg-border" />
      <h2 class="text-base font-semibold">Scan Comparison</h2>
      <div class="flex-1" />
      <Badge variant="outline" class="text-xs">
        {{ scanEntryA?.filename ?? 'Scan A' }} vs {{ scanEntryB?.filename ?? 'Scan B' }}
      </Badge>
    </div>

    <!-- Summary comparison cards -->
    <div class="grid grid-cols-2 gap-4">
      <!-- Scan A summary -->
      <div class="rounded-lg border bg-card/80 backdrop-blur-sm p-4">
        <div class="flex items-center gap-2 mb-3">
          <div class="h-2 w-2 rounded-full bg-blue-500" />
          <span class="text-sm font-semibold truncate">{{ scanEntryA?.filename ?? 'Scan A' }}</span>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div v-for="stat in summaryStatsA" :key="stat.label">
            <p class="text-[10px] text-muted-foreground uppercase tracking-wider">{{ stat.label }}</p>
            <p class="text-sm font-bold tabular-nums">{{ stat.value }}</p>
          </div>
        </div>
      </div>

      <!-- Scan B summary -->
      <div class="rounded-lg border bg-card/80 backdrop-blur-sm p-4">
        <div class="flex items-center gap-2 mb-3">
          <div class="h-2 w-2 rounded-full bg-emerald-500" />
          <span class="text-sm font-semibold truncate">{{ scanEntryB?.filename ?? 'Scan B' }}</span>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div v-for="stat in summaryStatsB" :key="stat.label">
            <p class="text-[10px] text-muted-foreground uppercase tracking-wider">{{ stat.label }}</p>
            <p class="text-sm font-bold tabular-nums">{{ stat.value }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Delta overview -->
    <div class="flex items-center gap-4 text-sm">
      <div class="flex items-center gap-1.5 rounded-md bg-emerald-500/10 px-2.5 py-1 text-emerald-600 dark:text-emerald-400">
        <UserPlus class="h-3.5 w-3.5" />
        <span class="font-medium">{{ result.added.length }}</span>
        <span class="text-xs">added</span>
      </div>
      <div class="flex items-center gap-1.5 rounded-md bg-red-500/10 px-2.5 py-1 text-red-600 dark:text-red-400">
        <UserMinus class="h-3.5 w-3.5" />
        <span class="font-medium">{{ result.removed.length }}</span>
        <span class="text-xs">removed</span>
      </div>
      <div class="flex items-center gap-1.5 rounded-md bg-amber-500/10 px-2.5 py-1 text-amber-600 dark:text-amber-400">
        <ArrowUpDown class="h-3.5 w-3.5" />
        <span class="font-medium">{{ result.changed.length }}</span>
        <span class="text-xs">changed</span>
      </div>
    </div>

    <!-- Diff content tabs -->
    <Tabs v-model="activeTab" class="flex-1 flex flex-col min-h-0">
      <TabsList class="w-full justify-start rounded-none border-b bg-transparent p-0">
        <TabsTrigger
          value="changed"
          class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
        >
          Changed ({{ result.changed.length }})
        </TabsTrigger>
        <TabsTrigger
          value="added"
          class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
        >
          Added ({{ result.added.length }})
        </TabsTrigger>
        <TabsTrigger
          value="removed"
          class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
        >
          Removed ({{ result.removed.length }})
        </TabsTrigger>
      </TabsList>

      <!-- Changed tab -->
      <TabsContent value="changed" class="flex-1 overflow-auto scrollbar-hidden mt-0 pt-2">
        <div v-if="result.changed.length === 0" class="flex items-center justify-center py-12 text-sm text-muted-foreground">
          No changed governors
        </div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="(gov, idx) in result.changed"
            :key="idx"
            class="rounded-lg border bg-card/80 backdrop-blur-sm px-4 py-3"
          >
            <div class="flex items-center gap-2 mb-2">
              <span class="text-sm font-semibold">{{ gov.name || gov[result.join_key ?? 'ID'] }}</span>
              <Badge variant="outline" class="text-[10px] px-1.5 py-0 h-4">
                {{ Object.keys(gov.changes).length }} field{{ Object.keys(gov.changes).length !== 1 ? 's' : '' }}
              </Badge>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              <div
                v-for="(change, field) in gov.changes"
                :key="field"
                class="rounded-md bg-muted/30 px-2.5 py-1.5"
              >
                <p class="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">{{ field }}</p>
                <div class="flex items-center gap-1.5 text-xs tabular-nums">
                  <span class="text-red-500 dark:text-red-400 line-through">{{ formatVal(change.old) }}</span>
                  <ArrowRight class="h-3 w-3 text-muted-foreground shrink-0" />
                  <span class="text-emerald-600 dark:text-emerald-400 font-medium">{{ formatVal(change.new) }}</span>
                  <span
                    v-if="typeof change.old === 'number' && typeof change.new === 'number'"
                    class="text-[10px] ml-auto"
                    :class="(change.new as number) > (change.old as number) ? 'text-emerald-500' : 'text-red-500'"
                  >
                    {{ formatDelta(change.old as number, change.new as number) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </TabsContent>

      <!-- Added tab -->
      <TabsContent value="added" class="flex-1 overflow-auto scrollbar-hidden mt-0 pt-2">
        <div v-if="result.added.length === 0" class="flex items-center justify-center py-12 text-sm text-muted-foreground">
          No new governors
        </div>
        <div v-else class="rounded-lg border overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-muted/60 border-b">
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">#</th>
                <th
                  v-for="col in addedColumns"
                  :key="col"
                  class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap"
                >
                  {{ col }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in result.added"
                :key="idx"
                class="border-b border-border/30 bg-emerald-500/5"
              >
                <td class="px-3 py-1.5 text-xs text-muted-foreground tabular-nums">{{ idx + 1 }}</td>
                <td
                  v-for="col in addedColumns"
                  :key="col"
                  class="px-3 py-1.5 text-xs whitespace-nowrap tabular-nums"
                >
                  {{ formatVal(row[col]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </TabsContent>

      <!-- Removed tab -->
      <TabsContent value="removed" class="flex-1 overflow-auto scrollbar-hidden mt-0 pt-2">
        <div v-if="result.removed.length === 0" class="flex items-center justify-center py-12 text-sm text-muted-foreground">
          No removed governors
        </div>
        <div v-else class="rounded-lg border overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-muted/60 border-b">
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">#</th>
                <th
                  v-for="col in removedColumns"
                  :key="col"
                  class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap"
                >
                  {{ col }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in result.removed"
                :key="idx"
                class="border-b border-border/30 bg-red-500/5"
              >
                <td class="px-3 py-1.5 text-xs text-muted-foreground tabular-nums">{{ idx + 1 }}</td>
                <td
                  v-for="col in removedColumns"
                  :key="col"
                  class="px-3 py-1.5 text-xs whitespace-nowrap tabular-nums"
                >
                  {{ formatVal(row[col]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpDown,
  UserPlus,
  UserMinus,
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import type { ScanComparePayload, ScanHistoryEntry, ScanSummary } from '@/types/ScanHistory'

const props = defineProps<{
  result: ScanComparePayload
  scanEntryA: ScanHistoryEntry | null
  scanEntryB: ScanHistoryEntry | null
}>()

defineEmits<{
  back: []
}>()

const activeTab = ref('changed')

function formatLargeNumber(n: number | null): string {
  if (n === null || n === undefined) return '—'
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return Math.round(n).toLocaleString()
}

function makeSummaryStats(summary: ScanSummary) {
  return [
    { label: 'Governors', value: summary.total_governors.toLocaleString() },
    { label: 'Avg Power', value: formatLargeNumber(summary.avg_power) },
    { label: 'Max Power', value: formatLargeNumber(summary.max_power) },
    { label: 'Avg KP', value: formatLargeNumber(summary.avg_killpoints) },
    { label: 'Total Kills', value: formatLargeNumber(summary.total_kills) },
    { label: 'Avg Deaths', value: formatLargeNumber(summary.avg_deaths) },
  ]
}

const summaryStatsA = computed(() => makeSummaryStats(props.result.summary_a))
const summaryStatsB = computed(() => makeSummaryStats(props.result.summary_b))

// Columns for added/removed tables
const addedColumns = computed(() => {
  if (props.result.added.length === 0) return []
  return Object.keys(props.result.added[0])
})

const removedColumns = computed(() => {
  if (props.result.removed.length === 0) return []
  return Object.keys(props.result.removed[0])
})

function formatVal(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  return String(value)
}

function formatDelta(oldVal: number, newVal: number): string {
  const diff = newVal - oldVal
  const prefix = diff > 0 ? '+' : ''
  if (Math.abs(diff) >= 1_000_000) return `${prefix}${(diff / 1_000_000).toFixed(1)}M`
  if (Math.abs(diff) >= 1_000) return `${prefix}${(diff / 1_000).toFixed(1)}K`
  return `${prefix}${diff.toLocaleString()}`
}
</script>
