<template>
  <Card class="flex h-full flex-col">
    <CardHeader class="pb-2">
      <CardTitle>Screen {{ batchStatus.current_page }}</CardTitle>
      <CardDescription>of {{ Math.ceil(batchStatus.target_governor / batchStatus.govs_per_page) }}</CardDescription>
    </CardHeader>

    <Separator />

    <CardContent class="flex-1 overflow-auto py-3 px-4">
      <!-- Governors — boxed like Kingdom kills -->
      <div class="rounded-lg bg-muted/50 dark:bg-muted/25 p-3 border border-border/60 dark:border-border/40">
        <div class="space-y-1 text-sm">
          <div v-for="gov in batchData" :key="gov.img_path" class="flex items-center justify-between gap-2">
            <span class="truncate">{{ gov.name }}</span>
            <span class="text-muted-foreground tabular-nums shrink-0">{{ formatNumber(gov.score) }}</span>
          </div>
        </div>
      </div>
    </CardContent>

    <Separator />

    <CardFooter class="flex-col gap-1.5 py-2.5 px-4">
      <!-- Progress percentage + counts -->
      <div class="flex w-full items-center justify-between text-sm">
        <span class="font-semibold text-primary tabular-nums">{{ progressPercent }}%</span>
        <span class="text-muted-foreground tabular-nums">
          {{ batchStatus.current_page * batchStatus.govs_per_page }} / {{ batchStatus.target_governor }}
        </span>
      </div>
      <!-- Progress bar -->
      <Progress
        :model-value="progressValue"
        class="w-full h-2.5 transition-all duration-500 ease-out"
      />

      <!-- Time info row -->
      <div class="flex w-full items-center justify-between text-xs mt-0.5">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <span class="text-muted-foreground cursor-help">
                <UseTimeAgo v-slot="{ timeAgo }" :time="lastUpdate">{{ timeAgo }}</UseTimeAgo>
              </span>
            </TooltipTrigger>
            <TooltipContent>Last Update: {{ lastUpdateFormatted }}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
        <TooltipProvider>
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
        </TooltipProvider>
      </div>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { UseTimeAgo } from '@vueuse/components'
import { useDateFormat } from '@vueuse/core'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import type { BatchAdditionalData } from '@/schema/BatchAdditionalData'
import type { BatchGovernorData } from '@/schema/BatchGovernorData'
import { formatNumber } from '@/util/format'

const props = defineProps<{
  batchData: BatchGovernorData[]
  batchStatus: BatchAdditionalData
}>()

const lastUpdate = computed(() => new Date(props.batchStatus.current_time))
const expectedFinish = computed(
  () => new Date(lastUpdate.value.getTime() + props.batchStatus.remaining_sec * 1000),
)

const lastUpdateFormatted = useDateFormat(lastUpdate, 'HH:mm:ss')
const expectedFinishFormatted = useDateFormat(expectedFinish, 'HH:mm:ss')

const progressValue = computed(() => {
  if (props.batchStatus.target_governor <= 0) return 0
  return ((props.batchStatus.current_page * props.batchStatus.govs_per_page) / props.batchStatus.target_governor) * 100
})

const progressPercent = computed(() => {
  return Math.min(100, Math.round(progressValue.value))
})
</script>
