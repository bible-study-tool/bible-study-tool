fn main() {
    let binaries_dir = std::path::Path::new("binaries");
    if !binaries_dir.exists() {
        let _ = std::fs::create_dir_all(binaries_dir);
    }
    let placeholder = binaries_dir.join("placeholder.txt");
    if !placeholder.exists() {
        let _ = std::fs::write(&placeholder, "Placeholder for sidecar binaries\n");
    }
    tauri_build::build();
}
