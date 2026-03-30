<template>
  <Card class="flex h-full flex-col">
    <CardHeader class="pb-2">
      <CardTitle>{{ kingdomStore.lastGovernor.name }}</CardTitle>
      <CardDescription>with id {{ kingdomStore.lastGovernor.id }}</CardDescription>
    </CardHeader>

    <Separator />

    <CardContent class="flex-1 overflow-auto py-3">
      <div class="space-y-1 text-sm">
        <div class="flex justify-between">
          <span>Power</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.power)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Killpoints</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.killpoints)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Alliance</span
          ><span class="text-muted-foreground">{{ kingdomStore.lastGovernor.alliance }}</span>
        </div>

        <Separator class="my-2" />

        <div class="flex justify-between">
          <span>T1 Kills</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.t1_kills)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>T2 Kills</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.t2_kills)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>T3 Kills</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.t3_kills)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>T4 Kills</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.t4_kills)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>T5 Kills</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.t5_kills)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Ranged Points</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.ranged_points)
          }}</span>
        </div>

        <Separator class="my-2" />

        <div class="flex justify-between">
          <span>Deaths</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.dead)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Assisted</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.rss_assistance)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Gathered</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.rss_gathered)
          }}</span>
        </div>
        <div class="flex justify-between">
          <span>Helps</span
          ><span class="text-muted-foreground">{{
            formatNumber(kingdomStore.lastGovernor.helps)
          }}</span>
        </div>
        <div v-if="kingdomStore.lastGovernor.city_hall_level > 0" class="flex justify-between">
          <span>City Hall</span
          ><span class="font-medium text-primary">Lv. {{ kingdomStore.lastGovernor.city_hall_level }}</span>
        </div>
      </div>
    </CardContent>

    <Separator />

    <CardFooter class="flex-col gap-2 py-3">
      <div class="flex w-full justify-between text-sm">
        <TooltipProvider>
          <div class="text-left">
            <div>Last Update</div>
            <Tooltip>
              <TooltipTrigger as-child>
                <span class="text-muted-foreground cursor-help">
                  <UseTimeAgo v-slot="{ timeAgo }" :time="lastUpdate">{{ timeAgo }}</UseTimeAgo>
                </span>
              </TooltipTrigger>
              <TooltipContent>{{ lastUpdateFormatted }}</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
        <div class="text-center">
          <div>
            {{ kingdomStore.status.current_governor }} of {{ kingdomStore.status.target_governor }}
          </div>
          <div class="text-muted-foreground">
            {{ kingdomStore.status.skipped_governors }}
            {{ kingdomStore.status.skipped_governors === 1 ? 'skip' : 'skips' }}
          </div>
        </div>
        <TooltipProvider>
          <div class="text-right">
            <div>Expected Finish</div>
            <Tooltip>
              <TooltipTrigger as-child>
                <span class="text-muted-foreground cursor-help">
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
        </TooltipProvider>
      </div>
      <Progress
        :model-value="
          (kingdomStore.status.current_governor / kingdomStore.status.target_governor) * 100
        "
        class="w-full"
      />
      <!-- CH Verification Progress -->
      <div
        v-if="kingdomStore.status.ch_verification_mode"
        class="w-full mt-2 space-y-1"
      >
        <div class="flex justify-between text-xs text-muted-foreground">
          <span>CH Verification</span>
          <span>{{ kingdomStore.status.ch_current_governor }} / {{ kingdomStore.status.ch_total_governors }}</span>
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

const kingdomStore = useKingdomStore()

const lastUpdate = computed(() => new Date(kingdomStore.status.current_time))
const expectedFinish = computed(
  () => new Date(lastUpdate.value.getTime() + kingdomStore.status.remaining_sec * 1000),
)

const lastUpdateFormatted = useDateFormat(lastUpdate, 'HH:mm:ss')
const expectedFinishFormatted = useDateFormat(expectedFinish, 'HH:mm:ss')

const formatNumber = (value: number | string) => {
  return isNaN(Number(value)) ? (value as string) : Intl.NumberFormat().format(value as number)
}
</script>
