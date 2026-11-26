use serde::Serialize;
use std::fs;
use std::io::Write;
use std::path::{Component, Path, PathBuf};
use std::sync::Mutex;
use std::time::UNIX_EPOCH;
use tauri::{Manager, State};
use walkdir::WalkDir;

mod updates;

struct AppState {
    notes_root: Mutex<PathBuf>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct NoteSummary {
    path: String,
    title: String,
    excerpt: String,
    updated: String,
}

#[derive(Serialize)]
struct Library {
    folders: Vec<String>,
    notes: Vec<NoteSummary>,
}

fn is_markdown(path: &Path) -> bool {
    path.extension()
        .and_then(|extension| extension.to_str())
        .is_some_and(|extension| extension.eq_ignore_ascii_case("md"))
}

fn safe_note_path(root: &Path, relative: &str) -> Result<PathBuf, String> {
    let relative_path = Path::new(relative);
    if relative_path.is_absolute()
        || !is_markdown(relative_path)
        || relative_path
            .components()
            .any(|part| !matches!(part, Component::Normal(_)))
    {
        return Err("Недопустимый путь заметки".into());
    }
    Ok(root.join(relative_path))
}

fn checked_existing_note(root: &Path, relative: &str) -> Result<PathBuf, String> {
    let root = root.canonicalize().map_err(|error| error.to_string())?;
    let path = safe_note_path(&root, relative)?
        .canonicalize()
        .map_err(|error| error.to_string())?;
    if !path.starts_with(&root) {
        return Err("Путь заметки выходит за пределы библиотеки".into());
    }
    Ok(path)
}

fn notes_root(state: &State<'_, AppState>) -> Result<PathBuf, String> {
    state
        .notes_root
        .lock()
        .map(|value| value.clone())
        .map_err(|_| "Хранилище недоступно".into())
}

fn valid_entry_name(title: &str) -> Result<&str, String> {
    let title = title.trim();
    let reserved = title
        .split('.')
        .next()
        .unwrap_or_default()
        .trim_end()
        .to_ascii_uppercase();
    if title.is_empty()
        || title.chars().count() > 80
        || title.ends_with('.')
        || title
            .chars()
            .any(|c| c.is_control() || r#"<>:"/\|?*"#.contains(c))
        || matches!(reserved.as_str(), "CON" | "PRN" | "AUX" | "NUL")
        || ["COM", "LPT"].iter().any(|prefix| {
            reserved.strip_prefix(prefix).is_some_and(|suffix| {
                matches!(
                    suffix,
                    "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "¹" | "²" | "³"
                )
            })
        })
    {
        return Err("Введите допустимое имя до 80 символов".into());
    }
    Ok(title)
}

fn checked_folder(root: &Path, folder: &str) -> Result<PathBuf, String> {
    if !folder.is_empty()
        && (cfg!(windows) && folder.contains(['\\', ':'])
            || folder
                .split('/')
                .any(|part| part.is_empty() || part == "." || part == ".."))
    {
        return Err("Недопустимый путь папки".into());
    }
    let root = root.canonicalize().map_err(|error| error.to_string())?;
    let directory = root
        .join(folder)
        .canonicalize()
        .map_err(|error| error.to_string())?;
    if !directory.starts_with(&root) || !directory.is_dir() {
        return Err("Папка недоступна в библиотеке заметок".into());
    }
    Ok(directory)
}

fn library_path(folder: &str, name: &str) -> String {
    if folder.is_empty() {
        name.into()
    } else {
        format!("{folder}/{name}")
    }
}

#[tauri::command]
fn create_folder(
    title: String,
    folder: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let title = valid_entry_name(&title)?;
    if title.eq_ignore_ascii_case(".assets") {
        return Err("Папка .assets предназначена для вложений".into());
    }
    let directory = checked_folder(&notes_root(&state)?, &folder)?;
    fs::create_dir(directory.join(title)).map_err(|error| {
        if error.kind() == std::io::ErrorKind::AlreadyExists {
            "Папка с таким именем уже существует".into()
        } else {
            error.to_string()
        }
    })?;
    Ok(library_path(&folder, title))
}

#[tauri::command]
fn create_note(
    title: String,
    folder: String,
    state: State<'_, AppState>,
) -> Result<NoteSummary, String> {
    let title = valid_entry_name(&title)?;
    let directory = checked_folder(&notes_root(&state)?, &folder)?;
    let filename = format!("{title}.md");
    let content = format!("# {title}\n");
    let mut temporary =
        tempfile::NamedTempFile::new_in(&directory).map_err(|error| error.to_string())?;
    temporary
        .write_all(content.as_bytes())
        .map_err(|error| error.to_string())?;
    temporary
        .persist_noclobber(directory.join(&filename))
        .map_err(|error| {
            if error.error.kind() == std::io::ErrorKind::AlreadyExists {
                "Заметка с таким именем уже существует".into()
            } else {
                error.error.to_string()
            }
        })?;
    Ok(NoteSummary {
        path: library_path(&folder, &filename),
        title: title.into(),
        excerpt: String::new(),
        updated: String::new(),
    })
}

#[tauri::command]
fn list_library(state: State<'_, AppState>) -> Result<Library, String> {
    let root = notes_root(&state)?;
    fs::create_dir_all(&root).map_err(|error| error.to_string())?;
    let mut notes = Vec::new();
    let mut folders = Vec::new();
    for entry in WalkDir::new(&root)
        .follow_links(false)
        .min_depth(1)
        .into_iter()
        .filter_entry(|entry| {
            !entry.file_type().is_dir() || !entry.file_name().eq_ignore_ascii_case(".assets")
        })
        .filter_map(Result::ok)
    {
        let path = entry.path();
        if !entry.file_type().is_dir() && (!entry.file_type().is_file() || !is_markdown(path)) {
            continue;
        }
        let Some(relative) = path
            .strip_prefix(&root)
            .map_err(|error| error.to_string())?
            .to_str()
        else {
            continue;
        };
        let relative = if cfg!(windows) {
            relative.replace('\\', "/")
        } else {
            relative.to_owned()
        };
        if entry.file_type().is_dir() {
            folders.push(relative);
            continue;
        }
        let content = fs::read_to_string(path).map_err(|error| error.to_string())?;
        let title = content
            .lines()
            .find_map(|line| line.strip_prefix("# "))
            .map(str::to_owned)
            .or_else(|| {
                path.file_stem()
                    .and_then(|value| value.to_str())
                    .map(str::to_owned)
            })
            .unwrap_or_else(|| "Без названия".into());
        let excerpt = content
            .lines()
            .filter(|line| !line.trim_start().starts_with('#'))
            .collect::<Vec<_>>()
            .join(" ")
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ")
            .chars()
            .take(120)
            .collect();
        let modified = fs::metadata(path)
            .and_then(|metadata| metadata.modified())
            .ok()
            .and_then(|value| value.duration_since(UNIX_EPOCH).ok())
            .map(|value| value.as_secs())
            .unwrap_or(0);
        notes.push(NoteSummary {
            path: relative,
            title,
            excerpt,
            updated: modified.to_string(),
        });
    }
    notes.sort_by(|left, right| right.updated.cmp(&left.updated));
    Ok(Library { folders, notes })
}

#[tauri::command]
fn read_note(path: String, state: State<'_, AppState>) -> Result<String, String> {
    let root = notes_root(&state)?;
    fs::read_to_string(checked_existing_note(&root, &path)?).map_err(|error| error.to_string())
}

#[tauri::command]
fn save_note(path: String, content: String, state: State<'_, AppState>) -> Result<(), String> {
    if content.len() > 16 * 1024 * 1024 {
        return Err("Заметка превышает ограничение 16 МБ".into());
    }
    let root = notes_root(&state)?;
    let destination = safe_note_path(&root, &path)?;
    if let Some(parent) = destination.parent() {
        let canonical_root = root.canonicalize().map_err(|error| error.to_string())?;
        let mut existing = parent;
        while !existing.exists() {
            existing = existing.parent().ok_or("Недопустимый путь заметки")?;
        }
        let canonical_existing = existing.canonicalize().map_err(|error| error.to_string())?;
        if !canonical_existing.starts_with(&canonical_root) {
            return Err("Путь заметки выходит за пределы библиотеки".into());
        }
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        let canonical_parent = parent.canonicalize().map_err(|error| error.to_string())?;
        if !canonical_parent.starts_with(&canonical_root) {
            return Err("Путь заметки выходит за пределы библиотеки".into());
        }
    }
    let parent = destination.parent().ok_or("Недопустимый путь заметки")?;
    let mut temporary =
        tempfile::NamedTempFile::new_in(parent).map_err(|error| error.to_string())?;
    temporary
        .write_all(content.as_bytes())
        .map_err(|error| error.to_string())?;
    temporary
        .as_file()
        .sync_all()
        .map_err(|error| error.to_string())?;
    temporary
        .persist(destination)
        .map_err(|error| error.error.to_string())?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_log::Builder::new().build())
        .manage(updates::PendingUpdate::default())
        .setup(|app| {
            if app.config().plugins.0.contains_key("updater") {
                app.handle()
                    .plugin(tauri_plugin_updater::Builder::new().build())?;
            }
            let root = app
                .path()
                .document_dir()
                .or_else(|_| app.path().home_dir().map(|home| home.join("Documents")))?
                .join("My Simple AI")
                .join("notes");
            fs::create_dir_all(&root)?;
            app.manage(AppState {
                notes_root: Mutex::new(root),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            list_library,
            create_folder,
            create_note,
            read_note,
            save_note,
            updates::updates_enabled,
            updates::check_update,
            updates::download_update,
            updates::install_update,
        ])
        .run(tauri::generate_context!())
        .expect("Tauri application failed");
}

#[cfg(test)]
mod tests {
    use super::{checked_folder, safe_note_path};
    use std::path::Path;

    #[test]
    fn note_paths_are_relative_markdown_files() {
        let root = Path::new("notes");
        assert!(safe_note_path(root, "folder/note.md").is_ok());
        assert!(safe_note_path(root, "folder/note.MD").is_ok());
        assert!(safe_note_path(root, "../secret.md").is_err());
        assert!(safe_note_path(root, "/absolute.md").is_err());
        assert!(safe_note_path(root, "script.py").is_err());
    }

    #[test]
    fn folder_paths_resolve_existing_directories_inside_the_library() {
        let library = tempfile::tempdir().unwrap();
        let root = library.path().join("notes");
        std::fs::create_dir_all(root.join("Идеи/Проекты")).unwrap();
        assert_eq!(
            checked_folder(&root, "").unwrap(),
            root.canonicalize().unwrap()
        );
        assert!(checked_folder(&root, "Идеи/Проекты").is_ok());
        for folder in ["../", "/tmp", "Идеи/../", "Идеи\\Проекты", "Нет папки"]
        {
            assert!(checked_folder(&root, folder).is_err(), "{folder}");
        }
        #[cfg(unix)]
        {
            std::os::unix::fs::symlink(library.path(), root.join("outside")).unwrap();
            assert!(checked_folder(&root, "outside").is_err());
        }
    }
}
