<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { SwitchRoot, type SwitchRootEmits, type SwitchRootProps, SwitchThumb, useForwardPropsEmits } from 'radix-vue'
import { cn } from '@/lib/utils'

const props = defineProps<SwitchRootProps & { class?: HTMLAttributes['class']; label?: string }>()
const emits = defineEmits<SwitchRootEmits>()
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <div class="flex items-center gap-2">
    <SwitchRoot
      v-bind="forwarded"
      :class="cn(
        'peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=unchecked]:bg-foreground/20',
        props.class,
      )"
    >
      <SwitchThumb
        :class="cn('pointer-events-none block h-4 w-4 rounded-full bg-background shadow-lg ring-0 transition-transform data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0')"
      />
    </SwitchRoot>
    <label v-if="label" class="text-sm font-medium leading-none">{{ label }}</label>
  </div>
</template>
