<template>
  <div class="flex h-full flex-col">
    <Tabs v-model="tab" class="flex h-full flex-col">
      <div class="px-4 pt-3 pb-2">
        <TabsList class="inline-flex w-auto gap-1 rounded-full bg-muted/60 p-1 backdrop-blur-sm ring-1 ring-border/40">
          <TabsTrigger
            value="kingdom"
            class="gap-2.5 rounded-full px-4 py-2 text-sm font-medium text-muted-foreground transition-all duration-200 hover:text-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-md data-[state=active]:shadow-primary/25"
          >
            <Crown class="h-4 w-4" />
            Kingdom
          </TabsTrigger>
          <TabsTrigger
            value="seed"
            class="gap-2.5 rounded-full px-4 py-2 text-sm font-medium text-muted-foreground transition-all duration-200 hover:text-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-md data-[state=active]:shadow-primary/25"
          >
            <Sprout class="h-4 w-4" />
            Seed
          </TabsTrigger>
          <TabsTrigger
            value="honor"
            class="gap-2.5 rounded-full px-4 py-2 text-sm font-medium text-muted-foreground transition-all duration-200 hover:text-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-md data-[state=active]:shadow-primary/25"
          >
            <Award class="h-4 w-4" />
            Honor
          </TabsTrigger>
          <TabsTrigger
            value="alliance"
            class="gap-2.5 rounded-full px-4 py-2 text-sm font-medium text-muted-foreground transition-all duration-200 hover:text-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-md data-[state=active]:shadow-primary/25"
          >
            <Shield class="h-4 w-4" />
            Alliance
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="kingdom" class="flex-1 overflow-hidden p-4 focus-visible:outline-none data-[state=active]:flex data-[state=active]:flex-col min-h-0">
        <KingdomScanner class="flex-1 min-h-0" />
      </TabsContent>
      <TabsContent value="seed" class="flex-1 overflow-hidden p-4 focus-visible:outline-none data-[state=active]:flex data-[state=active]:flex-col min-h-0">
        <BatchScanner batch-type="Seed" class="flex-1 min-h-0" />
      </TabsContent>
      <TabsContent value="honor" class="flex-1 overflow-hidden p-4 focus-visible:outline-none data-[state=active]:flex data-[state=active]:flex-col min-h-0">
        <BatchScanner batch-type="Honor" class="flex-1 min-h-0" />
      </TabsContent>
      <TabsContent value="alliance" class="flex-1 overflow-hidden p-4 focus-visible:outline-none data-[state=active]:flex data-[state=active]:flex-col min-h-0">
        <BatchScanner batch-type="Alliance" class="flex-1 min-h-0" />
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Crown, Sprout, Award, Shield } from 'lucide-vue-next'
import KingdomScanner from '@/components/KingdomScanner.vue'
import BatchScanner from '@/components/BatchScanner.vue'

const tab = ref('kingdom')
</script>
