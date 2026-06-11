/**
 * Tauri-specific IPC client.
 * Uses @tauri-apps/api to invoke Rust commands and listen for sidecar events.
 */
import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { toRaw } from 'vue'
import type { FullConfig } from '@/schema/FullConfig'
import type { ScanPreset } from '@/schema/ScanPreset'

/**
 * Deep-clone a value while stripping Vue reactive proxies.
 * Ensures Tauri's invoke serializes a plain object, not a Proxy.
 */
function toPlain<T>(obj: T): T {
  return JSON.parse(JSON.stringify(toRaw(obj)))
}

/**
 * Wait for a specific sidecar event (or an error event) with a timeout.
 * Resolves when the expected event fires; rejects on error or timeout.
 *
 * IMPORTANT: We must await the listen() promises before starting the timeout
 * to guarantee the listener is registered before any command is sent.
 * Returns a { promise, ready } pair so callers can await registration.
 */
function waitForSidecarEvent(
  successEvent: string,
  timeoutMs = 10000,
): { promise: Promise<unknown>; ready: Promise<void> } {
  let unlistenSuccess: UnlistenFn = () => {}
  let unlistenError: UnlistenFn = () => {}
  let settled = false

  let resolveReady: () => void
  const ready = new Promise<void>((r) => { resolveReady = r })

  const promise = new Promise<unknown>((resolve, reject) => {
    let timer: ReturnType<typeof setTimeout> | null = null

    const cleanup = () => {
      if (timer) clearTimeout(timer)
      unlistenSuccess()
      unlistenError()
    }

    // Register both listeners, then start the timeout
    Promise.all([
      listen<unknown>(`sidecar:${successEvent}`, (event) => {
        if (settled) return
        settled = true
        cleanup()
        resolve(event.payload)
      }),
      listen<unknown>('sidecar:error', (event) => {
        if (settled) return
        settled = true
        cleanup()
        reject(new Error(String(event.payload)))
      }),
    ]).then(([uSuccess, uError]) => {
      unlistenSuccess = uSuccess
      unlistenError = uError
      // Start the timeout only AFTER listeners are live
      timer = setTimeout(() => {
        if (settled) return
        settled = true
        cleanup()
        reject(new Error(`Timed out waiting for ${successEvent}`))
      }, timeoutMs)
      // Signal that listeners are registered
      resolveReady!()
    })
  })

  return { promise, ready }
}

// ---- Commands (frontend → Rust → Python) ----

export async function loadFullConfig(): Promise<void> {
  return invoke('load_config')
}

export async function loadScanPresets(): Promise<void> {
  return invoke('load_scan_presets')
}

export async function saveConfig(config: FullConfig): Promise<void> {
  // Strip Vue reactive proxies so Tauri serializes a plain object
  const plainConfig = toPlain(config)

  // Set up the confirmation listener and wait for it to be registered
  const { promise: confirmation, ready } = waitForSidecarEvent('config_saved', 10000)
  await ready

  // Now send the command — listener is guaranteed to be live
  await invoke('save_config', { config: plainConfig })

  // Wait for the sidecar to confirm the save succeeded
  await confirmation
}

export function saveScanPresets(presets: ScanPreset[]): void {
  invoke('save_scan_presets', { presets: toPlain(presets) })
}

export function startKingdomScan(config: FullConfig, preset: ScanPreset): void {
  invoke('start_kingdom_scan', { config: toPlain(config), preset: toPlain(preset) })
}

export function stopKingdomScan(): void {
  invoke('stop_kingdom_scan')
}

export function confirmKingdom(confirmed: boolean): void {
  invoke('confirm_kingdom', { confirmed })
}

export function startBatchScan(config: FullConfig, batchType: string): void {
  invoke('start_batch_scan', { config: toPlain(config), batchType })
}

export function stopBatchScan(batchType: string): void {
  invoke('stop_batch_scan', { batchType })
}

export function confirmBatch(confirmed: boolean, batchType: string): void {
  invoke('confirm_batch', { confirmed, batchType })
}

// Aliases matching the names used by consumer components
export const confirmKingdomScan = confirmKingdom
export const confirmBatchScan = confirmBatch

// ---- Scan History ----

export function listScanHistory(): void {
  invoke('list_scan_history').catch((e) => console.error('listScanHistory failed:', e))
}

export function getScanDetail(path: string, page = 1, pageSize = 50): void {
  invoke('get_scan_detail', { path, page, pageSize }).catch((e) =>
    console.error('getScanDetail failed:', e),
  )
}

export function compareScanFiles(pathA: string, pathB: string): void {
  invoke('compare_scans', { pathA, pathB }).catch((e) =>
    console.error('compareScanFiles failed:', e),
  )
}

export function deleteScanFile(path: string): void {
  invoke('delete_scan_file', { path }).catch((e) => console.error('deleteScanFile failed:', e))
}

export function openScanFolder(path: string): void {
  invoke('open_scan_folder', { path }).catch((e) => console.error('openScanFolder failed:', e))
}

export function detectEmulators(): void {
  invoke('detect_emulators').catch((e) => console.error('detectEmulators failed:', e))
}

// ---- Events (Python → Rust → frontend) ----

import type { SidecarEventMap, SidecarEventName } from '@/types/SidecarEvents'

/**
 * Subscribe to a typed sidecar event.
 * The handler payload is inferred from the event name via SidecarEventMap.
 */
export function onSidecarEvent<E extends SidecarEventName>(
  eventName: E,
  handler: SidecarEventMap[E] extends void
    ? () => void
    : (data: SidecarEventMap[E]) => void,
): Promise<UnlistenFn> {
  return listen<SidecarEventMap[E]>(`sidecar:${eventName}`, (event) => {
    ;(handler as (data: SidecarEventMap[E]) => void)(event.payload)
  })
}
