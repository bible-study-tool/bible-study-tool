use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;

pub struct EngineState {
    child: Mutex<Option<Child>>,
    pub port: u16,
}

impl EngineState {
    pub fn new(port: u16) -> Self {
        Self {
            child: Mutex::new(None),
            port,
        }
    }

    pub fn set_child(&self, child: Child) {
        let mut lock = self.child.lock().unwrap_or_else(|e| e.into_inner());
        if let Some(mut old) = lock.take() {
            let _ = old.kill();
            let _ = old.wait();
        }
        *lock = Some(child);
    }

    pub fn stop(&self) {
        let mut lock = self.child.lock().unwrap_or_else(|e| e.into_inner());
        if let Some(mut child) = lock.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

impl Drop for EngineState {
    fn drop(&mut self) {
        self.stop();
    }
}

/// Find an available localhost TCP port for the sidecar engine.
pub fn find_available_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|listener| listener.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(8000)
}

/// Helper to locate repository root by checking for directory markers (search/ and web/).
pub fn find_repo_root() -> Option<PathBuf> {
    let is_repo = |p: &std::path::Path| p.join("web").is_dir() && p.join("search").is_dir();

    if let Ok(cwd) = std::env::current_dir() {
        if let Some(root) = cwd.ancestors().find(|p| is_repo(p)) {
            return Some(root.to_path_buf());
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(root) = exe.ancestors().find(|p| is_repo(p)) {
            return Some(root.to_path_buf());
        }
    }
    None
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
    let roots = [
        find_repo_root(),
        std::env::current_dir().ok(),
    ];

    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    let primary_dist = "dist/bible-study-macos-arm64/bible-study";
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    let primary_dist = "dist/bible-study-macos-x86_64/bible-study";
    #[cfg(target_os = "linux")]
    let primary_dist = "dist/bible-study-linux-x86_64/bible-study";
    #[cfg(target_os = "windows")]
    let primary_dist = "dist/bible-study-windows-x86_64/bible-study.exe";

    for root_opt in &roots {
        if let Some(root) = root_opt {
            #[cfg(target_os = "windows")]
            let candidates = [
                root.join("src-tauri/binaries/bible-study.exe"),
                root.join(primary_dist),
                root.join("dist/bible-study/bible-study.exe"),
                root.join("bible-study.exe"),
            ];
            #[cfg(not(target_os = "windows"))]
            let candidates = [
                root.join("src-tauri/binaries/bible-study"),
                root.join(primary_dist),
                root.join("dist/bible-study/bible-study"),
                root.join("bible-study"),
            ];

            for candidate in &candidates {
                if candidate.is_file() {
                    return Some(candidate.clone());
                }
            }
        }
    }

    None
}

/// Resolve the launch command for the backend engine:
/// 1. Frozen standalone binary if present (production / packaged desktop app)
/// 2. Local Python virtual environment in repository if running in dev mode
pub fn resolve_engine_command(app_handle: &tauri::AppHandle, port: u16) -> Option<Command> {
    if let Some(engine_path) = resolve_engine_path(app_handle) {
        log::info!("Spawning standalone frozen engine at {:?}", engine_path);
        let mut cmd = Command::new(&engine_path);
        if let Some(engine_dir) = engine_path.parent() {
            cmd.current_dir(engine_dir);
        }
        cmd.stdin(std::process::Stdio::null())
            .arg("--port")
            .arg(port.to_string())
            .arg("--no-browser");

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x08000000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }

        return Some(cmd);
    }

    // Development mode fallback: spawn Python server from repository root
    if let Some(repo_root) = find_repo_root() {
        #[cfg(target_os = "windows")]
        let venv_rel = ["Scripts", "python.exe"];
        #[cfg(not(target_os = "windows"))]
        let venv_rel = ["bin", "python"];

        let mut venv_candidates = Vec::new();
        if let Ok(active_venv) = std::env::var("VIRTUAL_ENV") {
            venv_candidates.push(PathBuf::from(active_venv).join(venv_rel[0]).join(venv_rel[1]));
        }
        venv_candidates.push(repo_root.join(".venv").join(venv_rel[0]).join(venv_rel[1]));
        venv_candidates.push(repo_root.join("venv").join(venv_rel[0]).join(venv_rel[1]));

        let py_bin = venv_candidates
            .into_iter()
            .find(|p| p.is_file())
            .unwrap_or_else(|| {
                #[cfg(target_os = "windows")]
                { PathBuf::from("python") }
                #[cfg(not(target_os = "windows"))]
                { PathBuf::from("python3") }
            });

        log::info!("Spawning development Python engine using {:?} from {:?}", py_bin, repo_root);
        let mut cmd = Command::new(py_bin);
        cmd.current_dir(&repo_root);
        cmd.stdin(std::process::Stdio::null())
            .arg("-m")
            .arg("search.ui.web")
            .arg("--port")
            .arg(port.to_string())
            .arg("--no-browser");

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x08000000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }

        return Some(cmd);
    }

    None
}

/// Poll the /api/health endpoint until the local server responds with 200 OK.
pub fn wait_for_server(port: u16, max_attempts: usize) -> bool {
    let addr = format!("127.0.0.1:{}", port);
    for attempt in 0..max_attempts {
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
        if attempt + 1 < max_attempts {
            std::thread::sleep(Duration::from_millis(150));
        }
    }
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // 1. Detect port configuration or existing active server
    let env_port = std::env::var("BIBLE_STUDY_PORT")
        .ok()
        .and_then(|val| val.parse::<u16>().ok());

    let (port, spawn_needed) = match env_port {
        Some(p) if wait_for_server(p, 1) => {
            log::info!("Connecting to existing Bible Study server on specified port {}", p);
            (p, false)
        }
        Some(p) => {
            log::info!("Spawning Bible Study engine on configured port {}", p);
            (p, true)
        }
        None => {
            if wait_for_server(8000, 1) {
                log::info!("Connecting to existing Bible Study server on default port 8000");
                (8000, false)
            } else {
                (find_available_port(), true)
            }
        }
    };

    tauri::Builder::default()
        .manage(EngineState::new(port))
        .setup(move |app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if spawn_needed {
                let mut spawned = false;
                if let Some(mut cmd) = resolve_engine_command(app.handle(), port) {
                    match cmd.spawn() {
                        Ok(child) => {
                            app.state::<EngineState>().set_child(child);
                            spawned = true;
                        }
                        Err(e) => {
                            log::error!("Failed to spawn engine sidecar: {:?}", e);
                        }
                    }
                } else {
                    log::warn!("No standalone engine or python environment found to spawn on port {}", port);
                }

                // Wait for engine readiness only if process was successfully spawned (fail-fast)
                if spawned {
                    let ready = wait_for_server(port, 70);
                    if !ready {
                        log::error!("Engine did not report ready within timeout on port {}", port);
                    }
                }
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
