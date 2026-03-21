<template>
  <div class="flex h-full flex-col items-center justify-center gap-4">
    <div class="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
      <SearchX class="h-10 w-10 text-muted-foreground" />
    </div>
    <div class="text-center">
      <h1 class="text-5xl font-bold tracking-tight">404</h1>
      <p class="mt-2 text-lg text-muted-foreground">Page not found</p>
    </div>
    <Button variant="outline" @click="$router.push('/scanner')">
      <ArrowLeft class="mr-2 h-4 w-4" />
      Back to Scanners
    </Button>
  </div>
</template>

<script setup lang="ts">
import { SearchX, ArrowLeft } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
</script>
