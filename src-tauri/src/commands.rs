use serde_json::{json, Value};
use tauri::State;

use crate::sidecar::SidecarManager;

/// Send a generic command to the Python sidecar.
fn send(sidecar: &SidecarManager, cmd: &str, args: Option<Value>) -> Result<(), String> {
    sidecar.send_command(cmd, args)
}

#[tauri::command]
pub fn load_config(sidecar: State<'_, SidecarManager>) -> Result<(), String> {
    send(&sidecar, "LoadFullConfig", None)
}

#[tauri::command]
pub fn load_scan_presets(sidecar: State<'_, SidecarManager>) -> Result<(), String> {
    send(&sidecar, "LoadScanPresets", None)
}

#[tauri::command]
pub fn save_config(sidecar: State<'_, SidecarManager>, config: Value) -> Result<(), String> {
    send(&sidecar, "SaveConfig", Some(json!({ "config": config })))
}

#[tauri::command]
pub fn save_scan_presets(
    sidecar: State<'_, SidecarManager>,
    presets: Value,
) -> Result<(), String> {
    send(
        &sidecar,
        "SaveScanPresets",
        Some(json!({ "presets": presets })),
    )
}

#[tauri::command]
pub fn start_kingdom_scan(
    sidecar: State<'_, SidecarManager>,
    config: Value,
    preset: Value,
) -> Result<(), String> {
    send(
        &sidecar,
        "StartKingdomScan",
        Some(json!({ "config": config, "preset": preset })),
    )
}

#[tauri::command]
pub fn stop_kingdom_scan(sidecar: State<'_, SidecarManager>) -> Result<(), String> {
    send(&sidecar, "StopKingdomScan", None)
}

#[tauri::command]
pub fn confirm_kingdom(
    sidecar: State<'_, SidecarManager>,
    confirmed: bool,
) -> Result<(), String> {
    send(
        &sidecar,
        "ConfirmKingdom",
        Some(json!({ "confirmed": confirmed })),
    )
}

#[tauri::command]
pub fn start_batch_scan(
    sidecar: State<'_, SidecarManager>,
    config: Value,
    batch_type: String,
) -> Result<(), String> {
    send(
        &sidecar,
        "StartBatchScan",
        Some(json!({ "config": config, "batch_type": batch_type })),
    )
}

#[tauri::command]
pub fn stop_batch_scan(
    sidecar: State<'_, SidecarManager>,
    batch_type: String,
) -> Result<(), String> {
    send(
        &sidecar,
        "StopBatchScan",
        Some(json!({ "batch_type": batch_type })),
    )
}

#[tauri::command]
pub fn confirm_batch(
    sidecar: State<'_, SidecarManager>,
    confirmed: bool,
    batch_type: String,
) -> Result<(), String> {
    send(
        &sidecar,
        "ConfirmBatch",
        Some(json!({ "confirmed": confirmed, "batch_type": batch_type })),
    )
}
