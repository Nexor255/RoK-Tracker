/**
 * Type-safe sidecar event definitions.
 *
 * Defines a discriminated union of all sidecar events so that
 * `onSidecarEvent('event_name', (data) => ...)` infers the correct
 * payload type for each event without manual `as` casts.
 */
import type { FullConfig } from '@/schema/FullConfig'
import type { ScanPreset } from '@/schema/ScanPreset'
import type { KingdomGovernorData } from '@/schema/KingdomGovernorData'
import type { KingdomAdditionalData } from '@/schema/KingdomAdditionalData'
import type { BatchGovernorData } from '@/schema/BatchGovernorData'
import type { BatchAdditionalData } from '@/schema/BatchAdditionalData'
import type { ScanHistoryEntry, ScanDetailPayload, ScanComparePayload } from '@/types/ScanHistory'

/**
 * Map of sidecar event names to their payload types.
 * `void` means the event carries no payload.
 */
export interface SidecarEventMap {
  // Lifecycle
  ready: void
  stderr: string

  // Config
  config_loaded: FullConfig
  config_saved: void
  presets_loaded: ScanPreset[]
  presets_saved: void

  // Kingdom scanner
  kingdom_scan_id: string
  kingdom_governor_update: {
    gov: KingdomGovernorData
    extra: KingdomAdditionalData
  }
  kingdom_state_update: string
  kingdom_ask_confirm: string
  kingdom_scan_finished: void

  // Batch scanners (Alliance / Honor / Seed)
  batch_scan_id: {
    id: string
    type: string
  }
  batch_update: {
    gov: BatchGovernorData[]
    extra: BatchAdditionalData
    type: string
  }
  batch_state_update: {
    msg: string
    type: string
  }
  batch_ask_confirm: {
    msg: string
    type: string
  }
  batch_scan_finished: string | Record<string, unknown>

  // Scan History
  scan_history_list: ScanHistoryEntry[]
  scan_detail: ScanDetailPayload
  scan_compare_result: ScanComparePayload
  scan_file_deleted: string
  scan_folder_path: string

  // Errors
  error: string

  // Emulators
  emulators_detected: { id: string; name: string; port: number }[]
}

/** Union of all valid sidecar event names */
export type SidecarEventName = keyof SidecarEventMap
