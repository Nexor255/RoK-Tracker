<template>
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-12 min-h-0">
    <!-- Left Column: Controls (Presets & Tree) -->
    <Card class="flex flex-col gap-4 p-4 lg:col-span-2 min-h-0 overflow-y-auto">
      <!-- Scan Preset -->
      <div class="space-y-1.5">
        <label class="text-sm font-medium">Scan Preset</label>
        <div class="flex items-center gap-2">
          <Select v-model="selectedPresetName" :disabled="scanRunning">
            <SelectTrigger class="flex-1">
              <SelectValue :placeholder="selectedPreset?.name ?? 'Select preset'" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="preset in configStore.availableScanPresets"
                :key="preset.name"
                :value="preset.name"
              >
                {{ preset.name }}
              </SelectItem>
            </SelectContent>
          </Select>
          <Button
            v-if="selectedPreset"
            variant="destructive"
            size="icon"
            @click="handleDeletePreset"
            :disabled="scanRunning"
          >
            <Trash2 class="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Separator />

      <!-- Info Tree (checkboxes) -->
      <div class="flex-1 overflow-y-auto">
        <div v-for="group in infoToScan" :key="group.label" class="space-y-1.5">
          <div class="flex items-center gap-2">
            <Checkbox
              :checked="isGroupChecked(group)"
              @update:checked="toggleGroup(group, $event)"
              :disabled="scanRunning"
            />
            <span class="text-sm font-medium">{{ group.label }}</span>
          </div>
          <div v-if="group.children" class="ml-4 space-y-1.5">
            <div v-for="subGroup in group.children" :key="subGroup.label" class="space-y-1">
              <div class="flex items-center gap-2">
                <Checkbox
                  :checked="isGroupChecked(subGroup)"
                  @update:checked="toggleGroup(subGroup, $event)"
                  :disabled="scanRunning"
                />
                <span class="text-xs font-medium text-muted-foreground">{{ subGroup.label }}</span>
              </div>
              <div v-if="subGroup.children" class="ml-4 space-y-1">
                <div
                  v-for="leaf in subGroup.children"
                  :key="leaf.label"
                  class="flex items-center gap-2"
                >
                  <Checkbox
                    :checked="
                      configStore.selectedKingdomOptions.selections.includes(
                        leaf.label as SelectionValue,
                      )
                    "
                    @update:checked="toggleLeaf(leaf.label as SelectionValue, $event)"
                    :disabled="scanRunning"
                  />
                  <span class="text-xs">{{ leaf.label }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action buttons -->
      <div class="mt-auto flex flex-col gap-2">
        <Button variant="secondary" size="sm" @click="handleSavePreset" :disabled="scanRunning">
          Save as Preset
        </Button>

        <Button
          size="sm"
          :variant="startBtnVariant"
          @click="handleMainButtonClick"
          :disabled="startButtonDisabled"
        >
          {{ startButtonDisabled ? 'Stopping...' : scanRunning ? 'Stop Scan' : 'Start Scan' }}
        </Button>
      </div>
    </Card>

    <!-- Middle Column: Form Settings -->
    <div class="flex flex-col gap-6 lg:col-span-6 min-h-0 overflow-y-auto pr-1">
      <div class="flex flex-col gap-6">
        <!-- General -->
        <div class="grid grid-cols-2 gap-4">
          <Input
            v-model="configStore.config.scan.kingdom_name"
            label="Scan name"
            hint="Prepended to file name"
            :disabled="scanRunning"
          />

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

        <div class="grid grid-cols-2 gap-4">
          <Input
            v-model="configStore.config.general.bluestacks.name"
            label="Emulator name"
            hint="BlueStacks instance name"
            :disabled="scanRunning"
          />
          <Input
            v-model="configStore.config.general.adb_port"
            label="ADB Port"
            hint="Autofilled if found"
            :disabled="scanRunning"
          />
        </div>

        <!-- Governors to scan full width -->
        <Input
          type="number"
          v-model="configStore.config.scan.people_to_scan"
          label="Governors to scan"
          hint="Amount of people to scan"
          :disabled="scanRunning"
        />

        <!-- Toggles grid -->
        <div
          class="grid grid-cols-2 gap-x-4 gap-y-3 rounded-md bg-muted/50 dark:bg-muted/10 backdrop-blur-md p-3 border border-border/60 dark:border-border/50 shadow-sm"
        >
          <Switch
            :checked="configStore.config.scan.resume"
            @update:checked="configStore.config.scan.resume = $event"
            label="Start at 4th governor"
            :disabled="scanRunning"
          />
          <Switch
            :checked="configStore.config.scan.advanced_scroll"
            @update:checked="configStore.config.scan.advanced_scroll = $event"
            label="Better Scrolling"
            :disabled="scanRunning"
          />
          <Switch
            :checked="configStore.config.scan.track_inactives"
            @update:checked="configStore.config.scan.track_inactives = $event"
            label="Track inactives"
            :disabled="scanRunning"
          />
          <Switch
            :checked="configStore.config.scan.validate_kills"
            @update:checked="configStore.config.scan.validate_kills = $event"
            label="Validate kills"
            :disabled="scanRunning"
          />
          <Switch
            :checked="configStore.config.scan.reconstruct_kills"
            @update:checked="configStore.config.scan.reconstruct_kills = $event"
            label="Reconstruct kills"
            :disabled="scanRunning || !configStore.config.scan.validate_kills"
          />
        </div>

        <!-- Power Validation Row -->
        <div class="flex items-center gap-4 mt-1">
          <div class="w-1/3">
            <Switch
              :checked="configStore.config.scan.validate_power"
              @update:checked="configStore.config.scan.validate_power = $event"
              label="Validate Power"
              :disabled="scanRunning"
            />
          </div>
          <div class="w-2/3">
            <Input
              v-model="configStore.config.scan.power_threshold"
              label="Power tolerance"
              hint="Tolerance threshold"
              :disabled="scanRunning || !configStore.config.scan.validate_power"
            />
          </div>
        </div>

        <!-- City Hall Verification -->
        <div
          class="p-3 border border-border/60 dark:border-border/50 rounded-md bg-muted/50 dark:bg-muted/10 backdrop-blur-md mt-1 shadow-sm transition-all duration-200"
          :class="{ 'opacity-60': !configStore.config.scan.check_cityhall }"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium">City Hall Verification</span>
            <Switch
              :checked="configStore.config.scan.check_cityhall"
              @update:checked="configStore.config.scan.check_cityhall = $event"
              :disabled="scanRunning"
            />
          </div>
          <transition
            enter-active-class="transition-all duration-200 ease-out"
            leave-active-class="transition-all duration-150 ease-in"
            enter-from-class="opacity-0 max-h-0"
            enter-to-class="opacity-100 max-h-24"
            leave-from-class="opacity-100 max-h-24"
            leave-to-class="opacity-0 max-h-0"
          >
            <div v-if="configStore.config.scan.check_cityhall" class="mt-3 overflow-hidden">
              <Input
                v-model="configStore.config.scan.ch_auto_assign_power"
                type="number"
                label="Auto-Assign Power Threshold"
                hint="CH level auto-assigned above this power"
                :disabled="scanRunning"
              />
            </div>
          </transition>
        </div>

        <!-- Delays Row -->
        <div class="grid grid-cols-3 gap-2 xl:gap-4">
          <Input
            v-model="configStore.config.scan.timings.info_close"
            label="Info delay (s)"
            hint="Wait after more info"
            :disabled="scanRunning"
          />
          <Input
            v-model="configStore.config.scan.timings.gov_close"
            label="Gov delay (s)"
            hint="Wait after governor"
            :disabled="scanRunning"
          />
          <Input
            v-model="configStore.config.scan.timings.max_random"
            label="Random delay (s)"
            hint="Max added variance"
            :disabled="scanRunning"
          />
        </div>
      </div>
    </div>

    <!-- Right Column: Results & Status -->
    <div class="flex flex-col gap-4 lg:col-span-4 min-h-0">
      <div class="flex-1 flex flex-col gap-4 min-h-0">
        <!-- We use flex-1 on this div so the inner components can stretch or scroll if necessary. -->
        <LastGovernor class="flex-1" />
        <ScanStatus
          class="mt-auto"
          :scan-id="kingdomStore.scanID"
          :status-message="kingdomStore.statusMessage"
        />
      </div>
    </div>

    <!-- Dialogs -->
    <AlertDialog :open="saveDialogOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Save Preset</AlertDialogTitle>
          <AlertDialogDescription>Enter a name for the preset</AlertDialogDescription>
        </AlertDialogHeader>
        <Input v-model="newPresetName" placeholder="Preset name" />
        <AlertDialogFooter>
          <AlertDialogCancel @click="saveDialogOpen = false">Cancel</AlertDialogCancel>
          <AlertDialogAction @click="confirmSavePreset" :disabled="!newPresetName"
            >Save</AlertDialogAction
          >
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <AlertDialog :open="deleteDialogOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Preset</AlertDialogTitle>
          <AlertDialogDescription>
            Do you really want to delete the {{ selectedPreset?.name }} preset?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel @click="deleteDialogOpen = false">No</AlertDialogCancel>
          <AlertDialogAction
            @click="confirmDeletePreset"
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >Yes, delete</AlertDialogAction
          >
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <AlertDialog :open="confirmDialogOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Confirm</AlertDialogTitle>
          <AlertDialogDescription>Do you want to continue?</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel @click="handleConfirmResponse(false)">No</AlertDialogCancel>
          <AlertDialogAction @click="handleConfirmResponse(true)">Yes</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { Trash2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import LastGovernor from './LastGovernor.vue'
import ScanStatus from './ScanStatus.vue'
import { useKingdomStore } from '@/stores/kingdom-store'
import { useConfigStore } from '@/stores/config-store'
import { KingdomGovernorDataSchema } from '@/schema/KingdomGovernorData'
import { KingdomAdditionalDataSchema } from '@/schema/KingdomAdditionalData'
import type { ScanPreset } from '@/schema/ScanPreset'
import type { OutputFormat } from '@/types/OutputFormats'

import * as ipc from '@/lib/tauriClient'
import { onSidecarEvent } from '@/lib/tauriClient'

const kingdomStore = useKingdomStore()
const configStore = useConfigStore()
const { scanRunning, startButtonDisabled } = storeToRefs(kingdomStore)

const startBtnVariant = computed(() => {
  if (startButtonDisabled.value) return 'secondary'
  if (scanRunning.value) return 'destructive'
  return 'default'
})

// ---- Preset management ----
const selectedPresetName = ref(configStore.availableScanPresets[0]?.name ?? '')
const selectedPreset = computed(() =>
  configStore.availableScanPresets.find((p) => p.name === selectedPresetName.value),
)

watch(selectedPresetName, () => {
  if (selectedPreset.value) {
    configStore.selectedKingdomOptions.selections = selectedPreset.value.selections
  }
})

// Save preset dialog
const saveDialogOpen = ref(false)
const newPresetName = ref('')

const handleSavePreset = () => {
  newPresetName.value = ''
  saveDialogOpen.value = true
}

const confirmSavePreset = () => {
  const newPreset: ScanPreset = {
    name: newPresetName.value,
    selections: configStore.selectedKingdomOptions.selections,
  }
  configStore.availableScanPresets.push(newPreset)
  selectedPresetName.value = newPreset.name
  ipc.saveScanPresets(configStore.availableScanPresets)
  saveDialogOpen.value = false
}

// Delete preset dialog
const deleteDialogOpen = ref(false)

const handleDeletePreset = () => {
  deleteDialogOpen.value = true
}

const confirmDeletePreset = () => {
  configStore.availableScanPresets = configStore.availableScanPresets.filter(
    (p) => p.name !== selectedPreset.value?.name,
  )
  selectedPresetName.value = ''
  ipc.saveScanPresets(configStore.availableScanPresets)
  deleteDialogOpen.value = false
}

// ---- Output formats ----
const outputFormats: OutputFormat[] = [
  { label: 'Excel (xlsx)', value: 'xlsx', display: 'xlsx' },
  { label: 'Comma Separated Values (csv)', value: 'csv', display: 'csv' },
  { label: 'JSON Lines (jsonl)', value: 'jsonl', display: 'jsonl' },
]

const selectedOutputs = ref<OutputFormat[]>(
  outputFormats.filter((fmt) => {
    const formats = configStore.config.scan.formats
    return formats[fmt.value as keyof typeof formats]
  }),
)

const isFormatSelected = (fmt: OutputFormat): boolean => {
  return selectedOutputs.value.some((s) => s.value === fmt.value)
}

const toggleFormat = (fmt: OutputFormat) => {
  if (isFormatSelected(fmt)) {
    selectedOutputs.value = selectedOutputs.value.filter((s) => s.value !== fmt.value)
  } else {
    selectedOutputs.value.push(fmt)
  }
}

watch(
  selectedOutputs,
  (newVal) => {
    configStore.config.scan.formats.csv = newVal.some((f) => f.value === 'csv')
    configStore.config.scan.formats.jsonl = newVal.some((f) => f.value === 'jsonl')
    configStore.config.scan.formats.xlsx = newVal.some((f) => f.value === 'xlsx')
  },
  { deep: true },
)

// ---- Tree (info to scan) ----
interface TreeNode {
  label: string
  children?: TreeNode[]
}

const infoToScan: TreeNode[] = [
  {
    label: 'Everything',
    children: [
      {
        label: 'First Screen',
        children: [
          { label: 'ID' },
          { label: 'Name' },
          { label: 'Power' },
          { label: 'Killpoints' },
          { label: 'Alliance' },
        ],
      },
      {
        label: 'Second Screen',
        children: [
          { label: 'T1 Kills' },
          { label: 'T2 Kills' },
          { label: 'T3 Kills' },
          { label: 'T4 Kills' },
          { label: 'T5 Kills' },
          { label: 'Ranged' },
        ],
      },
      {
        label: 'Third Screen',
        children: [
          { label: 'Deaths' },
          { label: 'Assistance' },
          { label: 'Gathered' },
          { label: 'Helps' },
        ],
      },
    ],
  },
]

type SelectionValue = ScanPreset['selections'][number]

const getLeaves = (node: TreeNode): SelectionValue[] => {
  if (!node.children) return [node.label as SelectionValue]
  return node.children.flatMap(getLeaves)
}

const isGroupChecked = (node: TreeNode): boolean => {
  const leaves = getLeaves(node)
  return leaves.every((l) => configStore.selectedKingdomOptions.selections.includes(l))
}

const toggleGroup = (node: TreeNode, checked: boolean) => {
  const leaves = getLeaves(node)
  if (checked) {
    const toAdd = leaves.filter((l) => !configStore.selectedKingdomOptions.selections.includes(l))
    configStore.selectedKingdomOptions.selections.push(...toAdd)
  } else {
    configStore.selectedKingdomOptions.selections =
      configStore.selectedKingdomOptions.selections.filter((s) => !(leaves as string[]).includes(s))
  }
}

const toggleLeaf = (label: SelectionValue, checked: boolean) => {
  if (checked) {
    if (!configStore.selectedKingdomOptions.selections.includes(label)) {
      configStore.selectedKingdomOptions.selections.push(label)
    }
  } else {
    configStore.selectedKingdomOptions.selections =
      configStore.selectedKingdomOptions.selections.filter((s) => s !== label)
  }
}

// ---- Scan control ----
const handleMainButtonClick = () => {
  if (!scanRunning.value) {
    // Use the selected preset, or build one from current checkbox selections
    const preset = selectedPreset.value ?? {
      name: 'Custom',
      selections: [...configStore.selectedKingdomOptions.selections],
    }
    // Auto-save config so scanner-page tweaks aren't lost on crash
    ipc.saveConfig(configStore.config).catch(() => {})
    ipc.startKingdomScan(configStore.config, preset)
    scanRunning.value = true
  } else {
    ipc.stopKingdomScan()
    startButtonDisabled.value = true
  }
}

// ---- IPC callbacks ----
const confirmDialogOpen = ref(false)

const handleConfirmResponse = (confirmed: boolean) => {
  confirmDialogOpen.value = false
  ipc.confirmKingdomScan(confirmed)
}

const setScanId = (id: string) => {
  kingdomStore.scanID = id
}

// Throttle governor updates to one per animation frame to prevent UI jitter during fast scans
let pendingGovUpdate: { gov: unknown; extra: unknown } | null = null
let govRafId: number | null = null

const flushGovUpdate = () => {
  govRafId = null
  if (!pendingGovUpdate) return
  const { gov, extra } = pendingGovUpdate
  pendingGovUpdate = null
  kingdomStore.lastGovernor = KingdomGovernorDataSchema.parse(gov)
  kingdomStore.status = KingdomAdditionalDataSchema.parse(extra)
}

const governorUpdate = (governorData: unknown, extraData: unknown) => {
  pendingGovUpdate = { gov: governorData, extra: extraData }
  if (govRafId === null) {
    govRafId = requestAnimationFrame(flushGovUpdate)
  }
}

const stateUpdate = (state: string) => {
  kingdomStore.statusMessage = state
}

const askConfirm = (_message: string) => {
  confirmDialogOpen.value = true
}

const scanFinished = () => {
  scanRunning.value = false
  startButtonDisabled.value = false
}

// ---- Sidecar event listeners ----
const unlisteners: Array<() => void> = []

onMounted(async () => {
  unlisteners.push(
    await onSidecarEvent('kingdom_scan_id', (data) => {
      setScanId(data)
    }),
  )
  unlisteners.push(
    await onSidecarEvent('kingdom_governor_update', (data) => {
      governorUpdate(data.gov, data.extra)
    }),
  )
  unlisteners.push(
    await onSidecarEvent('kingdom_state_update', (data) => {
      stateUpdate(data)
    }),
  )
  unlisteners.push(
    await onSidecarEvent('kingdom_ask_confirm', (data) => {
      askConfirm(data)
    }),
  )
  unlisteners.push(
    await onSidecarEvent('kingdom_scan_finished', () => {
      scanFinished()
    }),
  )
})

onUnmounted(() => {
  unlisteners.forEach((fn) => fn())
  if (govRafId !== null) cancelAnimationFrame(govRafId)
})
</script>
