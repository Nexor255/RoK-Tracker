<template>
  <div class="h-full flex flex-col gap-6 overflow-y-auto pr-2 pb-4">
    <div>
      <h2 class="text-xl font-semibold tracking-tight">Calculators</h2>
      <p class="text-sm text-muted-foreground mt-1">
        Kill point calculators, resource planners, and more are on the way.
      </p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card
        v-for="calc in calculators"
        :key="calc.title"
        class="opacity-60 pointer-events-none select-none border-dashed"
      >
        <CardHeader class="pb-3">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
              <component :is="calc.icon" class="h-5 w-5 text-muted-foreground" />
            </div>
            <div class="flex-1 min-w-0">
              <CardTitle class="text-sm">{{ calc.title }}</CardTitle>
            </div>
          </div>
        </CardHeader>
        <CardContent class="pt-0">
          <p class="text-xs text-muted-foreground leading-relaxed">{{ calc.description }}</p>
          <Badge variant="secondary" class="mt-3 text-[10px]">Coming Soon</Badge>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Calculator, Package, Swords, Timer, Users, Gift } from 'lucide-vue-next'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const calculators = [
  {
    title: 'MGE Calculator',
    description: 'Calculate kill points required for Mightiest Governor events.',
    icon: Swords,
  },
  {
    title: 'Resource Planner',
    description: 'Plan resource gathering, spending, and bundle optimization.',
    icon: Package,
  },
  {
    title: 'Kill Point Calculator',
    description: 'Estimate kill points from different troop tier compositions.',
    icon: Calculator,
  },
  {
    title: 'Speedup Calculator',
    description: 'Optimize speedup usage for buildings, research, and training.',
    icon: Timer,
  },
  {
    title: 'Troop Training Planner',
    description: 'Plan troop training batches, times, and resource costs.',
    icon: Users,
  },
  {
    title: 'Alliance Gifting Tracker',
    description: 'Track alliance gifts, contributions, and member activity.',
    icon: Gift,
  },
]
</script>
