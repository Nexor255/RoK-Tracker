<template>
  <div class="flex flex-col gap-3">
    <!-- Empty state -->
    <div
      v-if="filteredHistory.length === 0 && !loading"
      class="flex flex-col items-center justify-center py-16 text-center"
    >
      <div class="rounded-full bg-muted/50 p-4 mb-4">
        <FileSearch class="h-10 w-10 text-muted-foreground/50" />
      </div>
      <p class="text-sm font-medium text-muted-foreground">No scans found</p>
      <p class="text-xs text-muted-foreground/60 mt-1">
        {{ searchQuery || filterType !== 'all' ? 'Try adjusting your filters' : 'Complete a scan to see it here' }}
      </p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="flex flex-col gap-3">
      <div v-for="i in 3" :key="i" class="h-[88px] rounded-lg bg-muted/30 animate-pulse" />
    </div>

    <!-- Grouped scan entries -->
    <template v-for="(scans, date) in groupedByDate" :key="date">
      <div class="flex items-center gap-2 mt-2 first:mt-0">
        <Calendar class="h-3.5 w-3.5 text-muted-foreground/60" />
        <span class="text-xs font-medium text-muted-foreground/80 uppercase tracking-wider">{{ formatDateHeader(date as string) }}</span>
        <div class="flex-1 h-px bg-border/50" />
      </div>

      <div
        v-for="scan in scans"
        :key="scan.path"
        class="group relative flex items-center gap-4 rounded-lg border bg-card/80 backdrop-blur-sm px-4 py-3 transition-all duration-200 hover:bg-accent/50 hover:border-primary/30 hover:shadow-md cursor-pointer"
        :class="{
          'ring-2 ring-primary/50 border-primary/40': compareMode && compareSelections.includes(scan.path),
          'opacity-40 pointer-events-none': compareMode && scan.scan_type !== 'kingdom' && !compareSelections.includes(scan.path),
        }"
        @click="handleRowClick(scan)"
      >
        <!-- Compare checkbox (shown in compare mode for kingdom scans) -->
        <Checkbox
          v-if="compareMode && scan.scan_type === 'kingdom'"
          :checked="compareSelections.includes(scan.path)"
          class="shrink-0"
          @click.stop
          @update:checked="$emit('toggle-compare', scan.path)"
        />
        <!-- Scan type icon -->
        <div
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors"
          :class="scanTypeStyles[scan.scan_type]?.bg ?? 'bg-muted'"
        >
          <component
            :is="scanTypeStyles[scan.scan_type]?.icon ?? FileSpreadsheet"
            class="h-5 w-5"
            :class="scanTypeStyles[scan.scan_type]?.text ?? 'text-muted-foreground'"
          />
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-0.5">
            <Badge
              :variant="scan.prefix === 'NEXT' ? 'secondary' : 'default'"
              class="text-[10px] px-1.5 py-0 h-4"
            >
              {{ scan.prefix }}
            </Badge>
            <span class="text-sm font-semibold truncate">
              {{ scan.governor_count }} governors
            </span>
            <span class="text-xs text-muted-foreground">·</span>
            <span class="text-xs text-muted-foreground truncate">{{ scan.kingdom_name }}</span>
          </div>
          <div class="flex items-center gap-2 text-xs text-muted-foreground/70">
            <Badge variant="outline" class="text-[10px] px-1.5 py-0 h-4 capitalize">
              {{ scan.scan_type }}
            </Badge>
            <span>.{{ scan.format }}</span>
            <span>·</span>
            <span>{{ formatFileSize(scan.size_bytes) }}</span>
            <span v-if="scan.run_id" class="hidden sm:inline">·</span>
            <code v-if="scan.run_id" class="hidden sm:inline text-[10px] font-mono opacity-50">{{ scan.run_id }}</code>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <Tooltip>
            <TooltipTrigger as-child>
              <button
                class="rounded-md p-1.5 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-colors"
                @click.stop="$emit('view', scan.path)"
              >
                <Eye class="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p class="text-xs">View scan data</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <button
                class="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                @click.stop="$emit('open-folder', scan.path)"
              >
                <FolderOpen class="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p class="text-xs">Reveal in Explorer</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <button
                class="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                @click.stop="handleDelete(scan)"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p class="text-xs">Delete scan file</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </div>
    </template>
  </div>

  <!-- Delete confirmation dialog -->
  <AlertDialog :open="deleteDialogOpen">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Delete Scan File</AlertDialogTitle>
        <AlertDialogDescription>
          Are you sure you want to delete
          <span class="font-semibold">{{ scanToDelete?.filename }}</span>?
          This action cannot be undone.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel @click="deleteDialogOpen = false">Cancel</AlertDialogCancel>
        <AlertDialogAction
          class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          @click="confirmDelete"
        >
          Delete
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>

<script setup lang="ts">
import { ref, markRaw, type Component } from 'vue'
import {
  Crown,
  Shield,
  Award,
  Sprout,
  FileSpreadsheet,
  FolderOpen,
  Trash2,
  FileSearch,
  Calendar,
  Eye,
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { ScanHistoryEntry } from '@/types/ScanHistory'

const props = defineProps<{
  filteredHistory: ScanHistoryEntry[]
  groupedByDate: Record<string, ScanHistoryEntry[]>
  loading: boolean
  searchQuery: string
  filterType: string
  compareMode: boolean
  compareSelections: string[]
}>()

const emit = defineEmits<{
  'open-folder': [path: string]
  'delete': [path: string]
  'view': [path: string]
  'toggle-compare': [path: string]
}>()

// Row click handler: compare mode toggles selection, normal mode opens detail
function handleRowClick(scan: ScanHistoryEntry) {
  if (props.compareMode) {
    if (scan.scan_type === 'kingdom') {
      emit('toggle-compare', scan.path)
    }
  } else {
    emit('view', scan.path)
  }
}

// Scan type visual config
const scanTypeStyles: Record<string, { icon: Component; bg: string; text: string }> = {
  kingdom: { icon: markRaw(Crown), bg: 'bg-amber-500/10 dark:bg-amber-500/15', text: 'text-amber-600 dark:text-amber-400' },
  alliance: { icon: markRaw(Shield), bg: 'bg-blue-500/10 dark:bg-blue-500/15', text: 'text-blue-600 dark:text-blue-400' },
  honor: { icon: markRaw(Award), bg: 'bg-purple-500/10 dark:bg-purple-500/15', text: 'text-purple-600 dark:text-purple-400' },
  seed: { icon: markRaw(Sprout), bg: 'bg-green-500/10 dark:bg-green-500/15', text: 'text-green-600 dark:text-green-400' },
}

// Delete dialog state
const deleteDialogOpen = ref(false)
const scanToDelete = ref<ScanHistoryEntry | null>(null)

function handleDelete(scan: ScanHistoryEntry) {
  scanToDelete.value = scan
  deleteDialogOpen.value = true
}

function confirmDelete() {
  if (scanToDelete.value) {
    emit('delete', scanToDelete.value.path)
  }
  deleteDialogOpen.value = false
  scanToDelete.value = null
}

// Formatting helpers
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDateHeader(dateStr: string): string {
  if (!dateStr || dateStr === 'Unknown Date') return 'Unknown Date'
  try {
    const date = new Date(dateStr + 'T00:00:00')
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    if (diff === 0) return 'Today'
    if (diff === 1) return 'Yesterday'
    if (diff < 7) return `${diff} days ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return dateStr
  }
}
</script>
