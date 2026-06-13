<template>
  <TooltipProvider>
    <Card class="flex flex-col">
      <CardHeader class="pb-2">
      <CardTitle>{{ kingdomStore.lastGovernor.name }} #{{ kingdomStore.status.current_governor }}</CardTitle>
      <CardDescription
        >with id
        <span class="font-medium text-primary">{{
          kingdomStore.lastGovernor.id
        }}</span></CardDescription
      >
    </CardHeader>

    <Separator />

    <CardContent class="overflow-auto py-3 px-4">
      <!-- General -->
      <div class="space-y-1 text-sm">
        <div class="flex justify-between">
          <span>Power</span>
          <span class="font-medium text-primary tabular-nums">{{
            formatNumber(kingdomStore.lastGovernor.power)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Killpoints</span>
          <span class="font-medium text-primary tabular-nums">{{
            formatNumber(kingdomStore.lastGovernor.killpoints)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Alliance</span>
          <span class="text-muted-foreground truncate ml-4 text-right">{{
            kingdomStore.lastGovernor.alliance
          }}</span>
        </div>
      </div>

      <!-- Kills & Economy — unified stats box -->
      <div
        class="mt-3 rounded-lg bg-muted/50 dark:bg-muted/25 p-3 border border-border/60 dark:border-border/40"
      >
        <div class="grid grid-cols-2 gap-x-5 gap-y-1 text-sm">
          <template v-for="stat in killStats" :key="stat.label">
            <div class="flex items-center justify-between gap-2">
              <span class="text-muted-foreground">{{ stat.label }}</span>
              <Tooltip>
                <TooltipTrigger as-child>
                  <span class="tabular-nums cursor-default">{{
                    formatCompactNumber(stat.value)
                  }}</span>
                </TooltipTrigger>
                <TooltipContent side="left">{{ formatNumber(stat.value) }}</TooltipContent>
              </Tooltip>
            </div>
          </template>
        </div>
        <Separator class="my-2.5" />
        <div class="flex items-center justify-between text-sm">
          <span class="font-medium">Deaths</span>
          <span class="font-medium text-primary tabular-nums">{{
            formatNumber(kingdomStore.lastGovernor.dead)
          }}</span>
        </div>
        <Separator class="my-2.5" />
        <div class="grid grid-cols-2 gap-x-5 gap-y-1 text-sm">
          <template v-for="stat in econStats" :key="stat.label">
            <div class="flex items-center justify-between gap-2">
              <span class="text-muted-foreground">{{ stat.label }}</span>
              <Tooltip>
                <TooltipTrigger as-child>
                  <span class="tabular-nums cursor-default">{{
                    formatCompactNumber(stat.value)
                  }}</span>
                </TooltipTrigger>
                <TooltipContent side="left">{{ formatNumber(stat.value) }}</TooltipContent>
              </Tooltip>
            </div>
          </template>
        </div>
      </div>

      <!-- City Hall — standalone -->
      <div class="mt-3 flex items-center justify-between text-sm">
        <span class="font-medium">City Hall</span>
        <span class="font-medium text-primary tabular-nums">{{
          kingdomStore.lastGovernor.city_hall_level
        }}</span>
      </div>
    </CardContent>

    <Separator />

    <CardFooter class="flex-col gap-1.5 py-2.5 px-4">
      <!-- Progress percentage + counts -->
      <div class="flex w-full items-center justify-between text-sm">
        <span class="font-semibold text-primary tabular-nums">{{ progressPercent }}%</span>
        <span class="text-muted-foreground tabular-nums">
          {{ kingdomStore.status.current_governor }} / {{ kingdomStore.status.target_governor }}
        </span>
      </div>
      <!-- Progress bar -->
      <Progress
        :model-value="progressValue"
        class="w-full h-2.5 transition-all duration-500 ease-out"
      />

      <!-- Scan speed — inline row with dot separators, slightly emphasized -->
      <div
        class="flex w-full items-center justify-center rounded-md bg-muted/40 dark:bg-muted/20 py-1.5 text-xs tabular-nums mt-1"
      >
        <Tooltip>
          <TooltipTrigger as-child>
            <span class="text-primary font-medium cursor-help">{{
              kingdomStore.status.avg_time_per_governor > 0
                ? kingdomStore.status.avg_time_per_governor.toFixed(1) + 's/gov'
                : '—'
            }}</span>
          </TooltipTrigger>
          <TooltipContent>Average time to scan each governor</TooltipContent>
        </Tooltip>
        <span class="text-muted-foreground/40 mx-2">•</span>
        <Tooltip>
          <TooltipTrigger as-child>
            <span class="text-primary font-medium cursor-help">{{
              kingdomStore.status.scan_speed_per_hour > 0
                ? Math.round(kingdomStore.status.scan_speed_per_hour) + '/hr'
                : '—'
            }}</span>
          </TooltipTrigger>
          <TooltipContent>Governors scanned per hour</TooltipContent>
        </Tooltip>
        <span class="text-muted-foreground/40 mx-2">•</span>
        <Tooltip>
          <TooltipTrigger as-child>
            <span class="text-primary font-medium cursor-help">{{
              kingdomStore.status.elapsed_sec > 0
                ? formatDuration(kingdomStore.status.elapsed_sec)
                : '—'
            }}</span>
          </TooltipTrigger>
          <TooltipContent>Total elapsed scan time</TooltipContent>
        </Tooltip>
      </div>

      <!-- Time info row — short labels to avoid wrapping -->
      <div class="flex w-full items-center justify-between text-xs mt-0.5">
        <Tooltip>
          <TooltipTrigger as-child>
            <span class="text-muted-foreground cursor-help">
              <UseTimeAgo v-slot="{ timeAgo }" :time="lastUpdate">{{ timeAgo }}</UseTimeAgo>
            </span>
          </TooltipTrigger>
          <TooltipContent>Last Update: {{ lastUpdateFormatted }}</TooltipContent>
        </Tooltip>
        <span class="text-muted-foreground/60 tabular-nums">
          {{ kingdomStore.status.skipped_governors }}
          {{ kingdomStore.status.skipped_governors === 1 ? 'skip' : 'skips' }}
        </span>
        <Tooltip>
          <TooltipTrigger as-child>
            <span class="text-muted-foreground cursor-help">
              ETA
              <UseTimeAgo
                v-slot="{ timeAgo }"
                :time="expectedFinish"
                :show-second="true"
                :update-interval="1000"
                >{{ timeAgo }}</UseTimeAgo
              >
            </span>
          </TooltipTrigger>
          <TooltipContent>{{ expectedFinishFormatted }}</TooltipContent>
        </Tooltip>
      </div>

      <!-- CH Verification Progress -->
      <div v-if="kingdomStore.status.ch_verification_mode" class="w-full mt-1 space-y-1">
        <div class="flex justify-between text-xs text-muted-foreground">
          <span>CH Verification</span>
          <span
            >{{ kingdomStore.status.ch_current_governor }} /
            {{ kingdomStore.status.ch_total_governors }}</span
          >
        </div>
        <Progress
          :model-value="
            (kingdomStore.status.ch_current_governor / kingdomStore.status.ch_total_governors) * 100
          "
          class="w-full h-1.5"
        />
      </div>
    </CardFooter>
    </Card>
  </TooltipProvider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { UseTimeAgo } from '@vueuse/components'
import { useDateFormat } from '@vueuse/core'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import { useKingdomStore } from '@/stores/kingdom-store'
import { formatNumber, formatCompactNumber, formatDuration } from '@/util/format'

const kingdomStore = useKingdomStore()

const lastUpdate = computed(() => new Date(kingdomStore.status.current_time))
const expectedFinish = computed(
  () => new Date(Date.now() + kingdomStore.status.remaining_sec * 1000),
)

const lastUpdateFormatted = useDateFormat(lastUpdate, 'HH:mm:ss')
const expectedFinishFormatted = useDateFormat(expectedFinish, 'HH:mm:ss')

const killStats = computed(() => [
  { label: 'T1 Kills', value: kingdomStore.lastGovernor.t1_kills },
  { label: 'T2 Kills', value: kingdomStore.lastGovernor.t2_kills },
  { label: 'T3 Kills', value: kingdomStore.lastGovernor.t3_kills },
  { label: 'T4 Kills', value: kingdomStore.lastGovernor.t4_kills },
  { label: 'T5 Kills', value: kingdomStore.lastGovernor.t5_kills },
  { label: 'Ranged', value: kingdomStore.lastGovernor.ranged_points },
])

const econStats = computed(() => [
  { label: 'Assisted', value: kingdomStore.lastGovernor.rss_assistance },
  { label: 'Helps', value: kingdomStore.lastGovernor.helps },
  { label: 'Gathered', value: kingdomStore.lastGovernor.rss_gathered },
])

const progressValue = computed(() => {
  if (kingdomStore.status.target_governor <= 0) return 0
  return (kingdomStore.status.current_governor / kingdomStore.status.target_governor) * 100
})

const progressPercent = computed(() => {
  return Math.min(100, Math.round(progressValue.value))
})
</script>
