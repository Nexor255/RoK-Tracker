<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { useVModel } from '@vueuse/core'
import { cn } from '@/lib/utils'
import { HelpCircle } from 'lucide-vue-next'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'

const props = defineProps<{
  defaultValue?: string | number
  modelValue?: string | number
  class?: HTMLAttributes['class']
  label?: string
  hint?: string
  disabled?: boolean
}>()

const emits = defineEmits<{
  'update:modelValue': [payload: string | number]
}>()

const modelValue = useVModel(props, 'modelValue', emits, {
  passive: true,
  defaultValue: props.defaultValue,
})
</script>

<template>
  <div class="space-y-1">
    <div v-if="label" class="flex items-center gap-1">
      <label class="text-sm font-medium leading-none text-foreground">{{ label }}</label>
      <TooltipProvider v-if="hint">
        <Tooltip>
          <TooltipTrigger as-child>
            <HelpCircle class="h-3.5 w-3.5 text-muted-foreground cursor-help shrink-0" />
          </TooltipTrigger>
          <TooltipContent side="top">
            <p>{{ hint }}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
    <input
      v-model="modelValue"
      :class="cn('flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50', props.class)"
      :disabled="disabled"
    />
  </div>
</template>
