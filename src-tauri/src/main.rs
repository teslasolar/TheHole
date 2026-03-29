#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod blocklists;
mod reader;
mod router;
mod slop_shield;
mod storage;

use tauri::Manager;

use blocklists::BlockList;
use slop_shield::SlopShield;
use storage::Database;

/// Tauri command: route an address-bar input string.
#[tauri::command]
fn navigate(input: String) -> router::RouterAction {
    router::parse_input(&input)
}

/// Tauri command: get the slop score for a page (convenience wrapper).
#[tauri::command]
fn get_slop_score(html: String, url: String, shield: tauri::State<'_, SlopShield>) -> f64 {
    shield.analyze_page(&html, &url).slop_score
}

/// Tauri command: toggle reader mode and return extracted article.
#[tauri::command]
fn toggle_reader(html: String) -> reader::Article {
    reader::extract_article(&html)
}

/// Tauri command: retrieve all settings as a JSON object.
#[tauri::command]
fn get_settings(db: tauri::State<'_, Database>) -> Result<serde_json::Value, String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT key, value FROM settings")
        .map_err(|e| e.to_string())?;
    let mut map = serde_json::Map::new();
    let rows = stmt
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(|e| e.to_string())?;
    for row in rows {
        let (k, v) = row.map_err(|e| e.to_string())?;
        map.insert(k, serde_json::Value::String(v));
    }
    Ok(serde_json::Value::Object(map))
}

/// Tauri command: update a single setting.
#[tauri::command]
fn update_settings(key: String, value: String, db: tauri::State<'_, Database>) -> Result<(), String> {
    storage::set_setting(key, value, db)
}

/// Tauri command: check if a URL is blocked by the ad/tracker blocklist.
#[tauri::command]
fn is_url_blocked(url: String, bl: tauri::State<'_, BlockList>) -> bool {
    bl.is_blocked(&url)
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Resolve app data directory for the database
            let data_dir = app
                .path()
                .app_data_dir()
                .expect("failed to resolve app data dir");

            // Initialise shared state
            let db = Database::open(data_dir).expect("failed to open database");
            let shield = SlopShield::new();
            let blocklist = BlockList::load_default();

            app.manage(db);
            app.manage(shield);
            app.manage(blocklist);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Router
            navigate,
            // Slop Shield
            slop_shield::get_slop_report,
            get_slop_score,
            // Reader
            reader::get_reader_content,
            toggle_reader,
            // Storage - bookmarks
            storage::add_bookmark,
            storage::remove_bookmark,
            storage::list_bookmarks,
            // Storage - history
            storage::add_history,
            storage::list_history,
            storage::clear_history,
            // Storage - settings
            storage::get_setting,
            storage::set_setting,
            get_settings,
            update_settings,
            // Blocklist
            is_url_blocked,
        ])
        .run(tauri::generate_context!())
        .expect("error while running THE HOLE BROWSER");
}
