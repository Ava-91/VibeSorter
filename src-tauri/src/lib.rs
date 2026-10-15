use std::net::{TcpListener, TcpStream};
use std::sync::{atomic::{AtomicU64, Ordering}, Mutex};
use std::time::Duration;

use tauri::{Emitter, Manager};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

struct BackendState(Mutex<Option<CommandChild>>);

struct AnalysisRun {
    id: u64,
    child: Option<CommandChild>,
    cancelled: bool,
}

struct AnalysisState {
    active: Mutex<Option<AnalysisRun>>,
    next_id: AtomicU64,
}

fn is_active_analysis_run(state: &AnalysisState, run_id: u64) -> bool {
    state.active.lock().unwrap().as_ref().is_some_and(|run| run.id == run_id)
}

fn finish_analysis_run(state: &AnalysisState, run_id: u64) -> Option<bool> {
    let mut active = state.active.lock().unwrap();
    if active.as_ref().is_some_and(|run| run.id == run_id) {
        active.take().map(|run| run.cancelled)
    } else {
        None
    }
}

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
    let port = if port == 0 {
        TcpListener::bind(("127.0.0.1", 0))
            .and_then(|listener| listener.local_addr())
            .map(|address| address.port())
            .map_err(|error| format!("Could not reserve a local browser port: {error}"))?
    } else {
        port
    };

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
    let previous_child = {
        let mut active = app.state::<AnalysisState>().active.lock().unwrap();
        active.take().and_then(|mut run| run.child.take())
    };
    if let Some(child) = previous_child {
        let _ = child.kill();
    }

    let command = app
        .shell()
        .sidecar("vibesorter-sidecar")
        .map_err(|error| format!("Could not prepare VibeSorter analysis: {error}"))?
        .args(["index", &folder, "--json", "--progress"]);
    let (mut events, child) = command
        .spawn()
        .map_err(|error| format!("Could not start analysis: {error}"))?;

    let run_id = app.state::<AnalysisState>().next_id.fetch_add(1, Ordering::Relaxed);
    *app.state::<AnalysisState>().active.lock().unwrap() = Some(AnalysisRun {
        id: run_id,
        child: Some(child),
        cancelled: false,
    });

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let state = handle.state::<AnalysisState>();
                    if is_active_analysis_run(&state, run_id) {
                        let _ = handle.emit(
                            "analysis-output",
                            String::from_utf8_lossy(&bytes).to_string(),
                        );
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let state = handle.state::<AnalysisState>();
                    if is_active_analysis_run(&state, run_id) {
                        let _ = handle.emit(
                            "analysis-diagnostic",
                            String::from_utf8_lossy(&bytes).to_string(),
                        );
                    }
                }
                CommandEvent::Terminated(payload) => {
                    let state = handle.state::<AnalysisState>();
                    if let Some(cancelled) = finish_analysis_run(&state, run_id) {
                        if cancelled {
                            let _ = handle.emit("analysis-cancelled", ());
                        } else if payload.code == Some(0) {
                            let _ = handle.emit("analysis-finished", payload.code);
                        } else {
                            let _ = handle.emit("analysis-failed", payload.code);
                        }
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
    let (run_id, child) = {
        let mut active = app.state::<AnalysisState>().active.lock().unwrap();
        if let Some(run) = active.as_mut() {
            run.cancelled = true;
            (Some(run.id), run.child.take())
        } else {
            (None, None)
        }
    };

    if let Some(child) = child {
        if let Err(error) = child.kill() {
            if let Some(run_id) = run_id {
                let mut active = app.state::<AnalysisState>().active.lock().unwrap();
                if let Some(run) = active.as_mut().filter(|run| run.id == run_id) {
                    run.cancelled = false;
                }
            }
            return Err(format!("Could not cancel analysis: {error}"));
        }
    }

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(BackendState(Mutex::new(None)))
        .manage(AnalysisState {
            active: Mutex::new(None),
            next_id: AtomicU64::new(1),
        })
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


#[cfg(test)]
mod analysis_lifecycle_tests {
    use super::*;

    fn test_state(active_id: u64, cancelled: bool) -> AnalysisState {
        AnalysisState {
            active: Mutex::new(Some(AnalysisRun {
                id: active_id,
                child: None,
                cancelled,
            })),
            next_id: AtomicU64::new(active_id + 1),
        }
    }

    #[test]
    fn stale_termination_does_not_clear_a_newer_run() {
        let state = test_state(2, false);

        assert_eq!(finish_analysis_run(&state, 1), None);
        assert!(is_active_analysis_run(&state, 2));
    }

    #[test]
    fn current_termination_clears_only_its_own_run() {
        let state = test_state(7, false);

        assert_eq!(finish_analysis_run(&state, 7), Some(false));
        assert!(!is_active_analysis_run(&state, 7));
    }

    #[test]
    fn cancellation_state_is_attached_to_its_run() {
        let state = test_state(3, true);

        assert_eq!(finish_analysis_run(&state, 3), Some(true));
        assert!(state.active.lock().unwrap().is_none());
    }
}
