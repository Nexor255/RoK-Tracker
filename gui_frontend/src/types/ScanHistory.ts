/**
 * Types for the Scan History feature.
 */

export interface ScanHistoryEntry {
  /** Absolute path to the scan output file */
  path: string
  /** Original filename */
  filename: string
  /** Scanner type that produced this file */
  scan_type: 'kingdom' | 'alliance' | 'honor' | 'seed'
  /** TOP (fresh scan) or NEXT (resumed scan) */
  prefix: 'TOP' | 'NEXT' | 'UNKNOWN'
  /** Number of governors scanned */
  governor_count: number
  /** Date the scan was performed (YYYY-MM-DD) */
  date: string
  /** Kingdom/scan name provided by the user */
  kingdom_name: string
  /** Random ID assigned to the scan run */
  run_id: string
  /** Output file format */
  format: 'xlsx' | 'csv' | 'jsonl'
  /** File size in bytes */
  size_bytes: number
  /** Last modified timestamp (unix epoch seconds) */
  modified: number
}

export interface ScanSummary {
  total_governors: number
  avg_power: number | null
  max_power: number | null
  total_power: number | null
  avg_killpoints: number | null
  max_killpoints: number | null
  avg_deaths: number | null
  max_deaths: number | null
  total_kills: number | null
  columns: string[]
}

export interface ScanDetailPayload {
  path: string
  columns: string[]
  rows: Record<string, unknown>[]
  summary: ScanSummary
  page: number
  page_size: number
  total_rows: number
  total_pages: number
}

export interface ScanGovernorDiff {
  /** Governor ID or Name (depending on join_key) */
  [key: string]: unknown
  name: string
  changes: Record<string, { old: unknown; new: unknown }>
}

export interface ScanComparePayload {
  summary_a: ScanSummary
  summary_b: ScanSummary
  added: Record<string, unknown>[]
  removed: Record<string, unknown>[]
  changed: ScanGovernorDiff[]
  join_key: string | null
}
