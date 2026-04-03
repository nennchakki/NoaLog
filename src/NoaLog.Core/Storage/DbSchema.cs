namespace NoaLog.Core.Storage;

public static class DbSchema
{
    public const int CurrentVersion = 1;

    public static string GetCreateTablesSql() => """
        CREATE TABLE IF NOT EXISTS profiles (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            description     TEXT DEFAULT '',
            header_rect     TEXT,
            body_rect       TEXT,
            narrator_rect   TEXT,
            hotkey          TEXT,
            narrator_hotkey TEXT,
            narrator_label  TEXT DEFAULT '語り部',
            ocr_settings    TEXT DEFAULT '{}',
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS log_entries (
            id              TEXT PRIMARY KEY,
            profile_id      TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            log_type        TEXT NOT NULL DEFAULT 'dialogue',
            raw_header      TEXT NOT NULL DEFAULT '',
            raw_body        TEXT NOT NULL DEFAULT '',
            speaker_name    TEXT NOT NULL DEFAULT '',
            speaker_org     TEXT NOT NULL DEFAULT '',
            body_text       TEXT NOT NULL DEFAULT '',
            edited_speaker_name TEXT,
            edited_speaker_org  TEXT,
            edited_body_text    TEXT,
            capture_path    TEXT,
            ocr_engine      TEXT NOT NULL DEFAULT 'manga_ocr_onnx',
            ocr_confidence  REAL DEFAULT 0.0,
            is_deleted      INTEGER NOT NULL DEFAULT 0,
            is_duplicate    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_dict_entries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id      TEXT NOT NULL,
            wrong_text   TEXT NOT NULL,
            correct_text TEXT NOT NULL,
            category     TEXT DEFAULT 'proper_noun',
            source       TEXT DEFAULT 'user',
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version    INTEGER NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_log_entries_profile_id ON log_entries(profile_id);
        CREATE INDEX IF NOT EXISTS idx_log_entries_timestamp ON log_entries(timestamp);
        """;
}
