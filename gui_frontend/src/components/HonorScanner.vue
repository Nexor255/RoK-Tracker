<template>
  <div class="flex gap-4">
    <div class="flex w-2/3 flex-col gap-3">
      <div class="flex gap-3">
        <div class="flex-[2]">
          <Input v-model="configStore.config.scan.kingdom_name" label="Scan name" hint="This will get prepended to the file name" :disabled="scanRunning" />
        </div>
        <div class="flex-1 space-y-1">
          <label class="text-sm font-medium">Output formats</label>
          <div class="flex flex-wrap gap-1 rounded-md border p-2 min-h-[36px]">
            <Badge v-for="(fmt, idx) in selectedOutputs" :key="fmt.value" variant="outline" class="flex items-center gap-1 cursor-pointer" @click="removeOutput(idx)">
              {{ fmt.display }}<X class="h-3 w-3" />
            </Badge>
          </div>
          <div class="flex gap-1 mt-1">
            <Button v-for="fmt in availableOutputFormats" :key="fmt.value" variant="ghost" size="sm" @click="addOutput(fmt)" :disabled="scanRunning" class="text-xs h-6">+ {{ fmt.display }}</Button>
          </div>
          <p class="text-xs text-muted-foreground">The format you want</p>
        </div>
      </div>
      <div class="flex gap-3">
        <div class="flex-1">
          <Input v-model="configStore.config.general.bluestacks.name" label="Emulator name" hint="Works only for BlueStacks" :disabled="scanRunning" />
        </div>
        <div class="flex-1">
          <Input v-model="configStore.config.general.adb_port" label="ADB Port of emulator" hint="Should be autofilled if emulator is found" :disabled="scanRunning" />
        </div>
      </div>
      <Input v-model="configStore.config.scan.people_to_scan" label="How many people to scan" hint="The amount of people you want to scan" :disabled="scanRunning" />
      <Input v-model="configStore.config.scan.timings.max_random" label="Maximum random delay (in s)" hint="A random delay is added to the wait times, this is the maximum" :disabled="scanRunning" />
      <Button :variant="scanRunning ? 'destructive' : 'default'" @click="handleMainButtonClick" :disabled="startButtonDisabled">
        {{ startButtonDisabled ? 'Stopping...' : scanRunning ? 'Stop Scan' : 'Start Scan' }}
      </Button>
    </div>
    <div class="flex flex-1 flex-col gap-3">
      <div class="flex-1">
        <LastBatch :batchData="honorStore.lastGovernor" :batchStatus="honorStore.status" />
      </div>
      <ScanStatus :scan-id="honorStore.scanID" :status-message="honorStore.statusMessage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { X } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import ScanStatus from './ScanStatus.vue'
import LastBatch from './LastBatch.vue'
import { useHonorStore } from '@/stores/honor-store'
import { useConfigStore } from '@/stores/config-store'
import type { OutputFormat } from '@/types/OutputFormats'
import * as ipc from '@/lib/ipcClient'
import type { BatchType } from '@/schema/BatchType'

const honorStore = useHonorStore()
const configStore = useConfigStore()
const { scanRunning, startButtonDisabled } = storeToRefs(honorStore)
const batchType: BatchType = { type: 'Honor' }

const outputFormats: OutputFormat[] = [
  { label: 'Excel (xlsx)', value: 'xlsx', display: 'xlsx' },
  { label: 'Comma Separated Values (csv)', value: 'csv', display: 'csv' },
  { label: 'JSON Lines (jsonl)', value: 'jsonl', display: 'jsonl' },
]
const selectedOutputs = ref<OutputFormat[]>([{ label: 'Excel', value: 'xlsx', display: 'xlsx' }])
const availableOutputFormats = computed(() => outputFormats.filter(f => !selectedOutputs.value.some(s => s.value === f.value)))
const addOutput = (fmt: OutputFormat) => { selectedOutputs.value.push(fmt) }
const removeOutput = (index: number) => { selectedOutputs.value.splice(index, 1) }

watch(selectedOutputs, (newVal) => {
  configStore.config.scan.formats.csv = newVal.some((f) => f.value === 'csv')
  configStore.config.scan.formats.jsonl = newVal.some((f) => f.value === 'jsonl')
  configStore.config.scan.formats.xlsx = newVal.some((f) => f.value === 'xlsx')
}, { deep: true })

const handleMainButtonClick = () => {
  if (!scanRunning.value) {
    ipc.startBatchScan(configStore.config, JSON.stringify(batchType))
    scanRunning.value = !scanRunning.value
  } else {
    ipc.stopBatchScan(JSON.stringify(batchType))
    startButtonDisabled.value = true
  }
}
</script>
