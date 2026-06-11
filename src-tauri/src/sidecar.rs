use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use tauri::{AppHandle, Emitter, Runtime};

/// Manages the Python sidecar subprocess lifecycle.
pub struct SidecarManager {
    child: Arc<Mutex<Option<Child>>>,
    stdin_handle: Arc<Mutex<Option<std::process::ChildStdin>>>,
}

impl SidecarManager {
    pub fn new() -> Self {
        Self {
            child: Arc::new(Mutex::new(None)),
            stdin_handle: Arc::new(Mutex::new(None)),
        }
    }

    /// Spawn the Python sidecar process and begin reading stdout events.
    pub fn spawn<R: Runtime>(&self, app_handle: AppHandle<R>) -> Result<(), String> {
        // Get the project root.
        // In dev mode, current_dir() points to src-tauri/ so we go up one level
        // to reach the repo root where scanner_sidecar.py lives.
        let cwd = std::env::current_dir()
            .map_err(|e| format!("Failed to get current dir: {}", e))?;

        // In dev mode, run scanner_sidecar.py directly with Python
        // In prod mode, run the bundled sidecar executable (placed by Tauri externalBin)
        let (program, args, work_dir) = if cfg!(debug_assertions) {
            // Tauri runs from src-tauri/, so the repo root is one level up
            let project_root = cwd.parent().unwrap_or(&cwd).to_path_buf();
            let script = project_root.join("scanner_sidecar.py");
            eprintln!("[sidecar] Dev mode — script: {}", script.display());
            let python_exe = project_root.join(".venv").join("Scripts").join("python.exe");
            (python_exe.to_string_lossy().to_string(), vec![script.to_string_lossy().to_string()], project_root)
        } else {
            // Tauri places externalBin binaries next to the app executable,
            // keeping the target-triple suffix: scanner_sidecar-{triple}[.exe]
            let exe_dir = std::env::current_exe()
                .map_err(|e| format!("Failed to get exe path: {}", e))?
                .parent()
                .ok_or("Failed to get exe dir")?
                .to_path_buf();

            let ext = if cfg!(target_os = "windows") { ".exe" } else { "" };
            let target_triple = env!("TARGET_TRIPLE");

            // Tauri's NSIS installer strips the target-triple suffix from
            // externalBin filenames, so we check both the suffixed name
            // (used during development builds) and the plain name (installed).
            let candidates = [
                format!("scanner_sidecar-{}{}", target_triple, ext),  // dev / cargo build
                format!("scanner_sidecar{}", ext),                     // NSIS installed
            ];

            let sidecar_path = candidates.iter()
                .map(|name| exe_dir.join(name))
                .inspect(|p| eprintln!("[sidecar] Checking: {}", p.display()))
                .find(|p| p.exists())
                .ok_or_else(|| format!(
                    "Sidecar binary not found next to '{}'. Tried: {}",
                    exe_dir.display(),
                    candidates.join(", ")
                ))?;

            eprintln!("[sidecar] Found sidecar at: {}", sidecar_path.display());

            (sidecar_path.to_string_lossy().to_string(), vec![], exe_dir)
        };

        let mut command = Command::new(&program);
        command.args(&args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .current_dir(&work_dir);

        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x08000000;
            command.creation_flags(CREATE_NO_WINDOW);
        }

        let mut child = command.spawn()
            .map_err(|e| format!("Failed to spawn sidecar '{}': {}", program, e))?;

        // Take ownership of stdin
        let stdin = child.stdin.take().ok_or("Failed to get sidecar stdin")?;
        let stdout = child.stdout.take().ok_or("Failed to get sidecar stdout")?;
        let stderr = child.stderr.take().ok_or("Failed to get sidecar stderr")?;

        *self.stdin_handle.lock().unwrap() = Some(stdin);
        *self.child.lock().unwrap() = Some(child);

        // Spawn a reader thread that parses JSON lines from stdout
        // and emits them as Tauri events to the frontend
        let app_handle_stdout = app_handle.clone();
        thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                match line {
                    Ok(text) => {
                        if text.trim().is_empty() {
                            continue;
                        }
                        match serde_json::from_str::<Value>(&text) {
                            Ok(json) => {
                                let event = json
                                    .get("event")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("unknown");
                                let data = json.get("data").cloned();

                                // Emit as a Tauri event: "sidecar:{event_name}"
                                let event_name = format!("sidecar:{}", event);
                                let _ = app_handle_stdout.emit(&event_name, data);
                            }
                            Err(e) => {
                                eprintln!("Sidecar JSON parse error: {} — line: {}", e, text);
                            }
                        }
                    }
                    Err(e) => {
                        eprintln!("Sidecar stdout read error: {}", e);
                        break;
                    }
                }
            }
        });

        // Spawn a reader thread for stderr — log to file and emit to frontend
        let stderr_log_path = work_dir.join("sidecar_stderr.log");
        thread::spawn(move || {
            let mut log_file = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&stderr_log_path)
                .ok();

            let reader = BufReader::new(stderr);
            for line in reader.lines() {
                match line {
                    Ok(text) => {
                        if text.trim().is_empty() {
                            continue;
                        }
                        // Write to log file
                        if let Some(ref mut f) = log_file {
                            let _ = writeln!(f, "{}", text);
                        }
                        // Also emit to frontend so errors are visible
                        let _ = app_handle.emit("sidecar:stderr", &text);
                        eprintln!("[sidecar stderr] {}", text);
                    }
                    Err(e) => {
                        eprintln!("Sidecar stderr read error: {}", e);
                        break;
                    }
                }
            }
        });

        Ok(())
    }

    /// Send a JSON command to the sidecar's stdin.
    pub fn send_command(&self, cmd: &str, args: Option<Value>) -> Result<(), String> {
        let mut msg = serde_json::json!({ "cmd": cmd });
        if let Some(a) = args {
            msg["args"] = a;
        }

        let mut stdin_guard = self.stdin_handle.lock().unwrap();
        if let Some(ref mut stdin) = *stdin_guard {
            let line = serde_json::to_string(&msg).map_err(|e| e.to_string())?;
            stdin
                .write_all(line.as_bytes())
                .map_err(|e| format!("Failed to write to sidecar stdin: {}", e))?;
            stdin
                .write_all(b"\n")
                .map_err(|e| format!("Failed to write newline: {}", e))?;
            stdin.flush().map_err(|e| format!("Failed to flush: {}", e))?;
            Ok(())
        } else {
            Err("Sidecar not running".to_string())
        }
    }

    /// Kill the sidecar process.
    pub fn kill(&self) {
        if let Some(ref mut child) = *self.child.lock().unwrap() {
            let _ = child.kill();
        }
        *self.stdin_handle.lock().unwrap() = None;
    }
}

impl Drop for SidecarManager {
    fn drop(&mut self) {
        self.kill();
    }
}
