mod commands;
mod sidecar;

use sidecar::SidecarManager;
use tauri::{Emitter, Manager};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_opener::init())
        .manage(SidecarManager::new())
        .setup(|app| {
            #[cfg(desktop)]
            app.handle()
                .plugin(tauri_plugin_updater::Builder::new().build())?;
            // Create deps/inputs folder next to the exe (bundled via Tauri resources)
            let exe_dir = std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|d| d.to_path_buf()));

            if let Some(dir) = exe_dir {
                let _ = std::fs::create_dir_all(dir.join("deps").join("inputs"));
                let _ = std::fs::create_dir_all(dir.join("deps").join("ch_templates"));
            }

            // Spawn the Python sidecar on app startup
            let sidecar = app.state::<SidecarManager>();
            let handle = app.handle().clone();
            if let Err(e) = sidecar.spawn(handle.clone()) {
                eprintln!("CRITICAL: Failed to spawn Python sidecar: {}", e);
                // Emit error to frontend so the user sees it
                let _ = handle.emit(
                    "sidecar:error",
                    serde_json::Value::String(format!(
                        "Failed to start scanner backend: {}. The app will not function correctly.",
                        e
                    )),
                );
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::load_config,
            commands::load_scan_presets,
            commands::save_config,
            commands::save_scan_presets,
            commands::start_kingdom_scan,
            commands::stop_kingdom_scan,
            commands::confirm_kingdom,
            commands::start_batch_scan,
            commands::stop_batch_scan,
            commands::confirm_batch,
            commands::list_scan_history,
            commands::get_scan_detail,
            commands::compare_scans,
            commands::delete_scan_file,
            commands::open_scan_folder,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
