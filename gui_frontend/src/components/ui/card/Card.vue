<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <div :class="cn('glass-card hover-card-glow rounded-xl border border-border/60 bg-card/90 text-card-foreground shadow-sm backdrop-blur-sm dark:bg-card/55 dark:border-border/40', props.class)">
    <slot />
  </div>
</template>
