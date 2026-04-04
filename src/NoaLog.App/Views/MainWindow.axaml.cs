using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Shapes;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Threading;
using NoaLog.App.Controls;
using NoaLog.Core.Models;
using NoaLog.Core.Ocr;
using NoaLog.Core.Pipeline;
using NoaLog.Core.Storage;

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

    // Engineパネル（左ペイン）+ ステータスバー
    private Ellipse? _engineStatusDot;
    private TextBlock? _engineNameLabel;
    private TextBlock? _engineStatusLabel;
    private TextBlock? _engineLastTimeLabel;
    private TextBlock? _ocrEngineLabel;
    private DispatcherTimer? _engineCheckTimer;

    // 推論ログパネル
    private Border? _inferenceLogPanel;
    private TextBlock? _inferenceLogText;
    private ScrollViewer? _inferenceLogScroll;

    private readonly SqliteStorage _storage;
private List<Profile> _profiles = new();
    private Profile? _currentProfile;
    private List<LogEntry> _logEntries = new();
    private LogCard? _selectedCard;
    private LogEntry? _selectedEntry;
    private HashSet<LogCard> _selectedCards = new();
    private bool _isDragSelecting;
    private ScrollViewer? _logScrollViewer;
    private List<int> _matchIndices = new();
    private int _currentMatchIndex = -1;

    // AXAMLローダー用パラメータなしコンストラクタ
    public MainWindow() : this(App.Storage!) { }

    public MainWindow(SqliteStorage storage)
    {
        _storage = storage;
        InitializeComponent();
    }

    protected override void OnClosing(WindowClosingEventArgs e)
    {
        base.OnClosing(e);
        try { App.OllamaManager?.Dispose(); } catch { }
        Environment.Exit(0);
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
        _logScrollViewer = this.FindControl<ScrollViewer>("LogScrollViewer");
        _statCount = this.FindControl<TextBlock>("StatCount");
        _entryCountLabel = this.FindControl<TextBlock>("EntryCountLabel");
        _lastCaptureLabel = this.FindControl<TextBlock>("LastCaptureLabel");

        // OCRエンジン表示
        _ocrEngineLabel = this.FindControl<TextBlock>("OcrEngineLabel");

        // Engineパネル
        _engineStatusDot = this.FindControl<Ellipse>("EngineStatusDot");
        _engineNameLabel = this.FindControl<TextBlock>("EngineNameLabel");
        _engineStatusLabel = this.FindControl<TextBlock>("EngineStatusLabel");
        _engineLastTimeLabel = this.FindControl<TextBlock>("EngineLastTimeLabel");
        UpdateEnginePanel();

        // エンジン初期化は非同期なので定期チェック
        _engineCheckTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _engineCheckTimer.Tick += (_, _) =>
        {
            UpdateEnginePanel();
            if (App.OcrEngine?.IsReady == true)
                _engineCheckTimer.Stop();
        };
        _engineCheckTimer.Start();

        // 推論ログパネル
        _inferenceLogPanel = this.FindControl<Border>("InferenceLogPanel");
        _inferenceLogText = this.FindControl<TextBlock>("InferenceLogText");
        _inferenceLogScroll = this.FindControl<ScrollViewer>("InferenceLogScroll");
        var showLog = _storage.GetSetting("inference_log.visible");
        if (_inferenceLogPanel != null && string.Equals(showLog, "True", StringComparison.OrdinalIgnoreCase))
            _inferenceLogPanel.IsVisible = true;

        // QwenVlClientのストリーミングイベント購読
        SubscribeInferenceEvents();

        // OCRエンジン切替イベント購読
        App.OcrEngineChanged += OnOcrEngineChanged;

        // CaptureWorkerのエントリ完了イベント購読
        if (App.CaptureWorker != null)
        {
            App.CaptureWorker.EntryCreated += OnCaptureEntryCreated;
            App.CaptureWorker.ProcessingFailed += (_, _) =>
                Dispatcher.UIThread.Post(() =>
                {
                    if (_haloIndicator != null)
                        _haloIndicator.State = HaloState.Failed;
                });
        }

        // ドラッグ選択イベント
        if (_logScrollViewer != null)
        {
            _logScrollViewer.PointerPressed += OnLogListPointerPressed;
            _logScrollViewer.PointerMoved += OnLogListPointerMoved;
            _logScrollViewer.PointerReleased += OnLogListPointerReleased;
        }

        // DetailPanel・CopyPanel・SearchBarは名前で検索
        _detailPanel = this.FindControl<DetailPanel>("DetailPanel");
        _copyPanel = this.FindControl<CopyPanel>("CopyPanel");
        _searchBar = this.FindControl<SearchBar>("SearchBar");

        // DetailPanel編集イベント → LogCardリアルタイム更新
        if (_detailPanel != null)
            _detailPanel.EntryEdited += OnDetailPanelEdited;

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
            _searchBar.ReplaceRequested += OnReplaceRequested;
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

        // 起動時はログを読み込まない — 新規キャプチャのみ表示
        _logEntries = new List<LogEntry>();
        RebuildLogCards();
        UpdateStats();

        // 選択解除
        _selectedCard = null;
        _selectedEntry = null;
        _selectedCards.Clear();
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

        // Ctrl/Cmd+クリックで追加選択
        var args = e as PointerPressedEventArgs;
        bool isMultiSelect = args?.KeyModifiers.HasFlag(KeyModifiers.Control) == true ||
                             args?.KeyModifiers.HasFlag(KeyModifiers.Meta) == true;

        if (isMultiSelect)
        {
            // トグル選択
            if (_selectedCards.Contains(clickedCard))
            {
                clickedCard.IsCardSelected = false;
                _selectedCards.Remove(clickedCard);
            }
            else
            {
                clickedCard.IsCardSelected = true;
                _selectedCards.Add(clickedCard);
            }
        }
        else
        {
            // 通常クリック: 他の選択を解除して1つ選択
            DeselectAllCards();
            clickedCard.IsCardSelected = true;
            _selectedCards.Add(clickedCard);
        }

        _selectedCard = clickedCard;

        // エントリを取得してDetailPanelに表示
        var entry = _logEntries.FirstOrDefault(e => e.Id == clickedCard.EntryId);
        if (entry != null)
        {
            _selectedEntry = entry;
            _detailPanel?.SetEntry(entry);
        }
    }

    private void SelectAllCards()
    {
        if (_logList == null) return;
        foreach (var item in _logList.Items)
        {
            if (item is LogCard card)
            {
                card.IsCardSelected = true;
                _selectedCards.Add(card);
            }
        }
    }

    private void DeselectAllCards()
    {
        foreach (var card in _selectedCards)
            card.IsCardSelected = false;
        _selectedCards.Clear();
        _selectedCard = null;
        _selectedEntry = null;
    }

    private void DeleteSelectedCards()
    {
        if (_selectedCards.Count == 0) return;

        // 選択されたカードのEntryIdを収集
        var idsToRemove = _selectedCards.Select(c => c.EntryId).ToHashSet();

        // リストから削除
        _logEntries.RemoveAll(e => idsToRemove.Contains(e.Id));

        // 選択状態クリア
        _selectedCards.Clear();
        _selectedCard = null;
        _selectedEntry = null;
        _detailPanel?.ClearEntry();

        // UI再構築
        RebuildLogCards();
        UpdateStats();
    }

    // ── ドラッグ選択 ──

    private void OnLogListPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        _isDragSelecting = true;
    }

    private void OnLogListPointerMoved(object? sender, PointerEventArgs e)
    {
        if (!_isDragSelecting || _logList == null || _logScrollViewer == null) return;

        var pos = e.GetPosition(_logList);

        // カーソル位置のカードを選択
        foreach (var item in _logList.Items)
        {
            if (item is LogCard card)
            {
                var cardBounds = card.Bounds;
                if (pos.Y >= cardBounds.Y && pos.Y <= cardBounds.Y + cardBounds.Height)
                {
                    if (!_selectedCards.Contains(card))
                    {
                        card.IsCardSelected = true;
                        _selectedCards.Add(card);
                    }
                }
            }
        }

        // 上端/下端付近で自動スクロール
        var scrollPos = e.GetPosition(_logScrollViewer);
        if (scrollPos.Y < 30)
            _logScrollViewer.Offset = new Avalonia.Vector(_logScrollViewer.Offset.X, Math.Max(0, _logScrollViewer.Offset.Y - 15));
        else if (scrollPos.Y > _logScrollViewer.Bounds.Height - 30)
            _logScrollViewer.Offset = new Avalonia.Vector(_logScrollViewer.Offset.X, _logScrollViewer.Offset.Y + 15);
    }

    private void OnLogListPointerReleased(object? sender, PointerReleasedEventArgs e)
    {
        _isDragSelecting = false;
    }

    private void OnDetailPanelEdited(object? sender, EventArgs e)
    {
        if (_selectedCard == null || _selectedEntry == null) return;

        _selectedCard.SpeakerNameText = _selectedEntry.DisplayName;
        _selectedCard.OrgText = _selectedEntry.DisplayOrg;
        _selectedCard.BodyText = _selectedEntry.DisplayBody;
        _selectedCard.IsEdited = true;
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

        // Ctrl (Windows/Linux) or Cmd (macOS)
        bool hasModifier = e.KeyModifiers.HasFlag(KeyModifiers.Control) ||
                           e.KeyModifiers.HasFlag(KeyModifiers.Meta);

        if (hasModifier)
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
                case Key.L:
                    e.Handled = true;
                    OnCaptureClick(null, e);
                    break;
                case Key.A:
                    e.Handled = true;
                    SelectAllCards();
                    break;
                case Key.N:
                    e.Handled = true;
                    OnNarratorCaptureClick();
                    break;
            }
        }

        if (e.Key == Key.Escape)
        {
            e.Handled = true;
            DeselectAllCards();
        }

        if (e.Key == Key.Back || e.Key == Key.Delete)
        {
            e.Handled = true;
            DeleteSelectedCards();
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
        Console.Error.WriteLine($"[Regions] OnRegionsSelected called: TextArea={e.TextAreaRect}, Narrator={e.NarratorRect}");

        // プロファイルがなければ自動作成
        if (_currentProfile == null)
        {
            Console.Error.WriteLine("[Regions] No profile — creating default");
            _currentProfile = new Profile { Name = "Default" };
            _storage.InsertProfile(_currentProfile);
            LoadProfiles();
        }

        if (e.TextAreaRect is { } ta)
            _currentProfile.TextAreaRect = new Core.Models.Rect((int)ta.X, (int)ta.Y, (int)ta.Width, (int)ta.Height);
        if (e.NarratorRect is { } nr)
            _currentProfile.NarratorRect = new Core.Models.Rect((int)nr.X, (int)nr.Y, (int)nr.Width, (int)nr.Height);

        Console.Error.WriteLine($"[Regions] Saved to profile: TextAreaRect={_currentProfile.TextAreaRect}");

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

    private async void OnCaptureClick(object? sender, RoutedEventArgs e)
    {
        Console.Error.WriteLine($"[Capture] Profile={_currentProfile?.Name}, TextAreaRect={_currentProfile?.TextAreaRect}, Engine={App.OcrEngine?.EngineName}, IsReady={App.OcrEngine?.IsReady}");

        // 領域が未設定の場合
        if (_currentProfile == null || _currentProfile.TextAreaRect == null)
        {
            Console.Error.WriteLine("[Capture] No profile or text area rect — aborting");
            if (_haloIndicator != null)
                _haloIndicator.State = HaloState.Failed;
            return;
        }
        if (App.CaptureQueue == null) return;

        // エンジン未準備
        if (App.OcrEngine == null || !App.OcrEngine.IsReady)
        {
            Console.Error.WriteLine("[Capture] Engine not ready — aborting");
            if (_haloIndicator != null)
                _haloIndicator.State = HaloState.Failed;
            return;
        }

        if (_haloIndicator != null)
            _haloIndicator.State = HaloState.Processing;

        Console.Error.WriteLine($"[Capture] Enqueueing capture request for profile {_currentProfile.Id}");

        var request = new CaptureRequest(
            _currentProfile.Id,
            _currentProfile.TextAreaRect,
            _currentProfile.NarratorRect
        );
        await App.CaptureQueue.EnqueueAsync(request);
    }

    private async void OnNarratorCaptureClick()
    {
        if (_currentProfile == null || _currentProfile.NarratorRect == null)
        {
            Console.Error.WriteLine("[Capture] No narrator rect — aborting");
            if (_haloIndicator != null)
                _haloIndicator.State = HaloState.Failed;
            return;
        }
        if (App.CaptureQueue == null || App.OcrEngine == null || !App.OcrEngine.IsReady)
        {
            if (_haloIndicator != null)
                _haloIndicator.State = HaloState.Failed;
            return;
        }

        if (_haloIndicator != null)
            _haloIndicator.State = HaloState.Processing;

        var request = new CaptureRequest(
            _currentProfile.Id,
            _currentProfile.NarratorRect,
            null,
            "narration"
        );
        await App.CaptureQueue.EnqueueAsync(request);
    }

    private void OnCaptureEntryCreated(object? sender, LogEntry entry)
    {
        Dispatcher.UIThread.Post(() =>
        {
            if (_haloIndicator != null)
                _haloIndicator.State = HaloState.Success;

            _logEntries.Add(entry);
            RebuildLogCards();
            UpdateStats();

            // 推論時間を表示（エントリのタイムスタンプから概算）
            if (_engineLastTimeLabel != null)
                _engineLastTimeLabel.Text = $"Last: {DateTime.Now:HH:mm:ss}";
        });
    }

    private void UpdateEnginePanel()
    {
        var engine = App.OcrEngine;
        if (engine == null) return;

        if (_engineNameLabel != null)
            _engineNameLabel.Text = engine.EngineName;

        if (_engineStatusLabel != null)
            _engineStatusLabel.Text = engine.IsReady ? "Ready" : "Not Ready";

        if (_engineStatusDot != null)
            _engineStatusDot.Fill = engine.IsReady
                ? new SolidColorBrush(Color.Parse("#7EC8A0"))
                : new SolidColorBrush(Color.Parse("#D4A0A0"));

        // ステータスバーのエンジン名も同期
        if (_ocrEngineLabel != null)
            _ocrEngineLabel.Text = engine.EngineName;
    }

    private void OnOcrEngineChanged(object? sender, EventArgs e)
    {
        Dispatcher.UIThread.Post(() =>
        {
            // ENGINEパネル + ステータスバー更新
            UpdateEnginePanel();

            // CaptureWorkerの再購読（新ワーカーに切り替わっているため）
            if (App.CaptureWorker != null)
            {
                App.CaptureWorker.EntryCreated -= OnCaptureEntryCreated;
                App.CaptureWorker.EntryCreated += OnCaptureEntryCreated;
                App.CaptureWorker.ProcessingFailed += (_, _) =>
                    Dispatcher.UIThread.Post(() =>
                    {
                        if (_haloIndicator != null)
                            _haloIndicator.State = HaloState.Failed;
                    });
            }

            // 初期化待ちタイマー再開
            _engineCheckTimer?.Start();
        });
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

        _matchIndices = matchIndices;
        _currentMatchIndex = matchIndices.Count > 0 ? 0 : -1;
        _searchBar?.UpdateMatchCount(matchIndices.Count, _currentMatchIndex);

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

    private void OnReplaceRequested(object? sender, ReplaceEventArgs e)
    {
        if (string.IsNullOrEmpty(e.Query) || _currentMatchIndex < 0 || _currentMatchIndex >= _matchIndices.Count)
            return;

        var entryIndex = _matchIndices[_currentMatchIndex];
        var entry = _logEntries[entryIndex];

        ReplaceInEntry(entry, e.Query, e.Replacement, e.IsRegex, onceOnly: true);

        // LogCard更新
        if (_logList?.Items[entryIndex] is LogCard card)
        {
            card.SpeakerNameText = entry.DisplayName;
            card.OrgText = entry.DisplayOrg;
            card.BodyText = entry.DisplayBody;
            card.IsEdited = true;
        }

        // DetailPanel更新
        if (_selectedEntry?.Id == entry.Id)
            _detailPanel?.SetEntry(entry);

        // 次のマッチへ移動
        if (_currentMatchIndex < _matchIndices.Count - 1)
        {
            _currentMatchIndex++;
            _searchBar?.UpdateMatchCount(_matchIndices.Count, _currentMatchIndex);
            OnNavigateToMatch(null, _currentMatchIndex);
        }
    }

    private void OnReplaceAllRequested(object? sender, ReplaceEventArgs e)
    {
        if (string.IsNullOrEmpty(e.Query)) return;

        int replacedCount = 0;
        foreach (var entry in _logEntries)
        {
            if (ReplaceInEntry(entry, e.Query, e.Replacement, e.IsRegex, onceOnly: false))
                replacedCount++;
        }

        if (replacedCount > 0)
        {
            RebuildLogCards();
            _detailPanel?.ClearEntry();
            _selectedCard = null;
            _selectedEntry = null;
        }
    }

    private static bool ReplaceInEntry(LogEntry entry, string query, string replacement, bool isRegex, bool onceOnly)
    {
        bool changed = false;

        // Speaker
        var speaker = entry.EditedSpeakerName ?? entry.SpeakerName;
        var newSpeaker = ApplyReplace(speaker, query, replacement, isRegex, onceOnly);
        if (newSpeaker != speaker) { entry.EditedSpeakerName = newSpeaker; changed = true; }

        // Org
        var org = entry.EditedSpeakerOrg ?? entry.SpeakerOrg;
        var newOrg = ApplyReplace(org, query, replacement, isRegex, onceOnly);
        if (newOrg != org) { entry.EditedSpeakerOrg = newOrg; changed = true; }

        // Body
        var body = entry.EditedBodyText ?? entry.BodyText;
        var newBody = ApplyReplace(body, query, replacement, isRegex, onceOnly);
        if (newBody != body) { entry.EditedBodyText = newBody; changed = true; }

        return changed;
    }

    private static string ApplyReplace(string text, string query, string replacement, bool isRegex, bool onceOnly)
    {
        if (string.IsNullOrEmpty(text)) return text;

        if (isRegex)
        {
            try
            {
                var regex = new System.Text.RegularExpressions.Regex(query,
                    System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                return onceOnly ? regex.Replace(text, replacement, 1) : regex.Replace(text, replacement);
            }
            catch { return text; }
        }

        if (onceOnly)
        {
            var idx = text.IndexOf(query, StringComparison.OrdinalIgnoreCase);
            if (idx < 0) return text;
            return text[..idx] + replacement + text[(idx + query.Length)..];
        }

        return text.Replace(query, replacement, StringComparison.OrdinalIgnoreCase);
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
        // 選択があればそれだけ、なければ全件
        var selectedIds = _selectedCards.Select(c => c.EntryId).ToHashSet();
        var entries = selectedIds.Count > 0
            ? _logEntries.Where(e => selectedIds.Contains(e.Id)).ToList()
            : _logEntries;

        var dialog = new ExportDialog(entries);
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

    // ── 推論ログパネル ──

    private void SubscribeInferenceEvents()
    {
        if (App.OcrEngine is QwenVlClient qwen)
        {
            qwen.InferenceStarted += label =>
                Dispatcher.UIThread.Post(() => AppendInferenceLog($"\n[{label}] "));

            qwen.TokenReceived += token =>
                Dispatcher.UIThread.Post(() => AppendInferenceLog(token));

            qwen.InferenceCompleted += _ =>
                Dispatcher.UIThread.Post(() => AppendInferenceLog(" ✓\n"));
        }
    }

    private void AppendInferenceLog(string text)
    {
        if (_inferenceLogText == null) return;
        _inferenceLogText.Text += text;

        // 長くなりすぎたら先頭を切り捨て
        if (_inferenceLogText.Text.Length > 5000)
            _inferenceLogText.Text = _inferenceLogText.Text[^3000..];

        _inferenceLogScroll?.ScrollToEnd();
    }

    public void SetInferenceLogVisible(bool visible)
    {
        if (_inferenceLogPanel != null)
            _inferenceLogPanel.IsVisible = visible;
    }
}
