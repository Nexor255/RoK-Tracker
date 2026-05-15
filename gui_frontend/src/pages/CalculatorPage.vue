<template>
  <div class="flex h-full flex-col">
    <Tabs v-model="activeTab" class="flex h-full flex-col">
      <TabsList class="w-full justify-start rounded-none border-b bg-transparent p-0">
        <TabsTrigger
          value="killpoints"
          class="gap-1.5 rounded-none border-b-2 border-transparent transition-colors duration-200 hover:border-muted-foreground/30 data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
        >
          <Swords class="h-4 w-4" />
          Kill Points
        </TabsTrigger>
        <TabsTrigger
          value="training"
          class="gap-1.5 rounded-none border-b-2 border-transparent transition-colors duration-200 hover:border-muted-foreground/30 data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
        >
          <Users class="h-4 w-4" />
          Troop Training
        </TabsTrigger>
        <TabsTrigger
          value="healing"
          class="gap-1.5 rounded-none border-b-2 border-transparent transition-colors duration-200 hover:border-muted-foreground/30 data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
        >
          <HeartPulse class="h-4 w-4" />
          Healing Cost
        </TabsTrigger>
      </TabsList>

      <!-- Kill Points Calculator -->
      <TabsContent value="killpoints" class="flex-1 overflow-auto p-4">
        <div class="mx-auto max-w-3xl flex flex-col gap-4">
          <Card>
            <CardHeader class="pb-3">
              <CardTitle>Kill Point Calculator</CardTitle>
              <CardDescription>Enter troop kills per tier to calculate total kill points.</CardDescription>
            </CardHeader>
            <CardContent class="grid gap-4">
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div v-for="tier in killTiers" :key="tier.label" class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">{{ tier.label }}</label>
                  <input
                    v-model.number="tier.kills"
                    type="number"
                    min="0"
                    placeholder="0"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                  <span class="text-[10px] text-muted-foreground">× {{ tier.multiplier }} pts each</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- Kill Points Result -->
          <Card class="border-primary/30 bg-primary/5">
            <CardContent class="pt-6">
              <div class="grid grid-cols-2 sm:grid-cols-5 gap-4 text-center">
                <div v-for="tier in killTiers" :key="'r-' + tier.label" class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{{ tier.label }}</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(tier.kills * tier.multiplier) }}</p>
                </div>
                <div class="space-y-0.5 border-l pl-4">
                  <p class="text-[10px] font-medium text-primary uppercase tracking-wider">Total</p>
                  <p class="text-lg font-bold text-primary tabular-nums">{{ fmt(totalKillPoints) }}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      <!-- Troop Training Calculator -->
      <TabsContent value="training" class="flex-1 overflow-auto p-4">
        <div class="mx-auto max-w-3xl flex flex-col gap-4">
          <Card>
            <CardHeader class="pb-3">
              <CardTitle>Troop Training Planner</CardTitle>
              <CardDescription>Estimate training time and resource cost for a batch of troops.</CardDescription>
            </CardHeader>
            <CardContent class="grid gap-4">
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">Troop Tier</label>
                  <select
                    v-model.number="training.tier"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option v-for="t in troopTierOptions" :key="t.tier" :value="t.tier">{{ t.name }}</option>
                  </select>
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">Troops to Train</label>
                  <input
                    v-model.number="training.count"
                    type="number"
                    min="0"
                    placeholder="10000"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">Batch Size</label>
                  <input
                    v-model.number="training.batchSize"
                    type="number"
                    min="1"
                    placeholder="200"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">Training Speed Bonus (%)</label>
                  <input
                    v-model.number="training.speedBonus"
                    type="number"
                    min="0"
                    placeholder="0"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card class="border-primary/30 bg-primary/5">
            <CardContent class="pt-6">
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Batches</p>
                  <p class="text-sm font-semibold tabular-nums">{{ trainingResult.batches }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Per Batch</p>
                  <p class="text-sm font-semibold tabular-nums">{{ formatDuration(trainingResult.perBatchMin) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Total Time</p>
                  <p class="text-lg font-bold text-primary tabular-nums">{{ formatDuration(trainingResult.totalMin) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Power Gain</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(trainingResult.power) }}</p>
                </div>
              </div>

              <Separator class="my-4" />

              <div class="grid grid-cols-4 gap-4 text-center">
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Food</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(trainingResult.food) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Wood</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(trainingResult.wood) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Stone</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(trainingResult.stone) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Gold</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(trainingResult.gold) }}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      <!-- Healing Cost Calculator -->
      <TabsContent value="healing" class="flex-1 overflow-auto p-4">
        <div class="mx-auto max-w-3xl flex flex-col gap-4">
          <Card>
            <CardHeader class="pb-3">
              <CardTitle>Healing Cost Calculator</CardTitle>
              <CardDescription>Enter wounded troops per tier to estimate healing resource costs and time.</CardDescription>
            </CardHeader>
            <CardContent class="grid gap-4">
              <div class="grid grid-cols-2 sm:grid-cols-5 gap-4">
                <div v-for="tier in healTiers" :key="tier.label" class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">{{ tier.label }} Wounded</label>
                  <input
                    v-model.number="tier.count"
                    type="number"
                    min="0"
                    placeholder="0"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">Healing Speed Bonus (%)</label>
                  <input
                    v-model.number="healSpeedBonus"
                    type="number"
                    min="0"
                    placeholder="0"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-medium text-muted-foreground">Hospital Capacity</label>
                  <input
                    v-model.number="hospitalCapacity"
                    type="number"
                    min="1"
                    placeholder="50000"
                    class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
              </div>
              <div class="rounded-md bg-muted/50 dark:bg-muted/10 p-4 border border-border/60 dark:border-border/50">
                <div class="space-y-2">
                  <div class="flex items-center justify-between">
                    <label class="text-xs font-medium text-muted-foreground">Alliance Help</label>
                    <span class="rounded-full bg-primary/15 px-2 py-0.5 text-xs font-semibold tabular-nums text-primary">{{ allianceHelps }} taps</span>
                  </div>
                  <input
                    v-model.number="allianceHelps"
                    type="range"
                    min="0"
                    max="30"
                    step="1"
                    class="alliance-slider"
                  />
                  <div class="flex justify-between text-[9px] text-muted-foreground/60 tabular-nums">
                    <span>0</span>
                    <span>10</span>
                    <span>20</span>
                    <span>30</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- Per-tier breakdown -->
          <Card class="border-primary/30 bg-primary/5">
            <CardHeader class="pb-3">
              <CardTitle class="text-sm">Per-Tier Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="grid grid-cols-5 gap-3 text-center mb-3">
                <div v-for="tier in healTiers" :key="'hc-' + tier.label" class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{{ tier.label }}</p>
                  <p class="text-xs font-semibold tabular-nums">{{ fmt((tier.count || 0) * tier.foodPer) }}</p>
                  <p class="text-[9px] text-muted-foreground">food</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- Totals -->
          <Card class="border-primary/30 bg-primary/5">
            <CardContent class="pt-6">
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Food</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(healResult.food) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Wood</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(healResult.wood) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Stone</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(healResult.stone) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Gold</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(healResult.gold) }}</p>
                </div>
              </div>

              <Separator class="my-4" />

              <div class="grid grid-cols-2 sm:grid-cols-5 gap-4 text-center">
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Total Wounded</p>
                  <p class="text-sm font-semibold tabular-nums">{{ fmt(healResult.totalTroops) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Base Heal Time</p>
                  <p class="text-sm font-semibold tabular-nums">{{ formatDuration(healResult.baseMin) }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-primary uppercase tracking-wider">After Helps</p>
                  <p class="text-lg font-bold text-primary tabular-nums">{{ formatDuration(healResult.totalMin) }}</p>
                  <p v-if="healResult.savedMin > 0" class="text-[9px] text-emerald-500">−{{ formatDuration(healResult.savedMin) }} saved</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Per Tap</p>
                  <p class="text-sm font-semibold tabular-nums">{{ healResult.firstTapMin.toFixed(1) }}m</p>
                  <p class="text-[9px] text-muted-foreground">{{ healResult.firstTapRule }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Batches</p>
                  <p class="text-sm font-semibold tabular-nums" :class="healResult.batches > 1 ? 'text-destructive' : ''">
                    {{ healResult.batches }}
                  </p>
                </div>
              </div>

              <!-- Explanation -->
              <div v-if="healResult.baseMin > 0" class="mt-4 rounded-md bg-muted/40 dark:bg-muted/10 p-3 border border-border/40 text-xs text-muted-foreground leading-relaxed">
                <p class="font-medium text-foreground mb-1">How Alliance Help works</p>
                <p>Each tap reduces by <span class="font-semibold text-foreground">max(1% of remaining time, 3m floor)</span>.</p>
                <p v-if="healResult.firstTapRule === '1% rule'" class="mt-1">
                  Your timer is large enough that <span class="text-primary font-medium">1% ({{ healResult.firstTapMin.toFixed(1) }}m)</span> exceeds the 3m floor — each tap gives diminishing returns.
                </p>
                <p v-else class="mt-1">
                  Your timer is small enough that the <span class="text-primary font-medium">3m floor</span> kicks in — each tap removes a flat 3m regardless of queue length.
                </p>
                <p v-if="healResult.tapsToFinish < Infinity" class="mt-1">
                  <span class="font-medium text-foreground">{{ healResult.tapsToFinish }} taps</span> would fully clear this queue.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Swords, Users, HeartPulse } from 'lucide-vue-next'

const activeTab = ref('killpoints')

// ─── Formatter ───
function fmt(n: number): string {
  if (!n || isNaN(n)) return '0'
  return n.toLocaleString('en-US')
}

function formatDuration(totalMinutes: number): string {
  if (!totalMinutes || totalMinutes <= 0) return '0m'
  const d = Math.floor(totalMinutes / 1440)
  const h = Math.floor((totalMinutes % 1440) / 60)
  const m = Math.round(totalMinutes % 60)
  const parts: string[] = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  if (m > 0 || parts.length === 0) parts.push(`${m}m`)
  return parts.join(' ')
}

// ─── Kill Points ───
const killTiers = reactive([
  { label: 'T1', multiplier: 2, kills: 0 },
  { label: 'T2', multiplier: 4, kills: 0 },
  { label: 'T3', multiplier: 6, kills: 0 },
  { label: 'T4', multiplier: 10, kills: 0 },
  { label: 'T5', multiplier: 20, kills: 0 },
])

const totalKillPoints = computed(() =>
  killTiers.reduce((sum, t) => sum + (t.kills || 0) * t.multiplier, 0)
)

// ─── Troop Training ───
const troopTierOptions = [
  { tier: 1, name: 'Tier 1', baseTime: 0.5, power: 2, food: 50, wood: 50, stone: 0, gold: 0 },
  { tier: 2, name: 'Tier 2', baseTime: 1, power: 8, food: 100, wood: 100, stone: 50, gold: 0 },
  { tier: 3, name: 'Tier 3', baseTime: 2, power: 24, food: 200, wood: 200, stone: 150, gold: 50 },
  { tier: 4, name: 'Tier 4', baseTime: 3, power: 60, food: 500, wood: 500, stone: 300, gold: 100 },
  { tier: 5, name: 'Tier 5', baseTime: 6, power: 100, food: 1000, wood: 1000, stone: 600, gold: 200 },
]

const training = reactive({ tier: 4, count: 10000, batchSize: 200, speedBonus: 0 })

const trainingResult = computed(() => {
  const tier = troopTierOptions.find((t) => t.tier === training.tier) ?? troopTierOptions[3]
  const count = training.count || 0
  const batch = training.batchSize || 1
  const bonus = 1 + (training.speedBonus || 0) / 100
  const batches = Math.ceil(count / batch)
  const perBatchMin = (tier.baseTime * batch) / bonus
  const totalMin = perBatchMin * batches
  return {
    batches,
    perBatchMin,
    totalMin,
    power: count * tier.power,
    food: count * tier.food,
    wood: count * tier.wood,
    stone: count * tier.stone,
    gold: count * tier.gold,
  }
})

// ─── Healing Cost ───
// Healing costs per troop (food, wood, stone, gold) and time in minutes per troop
const healTiers = reactive([
  { label: 'T1', count: 0, foodPer: 25,  woodPer: 15,  stonePer: 0,   goldPer: 0,   timePer: 0.1 },
  { label: 'T2', count: 0, foodPer: 50,  woodPer: 30,  stonePer: 15,  goldPer: 0,   timePer: 0.2 },
  { label: 'T3', count: 0, foodPer: 100, woodPer: 60,  stonePer: 40,  goldPer: 15,  timePer: 0.5 },
  { label: 'T4', count: 0, foodPer: 200, woodPer: 120, stonePer: 80,  goldPer: 30,  timePer: 1.0 },
  { label: 'T5', count: 0, foodPer: 400, woodPer: 250, stonePer: 160, goldPer: 60,  timePer: 2.0 },
])

const healSpeedBonus = ref(0)
const hospitalCapacity = ref(50000)
const allianceHelps = ref(0)
const TECH_FLOOR_MIN = 3

/**
 * RoK Alliance Help formula (iterative):
 * Each tap: reduction = max(1% of current remaining time, tech floor)
 * The 1% rule dominates for large queues; the floor dominates for small ones.
 */
function simulateHelps(startMin: number, taps: number, floor: number) {
  let remaining = startMin
  let totalSaved = 0
  for (let i = 0; i < taps && remaining > 0; i++) {
    const onePercent = remaining * 0.01
    const reduction = Math.max(onePercent, floor)
    const actual = Math.min(reduction, remaining)
    remaining -= actual
    totalSaved += actual
  }
  return { remaining, totalSaved }
}

/** How many taps to fully clear the queue */
function tapsToFinish(startMin: number, floor: number): number {
  if (startMin <= 0) return 0
  let remaining = startMin
  let taps = 0
  const maxIter = 100000 // safety cap
  while (remaining > 0.01 && taps < maxIter) {
    const reduction = Math.max(remaining * 0.01, floor)
    remaining -= Math.min(reduction, remaining)
    taps++
  }
  return taps >= maxIter ? Infinity : taps
}

const healResult = computed(() => {
  let food = 0, wood = 0, stone = 0, gold = 0, totalTroops = 0, rawMinutes = 0
  for (const t of healTiers) {
    const c = t.count || 0
    totalTroops += c
    food += c * t.foodPer
    wood += c * t.woodPer
    stone += c * t.stonePer
    gold += c * t.goldPer
    rawMinutes += c * t.timePer
  }
  const bonus = 1 + (healSpeedBonus.value || 0) / 100
  const baseMin = rawMinutes / bonus
  const floor = TECH_FLOOR_MIN
  const taps = allianceHelps.value || 0

  // First tap info
  const onePercent = baseMin * 0.01
  const firstTapMin = baseMin > 0 ? Math.max(onePercent, floor) : 0
  const firstTapRule = onePercent >= floor ? '1% rule' : 'floor rule'

  // Simulate all taps
  const { remaining: totalMin, totalSaved: savedMin } = simulateHelps(baseMin, taps, floor)

  const cap = hospitalCapacity.value || 1
  const batches = Math.ceil(totalTroops / cap)
  const ttf = baseMin > 0 ? tapsToFinish(baseMin, floor) : 0

  return { food, wood, stone, gold, totalTroops, baseMin, savedMin, totalMin, batches, firstTapMin, firstTapRule, tapsToFinish: ttf }
})
</script>

<style>
.alliance-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 9999px;
  background: var(--muted);
  outline: none;
  cursor: pointer;
}
.alliance-slider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 9999px;
  background: var(--muted);
}
.alliance-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary);
  border: 2px solid var(--background);
  cursor: pointer;
  margin-top: -6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.alliance-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
}
.alliance-slider::-moz-range-track {
  height: 6px;
  border-radius: 9999px;
  background: var(--muted);
  border: none;
}
.alliance-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border: 2px solid var(--background);
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}
</style>
