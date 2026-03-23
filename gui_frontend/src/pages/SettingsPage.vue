<template>
  <div class="h-full flex flex-col gap-4 overflow-y-auto pr-2 pb-4">
    <!-- General Settings -->
    <Card>
      <CardHeader class="pb-3">
        <CardTitle>General Settings</CardTitle>
        <CardDescription>Setup emulator connection and paths.</CardDescription>
      </CardHeader>
      <CardContent class="grid gap-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="text-sm font-medium leading-none">Emulator</label>
            <Select v-model="configStore.config.general.emulator">
              <SelectTrigger>
                <SelectValue placeholder="Select an emulator" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="bluestacks">BlueStacks</SelectItem>
                <SelectItem value="nox">Nox</SelectItem>
                <SelectItem value="ldplayer">LDPlayer</SelectItem>
                <SelectItem value="memu">MEmu</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Input 
            v-model="configStore.config.general.bluestacks.name" 
            label="BlueStacks Instance Name" 
          />
        </div>
        <div class="grid gap-2 mb-2">
           <label class="text-sm font-medium leading-none">BlueStacks Config Path</label>
           <Input 
             v-model="configStore.config.general.bluestacks.config" 
           />
        </div>
        <div class="w-1/2 pr-2">
          <Input 
            v-model.number="configStore.config.general.adb_port" 
            type="number"
            label="ADB Port" 
          />
        </div>
      </CardContent>
    </Card>

    <!-- Scan Settings -->
    <Card>
      <CardHeader class="pb-3">
        <CardTitle>Scan Settings</CardTitle>
        <CardDescription>Control the core aspects of how the scan behaves.</CardDescription>
      </CardHeader>
      <CardContent class="flex flex-col gap-4">
        <Input 
          v-model.number="configStore.config.scan.people_to_scan" 
          type="number"
          label="Default People to Scan" 
        />
        
        <div class="grid grid-cols-2 gap-x-4 gap-y-3 rounded-md bg-muted/10 p-4 border mt-2">
          <Switch
            :checked="configStore.config.scan.advanced_scroll"
            @update:checked="configStore.config.scan.advanced_scroll = $event"
            label="Advanced Scroll"
          />
          <Switch
            :checked="configStore.config.scan.track_inactives"
            @update:checked="configStore.config.scan.track_inactives = $event"
            label="Track Inactives"
          />
          <Switch
            :checked="configStore.config.scan.validate_kills"
            @update:checked="configStore.config.scan.validate_kills = $event"
            label="Validate Kills"
          />
          <Switch
            :checked="configStore.config.scan.reconstruct_kills"
            @update:checked="configStore.config.scan.reconstruct_kills = $event"
            label="Reconstruct Kills"
            :disabled="!configStore.config.scan.validate_kills"
          />
        </div>

        <div class="grid grid-cols-2 gap-4 mt-2">
          <div class="flex flex-col gap-3 p-3 border rounded-md bg-muted/5">
             <div class="flex items-center gap-2">
                <Switch
                  :checked="configStore.config.scan.validate_power"
                  @update:checked="configStore.config.scan.validate_power = $event"
                  label="Validate Power"
                />
             </div>
             <Input 
                v-model.number="configStore.config.scan.power_threshold" 
                type="number"
                label="Power Threshold" 
                :disabled="!configStore.config.scan.validate_power"
             />
          </div>
          <!-- Leaving empty slot where City Hall config would go to match the image spacing visually if desired, though since user asked to ignore it, we leave this space blank or remove the 2-col aspect. Let's keep it 2-col for aesthetic balance. -->
          <div></div> 
        </div>
      </CardContent>
    </Card>

    <!-- Timing Settings -->
    <Card>
      <CardHeader class="pb-3">
        <CardTitle>Timing Settings</CardTitle>
        <CardDescription>Fine-tune macro delay timings to match your PC performance.</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-2 gap-4">
           <Input 
              v-model.number="configStore.config.scan.timings.gov_open" 
              type="number"
              step="0.1"
              label="Governor Open Delay (s)" 
           />
           <Input 
              v-model.number="configStore.config.scan.timings.copy_wait" 
              type="number"
              step="0.1"
              label="Copy Wait Delay (s)" 
           />
           <Input 
              v-model.number="configStore.config.scan.timings.kills_open" 
              type="number"
              step="0.1"
              label="Kills Open Delay (s)" 
           />
           <Input 
              v-model.number="configStore.config.scan.timings.info_open" 
              type="number"
              step="0.1"
              label="Info Open Delay (s)" 
           />
           <Input 
              v-model.number="configStore.config.scan.timings.info_close" 
              type="number"
              step="0.1"
              label="Info Close Delay (s)" 
           />
           <Input 
              v-model.number="configStore.config.scan.timings.gov_close" 
              type="number"
              step="0.1"
              label="Governor Close Delay (s)" 
           />
        </div>
        <div class="mt-4 w-full">
           <Input 
              v-model.number="configStore.config.scan.timings.max_random" 
              type="number"
              step="0.1"
              label="Maximum Random Delay (s)" 
           />
        </div>
      </CardContent>
    </Card>

    <div class="flex justify-end pt-2">
      <Button @click="handleSaveConfig" :disabled="saving">
        <template v-if="saving">
          <svg class="mr-2 h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Saving…
        </template>
        <template v-else>Save Settings</template>
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useConfigStore } from '@/stores/config-store'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { toast } from '@/components/ui/toast'
import * as ipc from '@/lib/ipcClient'

const configStore = useConfigStore()
const saving = ref(false)

const handleSaveConfig = async () => {
  saving.value = true
  try {
    await ipc.saveConfig(configStore.config)
    toast({
      title: 'Settings Saved',
      description: 'Your configuration has been updated successfully.',
      variant: 'success',
    })
  } catch (err) {
    toast({
      title: 'Save Failed',
      description: String(err),
      variant: 'destructive',
    })
  } finally {
    saving.value = false
  }
}
</script>
