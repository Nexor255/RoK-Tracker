<template>
  <div class="h-full overflow-y-auto pr-2 pb-4">
    <div class="mx-auto max-w-3xl flex flex-col gap-4">
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

    <!-- Appearance Settings -->
    <Card>
      <CardHeader class="pb-3">
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Customize the look and feel of the application.</CardDescription>
      </CardHeader>
      <CardContent class="grid gap-4">
        <div class="space-y-3">
          <label class="text-sm font-medium leading-none flex items-center justify-between">
            Theme Accent Color
            <span class="text-xs font-mono text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-md border">Hue: {{ configStore.themeColor }}</span>
          </label>
          
          <!-- Hue Slider -->
          <div class="relative pt-1 pb-2">
            <input 
              type="range" 
              min="0" 
              max="360" 
              v-model.number="configStore.themeColor"
              class="hue-slider w-full h-3 rounded-full appearance-none cursor-pointer border border-border/50 shadow-inner"
              style="background: linear-gradient(to right, oklch(0.6 0.2 0), oklch(0.6 0.2 60), oklch(0.6 0.2 120), oklch(0.6 0.2 180), oklch(0.6 0.2 240), oklch(0.6 0.2 300), oklch(0.6 0.2 360));"
            />
            <div class="absolute -bottom-2 inset-x-0 pointer-events-none flex justify-between px-1.5">
               <!-- Tick marks for the slider -->
               <div v-for="i in 7" :key="i" class="w-[1px] h-1.5 bg-foreground/20"></div>
            </div>
          </div>

          <!-- Color Swatches -->
          <div class="flex flex-wrap gap-2.5 mt-2">
            <button
              v-for="preset in [
                { hue: 27, label: 'Red' },
                { hue: 50, label: 'Orange' },
                { hue: 100, label: 'Yellow-Green' },
                { hue: 150, label: 'Green' },
                { hue: 200, label: 'Cyan' },
                { hue: 250, label: 'Blue' },
                { hue: 275, label: 'Purple' },
                { hue: 330, label: 'Pink' }
              ]"
              :key="preset.hue"
              @click="configStore.themeColor = preset.hue"
              class="w-8 h-8 rounded-full border-2 transition-all hover:scale-110 active:scale-95 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background shadow-sm"
              :class="configStore.themeColor === preset.hue ? 'border-foreground scale-110 ring-2 ring-ring ring-offset-2 ring-offset-background' : 'border-transparent'"
              :title="preset.label"
              :style="{ backgroundColor: `oklch(0.6 0.2 ${preset.hue})` }"
            />
          </div>
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
        
        <div class="grid grid-cols-2 gap-x-4 gap-y-3 rounded-md bg-muted/50 dark:bg-muted/10 backdrop-blur-md p-4 border border-border/60 dark:border-border/50 mt-2 shadow-sm">
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

        <div class="flex flex-col gap-3 p-3 border border-border/60 dark:border-border/50 rounded-md bg-muted/50 dark:bg-muted/10 backdrop-blur-md mt-2 shadow-sm">
           <Switch
             :checked="configStore.config.scan.validate_power"
             @update:checked="configStore.config.scan.validate_power = $event"
             label="Validate Power"
           />
           <Input 
              v-model.number="configStore.config.scan.power_threshold" 
              type="number"
              label="Power Threshold" 
              :disabled="!configStore.config.scan.validate_power"
           />
        </div>
      </CardContent>
    </Card>

    <!-- City Hall Verification -->
    <Card>
      <CardHeader class="pb-3">
        <CardTitle>City Hall Verification</CardTitle>
        <CardDescription>Verify governor City Hall levels after the main scan completes.</CardDescription>
      </CardHeader>
      <CardContent class="flex flex-col gap-4">
        <Switch
          :checked="configStore.config.scan.check_cityhall"
          @update:checked="configStore.config.scan.check_cityhall = $event"
          label="Enable CH Verification"
        />
        <Input
          v-model.number="configStore.config.scan.ch_auto_assign_power"
          type="number"
          label="Auto-Assign Power Threshold"
          :disabled="!configStore.config.scan.check_cityhall"
        />
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
import * as ipc from '@/lib/tauriClient'

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
