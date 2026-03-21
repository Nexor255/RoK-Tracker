<template>
  <div class="flex h-full items-center justify-center">
    <Card class="w-full max-w-md text-center">
      <CardHeader>
        <div class="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <Calculator class="h-8 w-8 text-muted-foreground" />
        </div>
        <CardTitle class="text-xl">Calculators</CardTitle>
        <CardDescription>
          Kill point calculators, resource planners, and more are on the way.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Badge variant="secondary">Coming Soon</Badge>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { Calculator } from 'lucide-vue-next'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
</script>
