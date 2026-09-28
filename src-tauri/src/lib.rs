use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;

pub struct EngineState {
    pub child: Mutex<Option<Child>>,
    pub port: u16,
}

impl EngineState {
    pub fn stop(&self) {
        if let Ok(mut lock) = self.child.lock() {
            if let Some(mut child) = lock.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

/// Find an available localhost TCP port for the sidecar engine.
pub fn find_available_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|listener| listener.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(8000)
}

/// Resolve the path to the frozen bible-study engine executable.
pub fn resolve_engine_path(_app_handle: &tauri::AppHandle) -> Option<PathBuf> {
    // 1. Check relative to current executable (packaged app / app bundle)
    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(parent) = current_exe.parent() {
            // macOS App Bundle: Contents/MacOS/app -> Contents/Resources/binaries/bible-study
            #[cfg(target_os = "macos")]
            {
                let in_resources = parent.join("../Resources/binaries/bible-study");
                if in_resources.is_file() {
                    return Some(in_resources);
                }
                let in_resources_direct = parent.join("../Resources/bible-study");
                if in_resources_direct.is_file() {
                    return Some(in_resources_direct);
                }
                let alongside = parent.join("bible-study");
                if alongside.is_file() {
                    return Some(alongside);
                }
            }

            // Windows: bible-study.exe in binaries/ or alongside
            #[cfg(target_os = "windows")]
            {
                let in_binaries = parent.join("binaries/bible-study.exe");
                if in_binaries.is_file() {
                    return Some(in_binaries);
                }
                let alongside = parent.join("bible-study.exe");
                if alongside.is_file() {
                    return Some(alongside);
                }
            }

            // Linux: bible-study in binaries/ or alongside
            #[cfg(target_os = "linux")]
            {
                let in_binaries = parent.join("binaries/bible-study");
                if in_binaries.is_file() {
                    return Some(in_binaries);
                }
                let alongside = parent.join("bible-study");
                if alongside.is_file() {
                    return Some(alongside);
                }
            }
        }
    }

    // 2. Check standard release dist/ folders in repo or working directory
    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let candidates = [
        cwd.join("src-tauri/binaries/bible-study"),
        cwd.join("src-tauri/binaries/bible-study.exe"),
        cwd.join("dist/bible-study-linux-x86_64/bible-study"),
        cwd.join("dist/bible-study-macos-arm64/bible-study"),
        cwd.join("dist/bible-study-macos-x86_64/bible-study"),
        cwd.join("dist/bible-study-windows-x86_64/bible-study.exe"),
        cwd.join("dist/bible-study/bible-study"),
        cwd.join("dist/bible-study/bible-study.exe"),
        cwd.join("bible-study"),
        cwd.join("bible-study.exe"),
    ];

    for candidate in &candidates {
        if candidate.is_file() {
            return Some(candidate.clone());
        }
    }

    None
}

/// Poll the /api/health endpoint until the local server responds with 200 OK.
pub fn wait_for_server(port: u16, max_attempts: usize) -> bool {
    let addr = format!("127.0.0.1:{}", port);
    for _ in 0..max_attempts {
        if let Ok(mut stream) = TcpStream::connect(&addr) {
            let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
            let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
            let req = "GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
            if stream.write_all(req.as_bytes()).is_ok() {
                let mut buf = [0u8; 128];
                if let Ok(n) = stream.read(&mut buf) {
                    if n > 0 && String::from_utf8_lossy(&buf[..n]).contains("200 OK") {
                        return true;
                    }
                }
            }
        }
        std::thread::sleep(Duration::from_millis(150));
    }
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let port = find_available_port();

    tauri::Builder::default()
        .manage(EngineState {
            child: Mutex::new(None),
            port,
        })
        .setup(move |app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Resolve and spawn the engine sidecar
            if let Some(engine_path) = resolve_engine_path(app.handle()) {
                log::info!("Spawning Bible Study engine at {:?}", engine_path);
                let mut cmd = Command::new(&engine_path);
                if let Some(engine_dir) = engine_path.parent() {
                    cmd.current_dir(engine_dir);
                }
                cmd.stdin(std::process::Stdio::null())
                    .arg("--server")
                    .arg("--port")
                    .arg(port.to_string())
                    .arg("--no-browser");

                // Prevent console window from flashing on Windows
                #[cfg(target_os = "windows")]
                {
                    use std::os::windows::process::CommandExt;
                    const CREATE_NO_WINDOW: u32 = 0x08000000;
                    cmd.creation_flags(CREATE_NO_WINDOW);
                }

                match cmd.spawn() {
                    Ok(child) => {
                        let state = app.state::<EngineState>();
                        if let Ok(mut lock) = state.child.lock() {
                            *lock = Some(child);
                        }
                    }
                    Err(e) => {
                        log::error!("Failed to spawn engine sidecar: {:?}", e);
                    }
                }
            } else {
                log::warn!("No standalone engine found. Ensure a local server is running on port {}", port);
            }

            // Wait for engine readiness
            let ready = wait_for_server(port, 70);
            if !ready {
                log::warn!("Engine did not report ready within timeout on port {}", port);
            }

            // Navigate window to local engine and display
            if let Some(window) = app.get_webview_window("main") {
                let target_url = format!("http://127.0.0.1:{}", port);
                if let Ok(parsed) = target_url.parse() {
                    let _ = window.navigate(parsed);
                }
                let _ = window.show();
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            // Clean up sidecar process when main window closes
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                window.app_handle().state::<EngineState>().stop();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                app_handle.state::<EngineState>().stop();
            }
        });
}
