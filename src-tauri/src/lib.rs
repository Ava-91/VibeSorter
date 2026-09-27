use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

use tauri::{Emitter, Manager};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

struct BackendState(Mutex<Option<CommandChild>>);
struct AnalysisState(Mutex<Option<CommandChild>>);

#[tauri::command]
async fn choose_folder(app: tauri::AppHandle) -> Result<Option<String>, String> {
    Ok(app
        .dialog()
        .file()
        .set_title("Choose an image library")
        .blocking_pick_folder()
        .map(|path| path.to_string()))
}

#[tauri::command]
async fn start_backend(app: tauri::AppHandle, folder: String, port: u16) -> Result<String, String> {
    let db = std::path::Path::new(&folder)
        .join(".vibesorter")
        .join("analysis.db");
    let db = db
        .to_str()
        .ok_or_else(|| "The selected folder path is not valid UTF-8.".to_string())?;

    if let Some(child) = app.state::<BackendState>().0.lock().unwrap().take() {
        let _ = child.kill();
    }

    let command = app
        .shell()
        .sidecar("vibesorter-sidecar")
        .map_err(|error| format!("Could not prepare VibeSorter backend: {error}"))?
        .args([
            "browser",
            "--db",
            db,
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
        ]);
    let (mut events, child) = command
        .spawn()
        .map_err(|error| format!("Could not start VibeSorter backend: {error}"))?;

    *app.state::<BackendState>().0.lock().unwrap() = Some(child);

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let _ = handle.emit(
                        "backend-log",
                        String::from_utf8_lossy(&bytes).to_string(),
                    );
                }
                CommandEvent::Stderr(bytes) => {
                    let _ = handle.emit(
                        "backend-error",
                        String::from_utf8_lossy(&bytes).to_string(),
                    );
                }
                CommandEvent::Terminated(payload) => {
                    let _ = handle.emit("backend-exited", payload.code);
                    break;
                }
                _ => {}
            }
        }
    });

    for _ in 0..50 {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return Ok(format!("http://127.0.0.1:{port}"));
        }
        std::thread::sleep(Duration::from_millis(100));
    }

    Err("VibeSorter started, but the local browser server did not become ready.".to_string())
}

#[tauri::command]
async fn index_folder(app: tauri::AppHandle, folder: String) -> Result<(), String> {
    if let Some(child) = app.state::<AnalysisState>().0.lock().unwrap().take() {
        let _ = child.kill();
    }

    let command = app
        .shell()
        .sidecar("vibesorter-sidecar")
        .map_err(|error| format!("Could not prepare VibeSorter analysis: {error}"))?
        .args(["index", &folder, "--json"]);
    let (mut events, child) = command
        .spawn()
        .map_err(|error| format!("Could not start analysis: {error}"))?;

    *app.state::<AnalysisState>().0.lock().unwrap() = Some(child);

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let _ = handle.emit(
                        "analysis-output",
                        String::from_utf8_lossy(&bytes).to_string(),
                    );
                }
                CommandEvent::Stderr(bytes) => {
                    let _ = handle.emit(
                        "analysis-error",
                        String::from_utf8_lossy(&bytes).to_string(),
                    );
                }
                CommandEvent::Terminated(payload) => {
                    *handle.state::<AnalysisState>().0.lock().unwrap() = None;
                    if payload.code == Some(0) {
                        let _ = handle.emit("analysis-finished", payload.code);
                    } else {
                        let _ = handle.emit("analysis-failed", payload.code);
                    }
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(())
}

#[tauri::command]
async fn cancel_index(app: tauri::AppHandle) -> Result<(), String> {
    let child = app
        .state::<AnalysisState>()
        .0
        .lock()
        .unwrap()
        .take();

    if let Some(child) = child {
        child
            .kill()
            .map_err(|error| format!("Could not cancel analysis: {error}"))?;
        let _ = app.emit("analysis-cancelled", ());
    }

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(BackendState(Mutex::new(None)))
        .manage(AnalysisState(Mutex::new(None)))
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let window = app.get_webview_window("main").expect("main window");
            window.set_title("VibeSorter").ok();
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            choose_folder,
            start_backend,
            index_folder,
            cancel_index
        ])
        .run(tauri::generate_context!())
        .expect("error while running VibeSorter desktop");
}
