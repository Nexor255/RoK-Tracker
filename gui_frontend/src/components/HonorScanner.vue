<template>
  <div class="flex gap-4">
    <div class="flex w-2/3 flex-col gap-3">
      <div class="grid grid-cols-2 gap-3">
        <Input v-model="configStore.config.scan.kingdom_name" label="Scan name" hint="This will get prepended to the file name" :disabled="scanRunning" />
        <div class="space-y-1.5 flex flex-col justify-end">
          <label class="text-sm font-medium leading-none">Output formats</label>
          <div class="flex gap-2">
            <Button
              v-for="fmt in outputFormats"
              :key="fmt.value"
              :variant="isFormatSelected(fmt) ? 'default' : 'outline'"
              size="sm"
              @click="toggleFormat(fmt)"
              :disabled="scanRunning"
              class="text-xs"
            >
              {{ fmt.display }}
            </Button>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <Input v-model="configStore.config.general.bluestacks.name" label="Emulator name" hint="Works only for BlueStacks" :disabled="scanRunning" />
        <Input v-model="configStore.config.general.adb_port" label="ADB Port of emulator" hint="Should be autofilled if emulator is found" :disabled="scanRunning" />
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
import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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

const isFormatSelected = (fmt: OutputFormat): boolean => {
  return selectedOutputs.value.some(s => s.value === fmt.value)
}

const toggleFormat = (fmt: OutputFormat) => {
  if (isFormatSelected(fmt)) {
    selectedOutputs.value = selectedOutputs.value.filter(s => s.value !== fmt.value)
  } else {
    selectedOutputs.value.push(fmt)
  }
}

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
