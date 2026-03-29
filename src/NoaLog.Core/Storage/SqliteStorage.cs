using System.Text.Json;
using Microsoft.Data.Sqlite;
using NoaLog.Core.Dict;
using NoaLog.Core.Models;

namespace NoaLog.Core.Storage;

public class SqliteStorage
{
    private readonly string _connectionString;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public SqliteStorage(string dbPath)
    {
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = dbPath,
            Mode = SqliteOpenMode.ReadWriteCreate,
        }.ToString();
    }

    private SqliteConnection CreateConnection()
    {
        var connection = new SqliteConnection(_connectionString);
        connection.Open();

        using var pragmaCmd = connection.CreateCommand();
        pragmaCmd.CommandText = "PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;";
        pragmaCmd.ExecuteNonQuery();

        return connection;
    }

    // ─── Initialization ───────────────────────────────────────────

    public void Initialize()
    {
        using var connection = CreateConnection();

        using var createCmd = connection.CreateCommand();
        createCmd.CommandText = DbSchema.GetCreateTablesSql();
        createCmd.ExecuteNonQuery();

        using var versionCmd = connection.CreateCommand();
        versionCmd.CommandText = """
            INSERT INTO schema_version (version)
            SELECT @version
            WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = @version);
            """;
        versionCmd.Parameters.AddWithValue("@version", DbSchema.CurrentVersion);
        versionCmd.ExecuteNonQuery();
    }

    // ─── LogEntry CRUD ────────────────────────────────────────────

    public void InsertLogEntry(LogEntry entry)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            INSERT INTO log_entries (
                id, profile_id, timestamp, log_type,
                raw_header, raw_body, speaker_name, speaker_org, body_text,
                edited_speaker_name, edited_speaker_org, edited_body_text,
                capture_path, ocr_engine, ocr_confidence,
                is_deleted, is_duplicate, created_at, updated_at
            ) VALUES (
                @id, @profileId, @timestamp, @logType,
                @rawHeader, @rawBody, @speakerName, @speakerOrg, @bodyText,
                @editedSpeakerName, @editedSpeakerOrg, @editedBodyText,
                @capturePath, @ocrEngine, @ocrConfidence,
                @isDeleted, @isDuplicate, @createdAt, @updatedAt
            );
            """;

        AddLogEntryParameters(cmd, entry);
        cmd.ExecuteNonQuery();
    }

    public List<LogEntry> GetLogEntries(string profileId, bool includeDeleted = false)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();

        cmd.CommandText = includeDeleted
            ? "SELECT * FROM log_entries WHERE profile_id = @profileId ORDER BY timestamp;"
            : "SELECT * FROM log_entries WHERE profile_id = @profileId AND is_deleted = 0 ORDER BY timestamp;";

        cmd.Parameters.AddWithValue("@profileId", profileId);

        using var reader = cmd.ExecuteReader();
        var entries = new List<LogEntry>();
        while (reader.Read())
        {
            entries.Add(ReadLogEntry(reader));
        }
        return entries;
    }

    public LogEntry? GetLogEntryById(string id)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT * FROM log_entries WHERE id = @id;";
        cmd.Parameters.AddWithValue("@id", id);

        using var reader = cmd.ExecuteReader();
        return reader.Read() ? ReadLogEntry(reader) : null;
    }

    public void UpdateLogEntry(LogEntry entry)
    {
        entry.UpdatedAt = DateTime.UtcNow;

        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            UPDATE log_entries SET
                profile_id = @profileId,
                timestamp = @timestamp,
                log_type = @logType,
                raw_header = @rawHeader,
                raw_body = @rawBody,
                speaker_name = @speakerName,
                speaker_org = @speakerOrg,
                body_text = @bodyText,
                edited_speaker_name = @editedSpeakerName,
                edited_speaker_org = @editedSpeakerOrg,
                edited_body_text = @editedBodyText,
                capture_path = @capturePath,
                ocr_engine = @ocrEngine,
                ocr_confidence = @ocrConfidence,
                is_deleted = @isDeleted,
                is_duplicate = @isDuplicate,
                updated_at = @updatedAt
            WHERE id = @id;
            """;

        AddLogEntryParameters(cmd, entry);
        cmd.ExecuteNonQuery();
    }

    public void SoftDeleteLogEntry(string id)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            UPDATE log_entries SET is_deleted = 1, updated_at = @updatedAt WHERE id = @id;
            """;
        cmd.Parameters.AddWithValue("@id", id);
        cmd.Parameters.AddWithValue("@updatedAt", DateTime.UtcNow.ToString("o"));
        cmd.ExecuteNonQuery();
    }

    // ─── Profile CRUD ─────────────────────────────────────────────

    public void InsertProfile(Profile profile)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            INSERT INTO profiles (
                id, name, description, header_rect, body_rect, narrator_rect,
                hotkey, narrator_hotkey, narrator_label, ocr_settings,
                is_active, created_at, updated_at
            ) VALUES (
                @id, @name, @description, @headerRect, @bodyRect, @narratorRect,
                @hotkey, @narratorHotkey, @narratorLabel, @ocrSettings,
                @isActive, @createdAt, @updatedAt
            );
            """;

        AddProfileParameters(cmd, profile);
        cmd.ExecuteNonQuery();
    }

    public List<Profile> GetProfiles(bool includeInactive = false)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();

        cmd.CommandText = includeInactive
            ? "SELECT * FROM profiles ORDER BY name;"
            : "SELECT * FROM profiles WHERE is_active = 1 ORDER BY name;";

        using var reader = cmd.ExecuteReader();
        var profiles = new List<Profile>();
        while (reader.Read())
        {
            profiles.Add(ReadProfile(reader));
        }
        return profiles;
    }

    public Profile? GetProfileById(string id)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT * FROM profiles WHERE id = @id;";
        cmd.Parameters.AddWithValue("@id", id);

        using var reader = cmd.ExecuteReader();
        return reader.Read() ? ReadProfile(reader) : null;
    }

    public void UpdateProfile(Profile profile)
    {
        profile.UpdatedAt = DateTime.UtcNow;

        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            UPDATE profiles SET
                name = @name,
                description = @description,
                header_rect = @headerRect,
                body_rect = @bodyRect,
                narrator_rect = @narratorRect,
                hotkey = @hotkey,
                narrator_hotkey = @narratorHotkey,
                narrator_label = @narratorLabel,
                ocr_settings = @ocrSettings,
                is_active = @isActive,
                updated_at = @updatedAt
            WHERE id = @id;
            """;

        AddProfileParameters(cmd, profile);
        cmd.ExecuteNonQuery();
    }

    public void DeleteProfile(string id)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = "DELETE FROM profiles WHERE id = @id;";
        cmd.Parameters.AddWithValue("@id", id);
        cmd.ExecuteNonQuery();
    }

    // ─── Settings ─────────────────────────────────────────────────

    public string? GetSetting(string key)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT value FROM settings WHERE key = @key;";
        cmd.Parameters.AddWithValue("@key", key);

        var result = cmd.ExecuteScalar();
        return result as string;
    }

    public void SetSetting(string key, string value)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            INSERT INTO settings (key, value, updated_at)
            VALUES (@key, @value, @updatedAt)
            ON CONFLICT(key) DO UPDATE SET value = @value, updated_at = @updatedAt;
            """;
        cmd.Parameters.AddWithValue("@key", key);
        cmd.Parameters.AddWithValue("@value", value);
        cmd.Parameters.AddWithValue("@updatedAt", DateTime.UtcNow.ToString("o"));
        cmd.ExecuteNonQuery();
    }

    // ─── User Dict CRUD ────────────────────────────────────────

    public void InsertUserDictEntry(string gameId, string wrongText, string correctText, string category, string source)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            INSERT INTO user_dict_entries (game_id, wrong_text, correct_text, category, source, created_at)
            VALUES (@gameId, @wrongText, @correctText, @category, @source, @createdAt);
            """;
        cmd.Parameters.AddWithValue("@gameId", gameId);
        cmd.Parameters.AddWithValue("@wrongText", wrongText);
        cmd.Parameters.AddWithValue("@correctText", correctText);
        cmd.Parameters.AddWithValue("@category", category);
        cmd.Parameters.AddWithValue("@source", source);
        cmd.Parameters.AddWithValue("@createdAt", DateTime.UtcNow.ToString("o"));
        cmd.ExecuteNonQuery();
    }

    public List<UserDictEntry> GetUserDictEntries(string? gameId)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();

        if (gameId is null)
        {
            cmd.CommandText = "SELECT id, game_id, wrong_text, correct_text, category, source FROM user_dict_entries ORDER BY game_id, id;";
        }
        else
        {
            cmd.CommandText = "SELECT id, game_id, wrong_text, correct_text, category, source FROM user_dict_entries WHERE game_id = @gameId ORDER BY id;";
            cmd.Parameters.AddWithValue("@gameId", gameId);
        }

        using var reader = cmd.ExecuteReader();
        var entries = new List<UserDictEntry>();
        while (reader.Read())
        {
            entries.Add(new UserDictEntry(
                Id: reader.GetInt32(reader.GetOrdinal("id")),
                GameId: reader.GetString(reader.GetOrdinal("game_id")),
                WrongText: reader.GetString(reader.GetOrdinal("wrong_text")),
                CorrectText: reader.GetString(reader.GetOrdinal("correct_text")),
                Category: reader.GetString(reader.GetOrdinal("category")),
                Source: reader.GetString(reader.GetOrdinal("source"))
            ));
        }
        return entries;
    }

    public void DeleteUserDictEntry(int id)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = "DELETE FROM user_dict_entries WHERE id = @id;";
        cmd.Parameters.AddWithValue("@id", id);
        cmd.ExecuteNonQuery();
    }

    // ─── CorrectionRecord CRUD ─────────────────────────────────────

    public void InsertCorrectionRecord(CorrectionRecord record)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = """
            INSERT INTO correction_log (
                log_entry_id, field_name, original_value, corrected_value, ocr_engine, game_id
            ) VALUES (
                @logEntryId, @fieldName, @originalValue, @correctedValue, @ocrEngine, @gameId
            );
            """;
        cmd.Parameters.AddWithValue("@logEntryId", record.LogEntryId);
        cmd.Parameters.AddWithValue("@fieldName", record.FieldName);
        cmd.Parameters.AddWithValue("@originalValue", record.OriginalValue);
        cmd.Parameters.AddWithValue("@correctedValue", record.CorrectedValue);
        cmd.Parameters.AddWithValue("@ocrEngine", record.OcrEngine);
        cmd.Parameters.AddWithValue("@gameId", (object?)record.GameId ?? DBNull.Value);
        cmd.ExecuteNonQuery();
    }

    public List<CorrectionRecord> GetUnsentCorrectionRecords()
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT * FROM correction_log WHERE is_sent = 0;";

        using var reader = cmd.ExecuteReader();
        var records = new List<CorrectionRecord>();
        while (reader.Read())
        {
            records.Add(new CorrectionRecord
            {
                Id = reader.GetInt32(reader.GetOrdinal("id")),
                LogEntryId = reader.GetString(reader.GetOrdinal("log_entry_id")),
                FieldName = reader.GetString(reader.GetOrdinal("field_name")),
                OriginalValue = reader.GetString(reader.GetOrdinal("original_value")),
                CorrectedValue = reader.GetString(reader.GetOrdinal("corrected_value")),
                OcrEngine = reader.GetString(reader.GetOrdinal("ocr_engine")),
                GameId = GetNullableString(reader, "game_id"),
                CreatedAt = DateTime.Parse(reader.GetString(reader.GetOrdinal("created_at"))),
                IsSent = reader.GetInt64(reader.GetOrdinal("is_sent")) != 0,
            });
        }
        return records;
    }

    public void MarkCorrectionRecordsSent(IEnumerable<int> ids)
    {
        using var connection = CreateConnection();
        using var cmd = connection.CreateCommand();

        var idList = ids.ToList();
        if (idList.Count == 0) return;

        var paramNames = new List<string>();
        for (var i = 0; i < idList.Count; i++)
        {
            var paramName = $"@id{i}";
            paramNames.Add(paramName);
            cmd.Parameters.AddWithValue(paramName, idList[i]);
        }

        cmd.CommandText = $"UPDATE correction_log SET is_sent = 1 WHERE id IN ({string.Join(", ", paramNames)});";
        cmd.ExecuteNonQuery();
    }

    // ─── Helpers ──────────────────────────────────────────────────

    private static void AddLogEntryParameters(SqliteCommand cmd, LogEntry entry)
    {
        cmd.Parameters.AddWithValue("@id", entry.Id);
        cmd.Parameters.AddWithValue("@profileId", entry.ProfileId);
        cmd.Parameters.AddWithValue("@timestamp", entry.Timestamp.ToString("o"));
        cmd.Parameters.AddWithValue("@logType", entry.LogType.ToString().ToLowerInvariant());
        cmd.Parameters.AddWithValue("@rawHeader", entry.RawHeader);
        cmd.Parameters.AddWithValue("@rawBody", entry.RawBody);
        cmd.Parameters.AddWithValue("@speakerName", entry.SpeakerName);
        cmd.Parameters.AddWithValue("@speakerOrg", entry.SpeakerOrg);
        cmd.Parameters.AddWithValue("@bodyText", entry.BodyText);
        cmd.Parameters.AddWithValue("@editedSpeakerName", (object?)entry.EditedSpeakerName ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@editedSpeakerOrg", (object?)entry.EditedSpeakerOrg ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@editedBodyText", (object?)entry.EditedBodyText ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@capturePath", (object?)entry.CapturePath ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@ocrEngine", entry.OcrEngine);
        cmd.Parameters.AddWithValue("@ocrConfidence", entry.OcrConfidence);
        cmd.Parameters.AddWithValue("@isDeleted", entry.IsDeleted ? 1 : 0);
        cmd.Parameters.AddWithValue("@isDuplicate", entry.IsDuplicate ? 1 : 0);
        cmd.Parameters.AddWithValue("@createdAt", entry.CreatedAt.ToString("o"));
        cmd.Parameters.AddWithValue("@updatedAt", entry.UpdatedAt.ToString("o"));
    }

    private static void AddProfileParameters(SqliteCommand cmd, Profile profile)
    {
        cmd.Parameters.AddWithValue("@id", profile.Id);
        cmd.Parameters.AddWithValue("@name", profile.Name);
        cmd.Parameters.AddWithValue("@description", profile.Description);
        cmd.Parameters.AddWithValue("@headerRect", SerializeJson(profile.HeaderRect));
        cmd.Parameters.AddWithValue("@bodyRect", SerializeJson(profile.BodyRect));
        cmd.Parameters.AddWithValue("@narratorRect", SerializeJson(profile.NarratorRect));
        cmd.Parameters.AddWithValue("@hotkey", SerializeJson(profile.Hotkey));
        cmd.Parameters.AddWithValue("@narratorHotkey", SerializeJson(profile.NarratorHotkey));
        cmd.Parameters.AddWithValue("@narratorLabel", profile.NarratorLabel);
        cmd.Parameters.AddWithValue("@ocrSettings",
            profile.OcrSettings != null
                ? JsonSerializer.Serialize(profile.OcrSettings, JsonOptions)
                : "{}");
        cmd.Parameters.AddWithValue("@isActive", profile.IsActive ? 1 : 0);
        cmd.Parameters.AddWithValue("@createdAt", profile.CreatedAt.ToString("o"));
        cmd.Parameters.AddWithValue("@updatedAt", profile.UpdatedAt.ToString("o"));
    }

    private static LogEntry ReadLogEntry(SqliteDataReader reader)
    {
        return new LogEntry
        {
            Id = reader.GetString(reader.GetOrdinal("id")),
            ProfileId = reader.GetString(reader.GetOrdinal("profile_id")),
            Timestamp = DateTime.Parse(reader.GetString(reader.GetOrdinal("timestamp"))),
            LogType = Enum.Parse<LogType>(reader.GetString(reader.GetOrdinal("log_type")), ignoreCase: true),
            RawHeader = reader.GetString(reader.GetOrdinal("raw_header")),
            RawBody = reader.GetString(reader.GetOrdinal("raw_body")),
            SpeakerName = reader.GetString(reader.GetOrdinal("speaker_name")),
            SpeakerOrg = reader.GetString(reader.GetOrdinal("speaker_org")),
            BodyText = reader.GetString(reader.GetOrdinal("body_text")),
            EditedSpeakerName = GetNullableString(reader, "edited_speaker_name"),
            EditedSpeakerOrg = GetNullableString(reader, "edited_speaker_org"),
            EditedBodyText = GetNullableString(reader, "edited_body_text"),
            CapturePath = GetNullableString(reader, "capture_path"),
            OcrEngine = reader.GetString(reader.GetOrdinal("ocr_engine")),
            OcrConfidence = reader.GetDouble(reader.GetOrdinal("ocr_confidence")),
            IsDeleted = reader.GetInt64(reader.GetOrdinal("is_deleted")) != 0,
            IsDuplicate = reader.GetInt64(reader.GetOrdinal("is_duplicate")) != 0,
            CreatedAt = DateTime.Parse(reader.GetString(reader.GetOrdinal("created_at"))),
            UpdatedAt = DateTime.Parse(reader.GetString(reader.GetOrdinal("updated_at"))),
        };
    }

    private static Profile ReadProfile(SqliteDataReader reader)
    {
        return new Profile
        {
            Id = reader.GetString(reader.GetOrdinal("id")),
            Name = reader.GetString(reader.GetOrdinal("name")),
            Description = reader.GetString(reader.GetOrdinal("description")),
            HeaderRect = DeserializeJson<Rect>(GetNullableString(reader, "header_rect")),
            BodyRect = DeserializeJson<Rect>(GetNullableString(reader, "body_rect")),
            NarratorRect = DeserializeJson<Rect>(GetNullableString(reader, "narrator_rect")),
            Hotkey = DeserializeJson<Models.Hotkey>(GetNullableString(reader, "hotkey")),
            NarratorHotkey = DeserializeJson<Models.Hotkey>(GetNullableString(reader, "narrator_hotkey")),
            NarratorLabel = reader.GetString(reader.GetOrdinal("narrator_label")),
            OcrSettings = DeserializeJson<Dictionary<string, object>>(
                GetNullableString(reader, "ocr_settings")),
            IsActive = reader.GetInt64(reader.GetOrdinal("is_active")) != 0,
            CreatedAt = DateTime.Parse(reader.GetString(reader.GetOrdinal("created_at"))),
            UpdatedAt = DateTime.Parse(reader.GetString(reader.GetOrdinal("updated_at"))),
        };
    }

    private static string? GetNullableString(SqliteDataReader reader, string columnName)
    {
        var ordinal = reader.GetOrdinal(columnName);
        return reader.IsDBNull(ordinal) ? null : reader.GetString(ordinal);
    }

    private static object SerializeJson<T>(T? value) where T : class
    {
        if (value is null) return DBNull.Value;
        return JsonSerializer.Serialize(value, JsonOptions);
    }

    private static T? DeserializeJson<T>(string? json) where T : class
    {
        if (string.IsNullOrEmpty(json)) return null;
        return JsonSerializer.Deserialize<T>(json, JsonOptions);
    }
}
