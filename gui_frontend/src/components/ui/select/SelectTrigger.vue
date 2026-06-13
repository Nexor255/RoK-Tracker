<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { SelectIcon, SelectTrigger, type SelectTriggerProps } from 'radix-vue'
import { ChevronDown } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = defineProps<SelectTriggerProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <SelectTrigger
    v-bind="props"
    :class="cn(
      'form-control flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border border-input dark:border-white/10 bg-card dark:bg-white/5 dark:backdrop-blur-md px-3 py-2 text-sm shadow-sm dark:shadow-none transition-colors ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/40 dark:focus:ring-primary/35 dark:focus:border-primary/40 disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1',
      props.class,
    )"
  >
    <slot />
    <SelectIcon as-child>
      <ChevronDown class="h-4 w-4 opacity-50" />
    </SelectIcon>
  </SelectTrigger>
</template>
