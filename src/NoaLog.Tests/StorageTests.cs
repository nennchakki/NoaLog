using NoaLog.Core.Models;
using NoaLog.Core.Storage;

namespace NoaLog.Tests;

public class StorageTests : IDisposable
{
    private readonly string _dbPath;
    private readonly SqliteStorage _storage;

    public StorageTests()
    {
        _dbPath = Path.Combine(Path.GetTempPath(), $"noalog_test_{Guid.NewGuid()}.db");
        _storage = new SqliteStorage(_dbPath);
        _storage.Initialize();
    }

    public void Dispose()
    {
        if (File.Exists(_dbPath))
            File.Delete(_dbPath);
    }

    [Fact]
    public void Initialize_CreatesDatabase()
    {
        Assert.True(File.Exists(_dbPath));
    }

    [Fact]
    public void Profile_InsertAndGet()
    {
        var profile = new Profile
        {
            Name = "テストプロファイル",
            Description = "ブルーアーカイブ用",
            TextAreaRect = new Rect(100, 200, 300, 250),
        };

        _storage.InsertProfile(profile);
        var loaded = _storage.GetProfileById(profile.Id);

        Assert.NotNull(loaded);
        Assert.Equal("テストプロファイル", loaded!.Name);
        Assert.Equal("ブルーアーカイブ用", loaded.Description);
        Assert.NotNull(loaded.TextAreaRect);
        Assert.Equal(100, loaded.TextAreaRect!.X);
        Assert.Equal(200, loaded.TextAreaRect.Y);
        Assert.Equal(300, loaded.TextAreaRect.Width);
        Assert.Equal(250, loaded.TextAreaRect.Height);
    }

    [Fact]
    public void Profile_GetAll()
    {
        _storage.InsertProfile(new Profile { Name = "Profile A" });
        _storage.InsertProfile(new Profile { Name = "Profile B" });

        var profiles = _storage.GetProfiles();
        Assert.Equal(2, profiles.Count);
    }

    [Fact]
    public void LogEntry_InsertAndGet()
    {
        var profile = new Profile { Name = "Test" };
        _storage.InsertProfile(profile);

        var entry = new LogEntry
        {
            ProfileId = profile.Id,
            SpeakerName = "ミカ",
            SpeakerOrg = "ゲヘナ",
            BodyText = "先生、こんにちは！",
            OcrEngine = "manga_ocr_onnx",
        };

        _storage.InsertLogEntry(entry);
        var loaded = _storage.GetLogEntryById(entry.Id);

        Assert.NotNull(loaded);
        Assert.Equal("ミカ", loaded!.SpeakerName);
        Assert.Equal("ゲヘナ", loaded.SpeakerOrg);
        Assert.Equal("先生、こんにちは！", loaded.BodyText);
    }

    [Fact]
    public void LogEntry_SoftDelete()
    {
        var profile = new Profile { Name = "Test" };
        _storage.InsertProfile(profile);

        var entry = new LogEntry { ProfileId = profile.Id, BodyText = "削除テスト" };
        _storage.InsertLogEntry(entry);

        _storage.SoftDeleteLogEntry(entry.Id);

        var entries = _storage.GetLogEntries(profile.Id);
        Assert.Empty(entries);

        var entriesWithDeleted = _storage.GetLogEntries(profile.Id, includeDeleted: true);
        Assert.Single(entriesWithDeleted);
    }

    [Fact]
    public void LogEntry_DisplayProperties()
    {
        var entry = new LogEntry
        {
            SpeakerName = "ヒナ",
            SpeakerOrg = "ゲヘナ",
            BodyText = "原文",
            EditedBodyText = "修正済み",
        };

        Assert.Equal("ヒナ", entry.DisplayName);
        Assert.Equal("ゲヘナ", entry.DisplayOrg);
        Assert.Equal("修正済み", entry.DisplayBody);
        Assert.Equal("ヒナ / ゲヘナ", entry.DisplayHeader);
    }

    [Fact]
    public void Settings_SetAndGet()
    {
        _storage.SetSetting("theme", "dark");
        var value = _storage.GetSetting("theme");
        Assert.Equal("dark", value);

        _storage.SetSetting("theme", "light");
        value = _storage.GetSetting("theme");
        Assert.Equal("light", value);
    }

    [Fact]
    public void Profile_WithHotkey()
    {
        var profile = new Profile
        {
            Name = "Hotkey Test",
            Hotkey = new Hotkey(["ctrl", "l"]),
            NarratorHotkey = new Hotkey(["ctrl", "n"]),
        };

        _storage.InsertProfile(profile);
        var loaded = _storage.GetProfileById(profile.Id);

        Assert.NotNull(loaded?.Hotkey);
        Assert.Equal(2, loaded!.Hotkey!.Keys.Count);
        Assert.Equal("ctrl", loaded.Hotkey.Keys[0]);
        Assert.Equal("l", loaded.Hotkey.Keys[1]);
    }
}
