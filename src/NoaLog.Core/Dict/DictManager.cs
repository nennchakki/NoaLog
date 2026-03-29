using System.Text.Json;
using NoaLog.Core.Storage;

namespace NoaLog.Core.Dict;

/// <summary>
/// 辞書ライフサイクル管理。
/// ビルトイン辞書 + ユーザー辞書をロードし、検索APIを提供。
/// </summary>
public class DictManager
{
    private readonly string _builtinDictDir;
    private readonly SqliteStorage _storage;

    // gameId -> list of entries (builtin)
    private readonly Dictionary<string, List<DictFileEntry>> _builtinEntries = new();

    // gameId -> list of user entries
    private readonly Dictionary<string, List<UserDictEntry>> _userEntries = new();

    // gameId -> (wrong -> correct) for O(1) exact match
    private readonly Dictionary<string, Dictionary<string, string>> _exactMatchLookup = new();

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = true,
    };

    public DictManager(string builtinDictDir, SqliteStorage storage)
    {
        _builtinDictDir = builtinDictDir;
        _storage = storage;
    }

    /// <summary>Load all dictionaries (builtin JSON + user DB entries)</summary>
    public void LoadAll()
    {
        _builtinEntries.Clear();
        _userEntries.Clear();
        _exactMatchLookup.Clear();

        LoadBuiltinDicts();
        LoadUserDicts();
        RebuildExactMatchLookup();
    }

    /// <summary>Load builtin dictionaries from JSON files in the directory</summary>
    public void LoadBuiltinDicts()
    {
        if (!Directory.Exists(_builtinDictDir))
            return;

        foreach (var filePath in Directory.GetFiles(_builtinDictDir, "*.json"))
        {
            var json = File.ReadAllText(filePath);
            var dictFile = JsonSerializer.Deserialize<DictFile>(json, JsonOptions);
            if (dictFile is null)
                continue;

            var gameId = dictFile.Meta.GameId;
            if (!_builtinEntries.TryGetValue(gameId, out var list))
            {
                list = new List<DictFileEntry>();
                _builtinEntries[gameId] = list;
            }

            list.AddRange(dictFile.Entries);
        }
    }

    /// <summary>Load user dictionary entries from SQLite</summary>
    public void LoadUserDicts()
    {
        _userEntries.Clear();

        var entries = _storage.GetUserDictEntries(null);
        foreach (var entry in entries)
        {
            if (!_userEntries.TryGetValue(entry.GameId, out var list))
            {
                list = new List<UserDictEntry>();
                _userEntries[entry.GameId] = list;
            }

            list.Add(entry);
        }
    }

    /// <summary>Get all entries for a specific game (builtin + user combined)</summary>
    public IReadOnlyList<DictFileEntry> GetEntries(string? gameId)
    {
        var result = new List<DictFileEntry>();

        // Always include _common entries
        if (_builtinEntries.TryGetValue("_common", out var commonEntries))
            result.AddRange(commonEntries);

        // Add game-specific builtin entries
        if (gameId is not null && gameId != "_common" &&
            _builtinEntries.TryGetValue(gameId, out var gameEntries))
        {
            result.AddRange(gameEntries);
        }

        // Add user entries converted to DictFileEntry
        if (_userEntries.TryGetValue("_common", out var commonUserEntries))
        {
            result.AddRange(commonUserEntries.Select(ToFileEntry));
        }

        if (gameId is not null && gameId != "_common" &&
            _userEntries.TryGetValue(gameId, out var gameUserEntries))
        {
            result.AddRange(gameUserEntries.Select(ToFileEntry));
        }

        return result;
    }

    /// <summary>Find exact match: returns corrected text or null</summary>
    public string? FindExactMatch(string text, string? gameId)
    {
        // Check game-specific lookup first
        if (gameId is not null &&
            _exactMatchLookup.TryGetValue(gameId, out var gameLookup) &&
            gameLookup.TryGetValue(text, out var gameResult))
        {
            return gameResult;
        }

        // Fall back to _common
        if (_exactMatchLookup.TryGetValue("_common", out var commonLookup) &&
            commonLookup.TryGetValue(text, out var commonResult))
        {
            return commonResult;
        }

        return null;
    }

    /// <summary>Add user dictionary entry (persists to DB)</summary>
    public void AddUserEntry(string gameId, string wrongText, string correctText, string category = "proper_noun")
    {
        _storage.InsertUserDictEntry(gameId, wrongText, correctText, category, "user");

        // Reload user dicts to pick up the new entry with its DB-assigned ID
        LoadUserDicts();
        RebuildExactMatchLookup();
    }

    /// <summary>Remove user dictionary entry</summary>
    public void RemoveUserEntry(int entryId)
    {
        _storage.DeleteUserDictEntry(entryId);

        LoadUserDicts();
        RebuildExactMatchLookup();
    }

    /// <summary>Get all user entries for a game</summary>
    public IReadOnlyList<UserDictEntry> GetUserEntries(string? gameId)
    {
        if (gameId is null)
        {
            return _userEntries.Values.SelectMany(x => x).ToList();
        }

        return _userEntries.TryGetValue(gameId, out var entries)
            ? entries
            : Array.Empty<UserDictEntry>();
    }

    private void RebuildExactMatchLookup()
    {
        _exactMatchLookup.Clear();

        // Add builtin entries
        foreach (var (gameId, entries) in _builtinEntries)
        {
            var lookup = GetOrCreateLookup(gameId);
            foreach (var entry in entries.Where(e => e.MatchType == "exact"))
            {
                lookup[entry.Wrong] = entry.Correct;
            }
        }

        // Add user entries (user entries override builtin)
        foreach (var (gameId, entries) in _userEntries)
        {
            var lookup = GetOrCreateLookup(gameId);
            foreach (var entry in entries)
            {
                lookup[entry.WrongText] = entry.CorrectText;
            }
        }
    }

    private Dictionary<string, string> GetOrCreateLookup(string gameId)
    {
        if (!_exactMatchLookup.TryGetValue(gameId, out var lookup))
        {
            lookup = new Dictionary<string, string>();
            _exactMatchLookup[gameId] = lookup;
        }
        return lookup;
    }

    private static DictFileEntry ToFileEntry(UserDictEntry entry) => new()
    {
        Wrong = entry.WrongText,
        Correct = entry.CorrectText,
        Category = entry.Category,
        MatchType = "exact",
    };
}

/// <summary>User dictionary entry from DB</summary>
public record UserDictEntry(int Id, string GameId, string WrongText, string CorrectText, string Category, string Source);
