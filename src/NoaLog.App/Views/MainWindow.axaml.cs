using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using NoaLog.App.Controls;
using NoaLog.Core.Models;
using NoaLog.Core.Storage;
using NoaLog.Core.Telemetry;

namespace NoaLog.App.Views;

public partial class MainWindow : Window
{
    private HaloIndicator? _haloIndicator;
    private TextBlock? _regionHotkeyLabel;
    private TextBlock? _captureHotkeyLabel;
    private TextBlock? _narratorHotkeyLabel;
    private ComboBox? _profileCombo;
    private ItemsControl? _logList;
    private TextBlock? _statCount;
    private TextBlock? _entryCountLabel;
    private TextBlock? _lastCaptureLabel;

    // DetailPanel・CopyPanel（右ペイン）
    private DetailPanel? _detailPanel;
    private CopyPanel? _copyPanel;
    private SearchBar? _searchBar;

    private readonly SqliteStorage _storage;
    private readonly CorrectionLogger? _correctionLogger;
    private List<Profile> _profiles = new();
    private Profile? _currentProfile;
    private List<LogEntry> _logEntries = new();
    private LogCard? _selectedCard;
    private LogEntry? _selectedEntry;

    // AXAMLローダー用パラメータなしコンストラクタ
    public MainWindow() : this(App.Storage!, App.CorrectionLogger) { }

    public MainWindow(SqliteStorage storage, CorrectionLogger? correctionLogger = null)
    {
        _storage = storage;
        _correctionLogger = correctionLogger;
        InitializeComponent();
    }

    protected override void OnOpened(EventArgs e)
    {
        base.OnOpened(e);

        // コントロール参照取得
        _haloIndicator = this.FindControl<HaloIndicator>("HaloIndicator");
        _regionHotkeyLabel = this.FindControl<TextBlock>("RegionHotkeyLabel");
        _captureHotkeyLabel = this.FindControl<TextBlock>("CaptureHotkeyLabel");
        _narratorHotkeyLabel = this.FindControl<TextBlock>("NarratorHotkeyLabel");
        _profileCombo = this.FindControl<ComboBox>("ProfileCombo");
        _logList = this.FindControl<ItemsControl>("LogList");
        _statCount = this.FindControl<TextBlock>("StatCount");
        _entryCountLabel = this.FindControl<TextBlock>("EntryCountLabel");
        _lastCaptureLabel = this.FindControl<TextBlock>("LastCaptureLabel");

        // DetailPanel・CopyPanel・SearchBarは名前で検索
        _detailPanel = this.FindControl<DetailPanel>("DetailPanel");
        _copyPanel = this.FindControl<CopyPanel>("CopyPanel");
        _searchBar = this.FindControl<SearchBar>("SearchBar");

        // CopyPanelイベント
        if (_copyPanel != null)
        {
            _copyPanel.CopyRequested += OnCopyRequested;
            _copyPanel.ExportRequested += OnExportRequested;
        }

        // SearchBarイベント
        if (_searchBar != null)
        {
            _searchBar.SearchChanged += OnSearchChanged;
            _searchBar.NavigateToMatch += OnNavigateToMatch;
            _searchBar.ReplaceAllRequested += OnReplaceAllRequested;
            _searchBar.SearchClosed += OnSearchClosed;
        }

        // ProfileCombo変更イベント
        if (_profileCombo != null)
            _profileCombo.SelectionChanged += OnProfileSelectionChanged;

        UpdateHotkeyLabels();
        LoadProfiles();
    }

    // ── Profile管理 ──

    private void LoadProfiles()
    {
        _profiles = _storage.GetProfiles();

        if (_profileCombo == null) return;

        _profileCombo.Items.Clear();
        foreach (var profile in _profiles)
            _profileCombo.Items.Add(profile.Name);

        // 最初のプロファイルを自動選択
        if (_profiles.Count > 0)
            _profileCombo.SelectedIndex = 0;
    }

    private void OnProfileSelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (_profileCombo?.SelectedIndex is >= 0 and var idx && idx < _profiles.Count)
        {
            _currentProfile = _profiles[idx];
            LoadLogEntries();
        }
    }

    // ── ログリスト管理 ──

    private void LoadLogEntries()
    {
        if (_currentProfile == null || _logList == null) return;

        _logEntries = _storage.GetLogEntries(_currentProfile.Id);
        RebuildLogCards();
        UpdateStats();

        // 選択解除
        _selectedCard = null;
        _selectedEntry = null;
        _detailPanel?.ClearEntry();
    }

    private void RebuildLogCards()
    {
        if (_logList == null) return;

        _logList.Items.Clear();

        for (int i = 0; i < _logEntries.Count; i++)
        {
            var entry = _logEntries[i];
            var card = new LogCard
            {
                EntryId = entry.Id,
                SpeakerNameText = entry.DisplayName,
                OrgText = entry.DisplayOrg,
                BodyText = entry.DisplayBody,
                TimestampText = entry.Timestamp.ToString("HH:mm:ss"),
                IndexNumber = i + 1,
                IsEdited = entry.EditedBodyText != null || entry.EditedSpeakerName != null,
                IsNarration = entry.LogType == LogType.Narration,
                LowConfidence = entry.OcrConfidence > 0 && entry.OcrConfidence < 0.5,
            };

            card.CardClicked += OnLogCardClicked;
            _logList.Items.Add(card);
        }
    }

    private void OnLogCardClicked(object? sender, RoutedEventArgs e)
    {
        if (sender is not LogCard clickedCard) return;

        // 現在の編集を保存
        SaveCurrentEdits();

        // 前の選択を解除
        if (_selectedCard != null)
            _selectedCard.IsCardSelected = false;

        // 新しい選択
        clickedCard.IsCardSelected = true;
        _selectedCard = clickedCard;

        // エントリを取得してDetailPanelに表示
        var entry = _logEntries.FirstOrDefault(e => e.Id == clickedCard.EntryId);
        if (entry != null)
        {
            _selectedEntry = entry;
            _detailPanel?.SetEntry(entry);
        }
    }

    private void SaveCurrentEdits()
    {
        if (_selectedEntry == null || _detailPanel == null) return;

        // DetailPanelの現在の編集内容を取得して保存
        var currentEntry = _detailPanel.SelectedEntry;
        if (currentEntry == null) return;

        // 変更がある場合のみDB更新
        bool changed = false;
        if (currentEntry.EditedSpeakerName != _selectedEntry.EditedSpeakerName)
            changed = true;
        if (currentEntry.EditedSpeakerOrg != _selectedEntry.EditedSpeakerOrg)
            changed = true;
        if (currentEntry.EditedBodyText != _selectedEntry.EditedBodyText)
            changed = true;

        if (changed)
        {
            // 修正差分をテレメトリ用に記録
            if (_correctionLogger != null)
            {
                if (currentEntry.EditedSpeakerName != _selectedEntry.EditedSpeakerName)
                    _correctionLogger.LogCorrection(_selectedEntry, "speaker_name",
                        _selectedEntry.SpeakerName, currentEntry.EditedSpeakerName ?? "");
                if (currentEntry.EditedSpeakerOrg != _selectedEntry.EditedSpeakerOrg)
                    _correctionLogger.LogCorrection(_selectedEntry, "speaker_org",
                        _selectedEntry.SpeakerOrg, currentEntry.EditedSpeakerOrg ?? "");
                if (currentEntry.EditedBodyText != _selectedEntry.EditedBodyText)
                    _correctionLogger.LogCorrection(_selectedEntry, "body_text",
                        _selectedEntry.BodyText, currentEntry.EditedBodyText ?? "");
            }

            _storage.UpdateLogEntry(currentEntry);

            // LogCardの表示も更新
            if (_selectedCard != null)
            {
                _selectedCard.SpeakerNameText = currentEntry.DisplayName;
                _selectedCard.OrgText = currentEntry.DisplayOrg;
                _selectedCard.BodyText = currentEntry.DisplayBody;
                _selectedCard.IsEdited = true;
            }
        }
    }

    private void UpdateStats()
    {
        int count = _logEntries.Count;

        if (_statCount != null)
            _statCount.Text = count.ToString();

        if (_entryCountLabel != null)
            _entryCountLabel.Text = $"{count} entries";

        if (_lastCaptureLabel != null && _logEntries.Count > 0)
        {
            var last = _logEntries[^1].Timestamp;
            _lastCaptureLabel.Text = $"Last: {last:HH:mm:ss}";
        }
    }

    // ── ホットキー表示 ──

    private void UpdateHotkeyLabels()
    {
        bool isMac = RuntimeInformation.IsOSPlatform(OSPlatform.OSX);

        // 設定から読み込み（デフォルト値あり）
        var regionKey = _storage.GetSetting("hotkey_region") ?? (isMac ? "⌃R" : "Ctrl+R");
        var captureKey = _storage.GetSetting("hotkey_capture") ?? (isMac ? "⌃L" : "Ctrl+L");
        var narratorKey = _storage.GetSetting("hotkey_narrator") ?? (isMac ? "⌃N" : "Ctrl+N");

        if (_regionHotkeyLabel != null)
            _regionHotkeyLabel.Text = regionKey;
        if (_captureHotkeyLabel != null)
            _captureHotkeyLabel.Text = captureKey;
        if (_narratorHotkeyLabel != null)
            _narratorHotkeyLabel.Text = narratorKey;
    }

    // ── キーボードショートカット ──

    protected override void OnKeyDown(KeyEventArgs e)
    {
        base.OnKeyDown(e);

        if (e.KeyModifiers.HasFlag(KeyModifiers.Control))
        {
            switch (e.Key)
            {
                case Key.R:
                    e.Handled = true;
                    OpenCaptureOverlay();
                    break;
                case Key.F:
                    e.Handled = true;
                    _searchBar?.Show(false);
                    break;
                case Key.H:
                    e.Handled = true;
                    _searchBar?.Show(true);
                    break;
            }
        }
    }

    private void OpenCaptureOverlay()
    {
        var overlay = new CaptureOverlay();
        overlay.RegionsSelected += OnRegionsSelected;
        overlay.Show(this);
    }

    private void OnRegionsSelected(object? sender, RegionsSelectedEventArgs e)
    {
        if (_currentProfile == null) return;

        if (e.HeaderRect is { } hr)
            _currentProfile.HeaderRect = new Core.Models.Rect((int)hr.X, (int)hr.Y, (int)hr.Width, (int)hr.Height);
        if (e.BodyRect is { } br)
            _currentProfile.BodyRect = new Core.Models.Rect((int)br.X, (int)br.Y, (int)br.Width, (int)br.Height);
        if (e.NarratorRect is { } nr)
            _currentProfile.NarratorRect = new Core.Models.Rect((int)nr.X, (int)nr.Y, (int)nr.Width, (int)nr.Height);

        // プロファイルの領域をDBに保存
        _storage.UpdateProfile(_currentProfile);
    }

    // ── ボタンハンドラ ──

    private async void OnSettingsClick(object? sender, RoutedEventArgs e)
    {
        var dialog = new SettingsDialog(_storage);
        await dialog.ShowDialog<object?>(this);
        UpdateHotkeyLabels();
    }

    private async void OnNewProfileClick(object? sender, RoutedEventArgs e)
    {
        var dialog = new ProfileEditorDialog();
        await dialog.ShowDialog<object?>(this);

        if (dialog.Result is { } newProfile)
        {
            _storage.InsertProfile(newProfile);
            LoadProfiles();

            // 新しいプロファイルを選択
            var idx = _profiles.FindIndex(p => p.Id == newProfile.Id);
            if (idx >= 0 && _profileCombo != null)
                _profileCombo.SelectedIndex = idx;
        }
    }

    private async void OnEditProfileClick(object? sender, RoutedEventArgs e)
    {
        if (_currentProfile == null)
        {
            var msgBox = new Window
            {
                Title = "NoaLog",
                Width = 320,
                Height = 140,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Content = new TextBlock
                {
                    Text = "編集するプロファイルが選択されていません。",
                    VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center,
                    HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                    TextWrapping = Avalonia.Media.TextWrapping.Wrap,
                    Margin = new Avalonia.Thickness(16),
                },
            };
            await msgBox.ShowDialog(this);
            return;
        }

        var dialog = new ProfileEditorDialog(_currentProfile);
        await dialog.ShowDialog<object?>(this);

        if (dialog.Result is { } updatedProfile)
        {
            _storage.UpdateProfile(updatedProfile);
            _currentProfile = updatedProfile;
            LoadProfiles();
        }
    }

    private void OnCaptureClick(object? sender, RoutedEventArgs e)
    {
        if (_haloIndicator != null)
            _haloIndicator.State = HaloState.Processing;
    }

    // ── 検索・置換 ──

    private void OnSearchChanged(object? sender, SearchEventArgs e)
    {
        if (string.IsNullOrEmpty(e.Query))
        {
            // 検索クリア — 全カードを表示
            RebuildLogCards();
            _searchBar?.UpdateMatchCount(0, -1);
            return;
        }

        // マッチするエントリを検索
        var matchIndices = new List<int>();
        for (int i = 0; i < _logEntries.Count; i++)
        {
            var entry = _logEntries[i];
            bool match;

            if (e.IsRegex)
            {
                try
                {
                    var regex = new System.Text.RegularExpressions.Regex(e.Query,
                        System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                    match = regex.IsMatch(entry.DisplayName) ||
                            regex.IsMatch(entry.DisplayOrg) ||
                            regex.IsMatch(entry.DisplayBody);
                }
                catch
                {
                    match = false; // 不正な正規表現
                }
            }
            else
            {
                match = entry.DisplayName.Contains(e.Query, StringComparison.OrdinalIgnoreCase) ||
                        entry.DisplayOrg.Contains(e.Query, StringComparison.OrdinalIgnoreCase) ||
                        entry.DisplayBody.Contains(e.Query, StringComparison.OrdinalIgnoreCase);
            }

            if (match)
                matchIndices.Add(i);
        }

        _searchBar?.UpdateMatchCount(matchIndices.Count, matchIndices.Count > 0 ? 0 : -1);

        // マッチしたカードをハイライト（LogCardの選択状態で表示）
        if (_logList != null)
        {
            for (int i = 0; i < _logList.Items.Count; i++)
            {
                if (_logList.Items[i] is LogCard card)
                {
                    // マッチしていないカードは薄くする等の視覚的フィードバック
                    card.Opacity = matchIndices.Contains(i) ? 1.0 : 0.4;
                }
            }
        }
    }

    private void OnNavigateToMatch(object? sender, int matchIndex)
    {
        if (matchIndex < 0 || matchIndex >= _logEntries.Count) return;

        // 該当カードを選択
        if (_logList?.Items[matchIndex] is LogCard card)
        {
            // クリックイベントをシミュレート
            OnLogCardClicked(card, new RoutedEventArgs());
        }
    }

    private void OnReplaceAllRequested(object? sender, ReplaceEventArgs e)
    {
        if (string.IsNullOrEmpty(e.Query)) return;

        int replacedCount = 0;
        foreach (var entry in _logEntries)
        {
            bool changed = false;
            var body = entry.EditedBodyText ?? entry.BodyText;

            string newBody;
            if (e.IsRegex)
            {
                try
                {
                    var regex = new System.Text.RegularExpressions.Regex(e.Query,
                        System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                    newBody = regex.Replace(body, e.Replacement);
                }
                catch { continue; }
            }
            else
            {
                newBody = body.Replace(e.Query, e.Replacement, StringComparison.OrdinalIgnoreCase);
            }

            if (newBody != body)
            {
                entry.EditedBodyText = newBody;
                _storage.UpdateLogEntry(entry);
                changed = true;
                replacedCount++;
            }

            if (changed) continue; // body was changed
        }

        if (replacedCount > 0)
        {
            // ログリストを再構築
            RebuildLogCards();
            _detailPanel?.ClearEntry();
            _selectedCard = null;
            _selectedEntry = null;
        }
    }

    private void OnSearchClosed(object? sender, EventArgs e)
    {
        // 全カードの透明度をリセット
        if (_logList != null)
        {
            foreach (var item in _logList.Items)
            {
                if (item is LogCard card)
                    card.Opacity = 1.0;
            }
        }
    }

    // ── Copy/Export ──

    private async void OnCopyRequested(object? sender, EventArgs e)
    {
        if (_selectedEntry == null || _copyPanel == null) return;

        var format = _copyPanel.SelectedFormat;
        var text = FormatEntryForCopy(_selectedEntry, format);

        var clipboard = TopLevel.GetTopLevel(this)?.Clipboard;
        if (clipboard != null)
            await clipboard.SetTextAsync(text);
    }

    private async void OnExportRequested(object? sender, EventArgs e)
    {
        var dialog = new ExportDialog(_logEntries);
        await dialog.ShowDialog<object?>(this);
    }

    private static string FormatEntryForCopy(LogEntry entry, string format)
    {
        return format switch
        {
            "markdown" => $"## {entry.DisplayHeader}\n*{entry.Timestamp:yyyy-MM-dd HH:mm:ss}*\n\n{entry.DisplayBody}",
            "json" => System.Text.Json.JsonSerializer.Serialize(new
            {
                timestamp = entry.Timestamp.ToString("o"),
                speaker = entry.DisplayName,
                organization = entry.DisplayOrg,
                body = entry.DisplayBody,
            }, new System.Text.Json.JsonSerializerOptions { WriteIndented = true }),
            _ => $"[{entry.Timestamp:yyyy-MM-dd HH:mm:ss}] {entry.DisplayHeader}\n{entry.DisplayBody}",
        };
    }
}
