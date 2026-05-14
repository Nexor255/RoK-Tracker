import { defineStore, acceptHMRUpdate } from 'pinia'
import { ref, computed } from 'vue'
import type { ScanHistoryEntry, ScanDetailPayload, ScanComparePayload } from '@/types/ScanHistory'

export const useHistoryStore = defineStore('history', () => {
  const scanHistory = ref<ScanHistoryEntry[]>([])
  const loading = ref(false)
  const filterType = ref<string>('all')
  const searchQuery = ref('')

  // Detail view state
  const selectedDetail = ref<ScanDetailPayload | null>(null)
  const detailLoading = ref(false)

  // Compare state
  const compareSelections = ref<string[]>([])
  const compareResult = ref<ScanComparePayload | null>(null)
  const compareLoading = ref(false)
  const compareMode = ref(false)

  /** Filtered and searched scan list */
  const filteredHistory = computed(() => {
    let list = scanHistory.value

    // Filter by scan type
    if (filterType.value !== 'all') {
      list = list.filter((s) => s.scan_type === filterType.value)
    }

    // Filter by search query (kingdom name or run_id)
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      list = list.filter(
        (s) =>
          s.kingdom_name.toLowerCase().includes(q) ||
          s.run_id.toLowerCase().includes(q) ||
          s.filename.toLowerCase().includes(q),
      )
    }

    return list
  })

  /** Group scans by date for display */
  const groupedByDate = computed(() => {
    const groups: Record<string, ScanHistoryEntry[]> = {}
    for (const scan of filteredHistory.value) {
      const dateKey = scan.date || 'Unknown Date'
      if (!groups[dateKey]) groups[dateKey] = []
      groups[dateKey].push(scan)
    }
    return groups
  })

  /** Total count of all scan files */
  const totalCount = computed(() => scanHistory.value.length)

  /** Count by type */
  const countByType = computed(() => {
    const counts: Record<string, number> = { kingdom: 0, alliance: 0, honor: 0, seed: 0 }
    for (const scan of scanHistory.value) {
      counts[scan.scan_type] = (counts[scan.scan_type] || 0) + 1
    }
    return counts
  })

  function removeScan(path: string) {
    scanHistory.value = scanHistory.value.filter((s) => s.path !== path)
    // If the deleted file was being viewed, close the detail
    if (selectedDetail.value?.path === path) {
      selectedDetail.value = null
    }
  }

  function clearDetail() {
    selectedDetail.value = null
    detailLoading.value = false
  }

  function toggleCompareSelection(path: string) {
    const idx = compareSelections.value.indexOf(path)
    if (idx >= 0) {
      compareSelections.value.splice(idx, 1)
    } else if (compareSelections.value.length < 2) {
      compareSelections.value.push(path)
    }
  }

  function clearCompare() {
    compareResult.value = null
    compareLoading.value = false
    compareSelections.value = []
    compareMode.value = false
  }

  return {
    scanHistory,
    loading,
    filterType,
    searchQuery,
    selectedDetail,
    detailLoading,
    compareSelections,
    compareResult,
    compareLoading,
    compareMode,
    filteredHistory,
    groupedByDate,
    totalCount,
    countByType,
    removeScan,
    clearDetail,
    toggleCompareSelection,
    clearCompare,
  }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useHistoryStore, import.meta.hot))
}
