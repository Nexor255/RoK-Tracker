mod commands;
mod sidecar;

use sidecar::SidecarManager;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarManager::new())
        .setup(|app| {
            // Create deps folders next to the exe so the user just needs to add files
            let exe_dir = std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|d| d.to_path_buf()));

            if let Some(dir) = exe_dir {
                let _ = std::fs::create_dir_all(dir.join("deps").join("platform-tools"));
                let _ = std::fs::create_dir_all(dir.join("deps").join("tessdata"));
                let _ = std::fs::create_dir_all(dir.join("deps").join("inputs"));
            }

            // Spawn the Python sidecar on app startup
            let sidecar = app.state::<SidecarManager>();
            let handle = app.handle().clone();
            if let Err(e) = sidecar.spawn(handle) {
                eprintln!("WARNING: Failed to spawn Python sidecar: {}", e);
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
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
