use rusqlite::{params, Connection};
use std::path::PathBuf;
use std::sync::Mutex;

/// Thread-safe wrapper around the SQLite connection.
pub struct Database {
    pub conn: Mutex<Connection>,
}

impl Database {
    /// Open (or create) the database and run migrations.
    pub fn open(app_data_dir: PathBuf) -> Result<Self, String> {
        std::fs::create_dir_all(&app_data_dir).map_err(|e| e.to_string())?;
        let db_path = app_data_dir.join("hole.db");
        let conn = Connection::open(&db_path).map_err(|e| e.to_string())?;
        let db = Self {
            conn: Mutex::new(conn),
        };
        db.init_tables()?;
        Ok(db)
    }

    fn init_tables(&self) -> Result<(), String> {
        let conn = self.conn.lock().map_err(|e| e.to_string())?;
        conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS bookmarks (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                url     TEXT NOT NULL,
                title   TEXT NOT NULL DEFAULT '',
                date_added TEXT NOT NULL DEFAULT (datetime('now')),
                tags    TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT NOT NULL,
                title      TEXT NOT NULL DEFAULT '',
                visited_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS slop_overrides (
                domain     TEXT PRIMARY KEY,
                user_score REAL NOT NULL DEFAULT 0.0,
                reason     TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            ",
        )
        .map_err(|e| e.to_string())?;
        Ok(())
    }
}

// ── Serializable structs returned to the frontend ──

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Bookmark {
    pub id: i64,
    pub url: String,
    pub title: String,
    pub date_added: String,
    pub tags: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct HistoryEntry {
    pub id: i64,
    pub url: String,
    pub title: String,
    pub visited_at: String,
}

// ── Tauri commands ──

#[tauri::command]
pub fn add_bookmark(
    url: String,
    title: String,
    tags: String,
    db: tauri::State<'_, Database>,
) -> Result<i64, String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO bookmarks (url, title, tags) VALUES (?1, ?2, ?3)",
        params![url, title, tags],
    )
    .map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn remove_bookmark(id: i64, db: tauri::State<'_, Database>) -> Result<(), String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM bookmarks WHERE id = ?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn list_bookmarks(db: tauri::State<'_, Database>) -> Result<Vec<Bookmark>, String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, url, title, date_added, tags FROM bookmarks ORDER BY date_added DESC")
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map([], |row| {
            Ok(Bookmark {
                id: row.get(0)?,
                url: row.get(1)?,
                title: row.get(2)?,
                date_added: row.get(3)?,
                tags: row.get(4)?,
            })
        })
        .map_err(|e| e.to_string())?;
    let mut bookmarks = Vec::new();
    for row in rows {
        bookmarks.push(row.map_err(|e| e.to_string())?);
    }
    Ok(bookmarks)
}

#[tauri::command]
pub fn add_history(
    url: String,
    title: String,
    db: tauri::State<'_, Database>,
) -> Result<i64, String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO history (url, title) VALUES (?1, ?2)",
        params![url, title],
    )
    .map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn list_history(
    limit: Option<u32>,
    db: tauri::State<'_, Database>,
) -> Result<Vec<HistoryEntry>, String> {
    let limit = limit.unwrap_or(100);
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, url, title, visited_at FROM history ORDER BY visited_at DESC LIMIT ?1")
        .map_err(|e| e.to_string())?;
    let rows = stmt
        .query_map(params![limit], |row| {
            Ok(HistoryEntry {
                id: row.get(0)?,
                url: row.get(1)?,
                title: row.get(2)?,
                visited_at: row.get(3)?,
            })
        })
        .map_err(|e| e.to_string())?;
    let mut entries = Vec::new();
    for row in rows {
        entries.push(row.map_err(|e| e.to_string())?);
    }
    Ok(entries)
}

#[tauri::command]
pub fn clear_history(db: tauri::State<'_, Database>) -> Result<(), String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM history", [])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn get_setting(key: String, db: tauri::State<'_, Database>) -> Result<Option<String>, String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT value FROM settings WHERE key = ?1")
        .map_err(|e| e.to_string())?;
    let mut rows = stmt
        .query_map(params![key], |row| row.get::<_, String>(0))
        .map_err(|e| e.to_string())?;
    match rows.next() {
        Some(Ok(val)) => Ok(Some(val)),
        Some(Err(e)) => Err(e.to_string()),
        None => Ok(None),
    }
}

#[tauri::command]
pub fn set_setting(key: String, value: String, db: tauri::State<'_, Database>) -> Result<(), String> {
    let conn = db.conn.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?1, ?2)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        params![key, value],
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_db() -> Database {
        let conn = Connection::open_in_memory().unwrap();
        let db = Database { conn: Mutex::new(conn) };
        db.init_tables().unwrap();
        db
    }

    #[test]
    fn test_init_tables() {
        let db = test_db();
        let conn = db.conn.lock().unwrap();
        // Verify all four tables exist by querying sqlite_master
        let count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('bookmarks','history','slop_overrides','settings')",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(count, 4);
    }

    #[test]
    fn test_bookmark_add_list() {
        let db = test_db();
        {
            let conn = db.conn.lock().unwrap();
            conn.execute("INSERT INTO bookmarks (url, title, tags) VALUES (?1, ?2, ?3)", params!["https://a.com", "A", "tag1"]).unwrap();
            conn.execute("INSERT INTO bookmarks (url, title, tags) VALUES (?1, ?2, ?3)", params!["https://b.com", "B", ""]).unwrap();
        }
        let conn = db.conn.lock().unwrap();
        let count: i64 = conn.query_row("SELECT COUNT(*) FROM bookmarks", [], |r| r.get(0)).unwrap();
        assert_eq!(count, 2);
    }

    #[test]
    fn test_bookmark_remove() {
        let db = test_db();
        let id: i64;
        {
            let conn = db.conn.lock().unwrap();
            conn.execute("INSERT INTO bookmarks (url, title) VALUES (?1, ?2)", params!["https://x.com", "X"]).unwrap();
            id = conn.last_insert_rowid();
        }
        {
            let conn = db.conn.lock().unwrap();
            conn.execute("DELETE FROM bookmarks WHERE id = ?1", params![id]).unwrap();
        }
        let conn = db.conn.lock().unwrap();
        let count: i64 = conn.query_row("SELECT COUNT(*) FROM bookmarks", [], |r| r.get(0)).unwrap();
        assert_eq!(count, 0);
    }

    #[test]
    fn test_history_add_list_clear() {
        let db = test_db();
        {
            let conn = db.conn.lock().unwrap();
            conn.execute("INSERT INTO history (url, title) VALUES (?1, ?2)", params!["https://h.com", "H"]).unwrap();
        }
        {
            let conn = db.conn.lock().unwrap();
            let count: i64 = conn.query_row("SELECT COUNT(*) FROM history", [], |r| r.get(0)).unwrap();
            assert_eq!(count, 1);
        }
        {
            let conn = db.conn.lock().unwrap();
            conn.execute("DELETE FROM history", []).unwrap();
        }
        let conn = db.conn.lock().unwrap();
        let count: i64 = conn.query_row("SELECT COUNT(*) FROM history", [], |r| r.get(0)).unwrap();
        assert_eq!(count, 0);
    }

    #[test]
    fn test_settings_set_get_upsert() {
        let db = test_db();
        {
            let conn = db.conn.lock().unwrap();
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?1, ?2) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                params!["theme", "dark"],
            ).unwrap();
        }
        {
            let conn = db.conn.lock().unwrap();
            let val: String = conn.query_row("SELECT value FROM settings WHERE key = ?1", params!["theme"], |r| r.get(0)).unwrap();
            assert_eq!(val, "dark");
        }
        // upsert
        {
            let conn = db.conn.lock().unwrap();
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?1, ?2) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                params!["theme", "light"],
            ).unwrap();
        }
        let conn = db.conn.lock().unwrap();
        let val: String = conn.query_row("SELECT value FROM settings WHERE key = ?1", params!["theme"], |r| r.get(0)).unwrap();
        assert_eq!(val, "light");
    }
}
