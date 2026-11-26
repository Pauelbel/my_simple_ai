use std::time::Duration;

#[cfg(target_os = "linux")]
use tauri::Manager;
use tauri::{async_runtime::Mutex, AppHandle, State};
use tauri_plugin_updater::{Update, UpdaterExt};

#[derive(Default)]
pub struct PendingUpdate(Mutex<Option<UpdatePackage>>);

struct UpdatePackage {
    update: Update,
    bytes: Option<Vec<u8>>,
}

#[tauri::command]
pub fn updates_enabled(app: AppHandle) -> bool {
    if cfg!(debug_assertions) || !app.config().plugins.0.contains_key("updater") {
        return false;
    }
    #[cfg(target_os = "linux")]
    {
        app.env().appimage.is_some()
    }
    #[cfg(not(target_os = "linux"))]
    {
        cfg!(target_os = "windows")
    }
}

#[tauri::command]
pub async fn check_update(
    app: AppHandle,
    pending: State<'_, PendingUpdate>,
) -> Result<Option<String>, String> {
    if !updates_enabled(app.clone()) {
        return Ok(None);
    }
    let mut pending = pending.0.lock().await;
    if let Some(package) = pending.as_ref().filter(|package| package.bytes.is_some()) {
        return Ok(Some(package.update.version.clone()));
    }
    let update = app
        .updater_builder()
        .timeout(Duration::from_secs(20))
        .build()
        .map_err(|error| error.to_string())?
        .check()
        .await
        .map_err(|error| error.to_string())?;
    let version = update.as_ref().map(|update| update.version.clone());
    *pending = update.map(|update| UpdatePackage {
        update,
        bytes: None,
    });
    Ok(version)
}

#[tauri::command]
pub async fn download_update(
    app: AppHandle,
    pending: State<'_, PendingUpdate>,
) -> Result<(), String> {
    if !updates_enabled(app) {
        return Err("Обновления недоступны для этой сборки".into());
    }
    let mut pending = pending.0.lock().await;
    let package = pending.as_mut().ok_or("Сначала проверьте обновления")?;
    if package.bytes.is_none() {
        let bytes = package
            .update
            .download(|_, _| {}, || {})
            .await
            .map_err(|error| error.to_string())?;
        package.bytes = Some(bytes);
    }
    Ok(())
}

#[tauri::command]
pub async fn install_update(
    app: AppHandle,
    pending: State<'_, PendingUpdate>,
) -> Result<(), String> {
    if !updates_enabled(app.clone()) {
        return Err("Обновления недоступны для этой сборки".into());
    }
    let mut pending = pending.0.lock().await;
    let package = pending.as_ref().ok_or("Сначала скачайте обновление")?;
    let bytes = package
        .bytes
        .as_deref()
        .ok_or("Сначала скачайте обновление")?;
    package
        .update
        .install(bytes)
        .map_err(|error| error.to_string())?;
    *pending = None;
    #[cfg(target_os = "linux")]
    app.request_restart();
    Ok(())
}
