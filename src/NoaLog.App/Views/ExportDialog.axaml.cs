using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Avalonia;
using Avalonia.Animation;
using Avalonia.Animation.Easings;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Platform.Storage;
using Avalonia.Styling;
using NoaLog.Core.Export;
using NoaLog.Core.Models;

namespace NoaLog.App.Views;

/// <summary>
/// ログエントリを一括エクスポートするダイアログ
/// </summary>
public partial class ExportDialog : Window
{
    private readonly List<LogEntry> _allEntries;
    private readonly List<LogEntry> _selectedEntries;

    // コントロール参照
    private RadioButton? _formatPlain;
    private RadioButton? _formatMarkdown;
    private RadioButton? _formatJson;
    private RadioButton? _rangeAll;
    private RadioButton? _rangeSelected;
    private TextBlock? _entryCountLabel;
    private TextBox? _previewBox;

    /// <summary>
    /// デザイナ用パラメータなしコンストラクタ
    /// </summary>
    public ExportDialog() : this(new List<LogEntry>()) { }

    /// <summary>
    /// エントリを渡してダイアログを生成する
    /// </summary>
    /// <param name="entries">エクスポート対象のログエントリ一覧</param>
    public ExportDialog(List<LogEntry> entries)
    {
        _allEntries = entries ?? new List<LogEntry>();
        _selectedEntries = new List<LogEntry>();
        InitializeComponent();
    }

    /// <summary>
    /// 選択中のエントリを設定する（ShowDialog前に呼ぶ）
    /// </summary>
    public void SetSelectedEntries(List<LogEntry> selected)
    {
        _selectedEntries.Clear();
        if (selected != null)
            _selectedEntries.AddRange(selected);

        UpdateEntryCountLabel();
        UpdatePreview();
    }

    protected override async void OnOpened(EventArgs e)
    {
        base.OnOpened(e);

        Opacity = 0;
        var scaleTransform = new ScaleTransform(0.97, 0.97);
        RenderTransform = scaleTransform;
        RenderTransformOrigin = new RelativePoint(0.5, 0.5, RelativeUnit.Relative);

        var fadeIn = new Animation
        {
            Duration = TimeSpan.FromMilliseconds(200),
            Easing = new CubicEaseOut(),
            Children =
            {
                new KeyFrame { Cue = new Cue(0), Setters = { new Setter(OpacityProperty, 0.0) } },
                new KeyFrame { Cue = new Cue(1), Setters = { new Setter(OpacityProperty, 1.0) } },
            }
        };

        var scaleInX = new Animation
        {
            Duration = TimeSpan.FromMilliseconds(200),
            Easing = new CubicEaseOut(),
            Children =
            {
                new KeyFrame { Cue = new Cue(0), Setters = { new Setter(ScaleTransform.ScaleXProperty, 0.97) } },
                new KeyFrame { Cue = new Cue(1), Setters = { new Setter(ScaleTransform.ScaleXProperty, 1.0) } },
            }
        };

        var scaleInY = new Animation
        {
            Duration = TimeSpan.FromMilliseconds(200),
            Easing = new CubicEaseOut(),
            Children =
            {
                new KeyFrame { Cue = new Cue(0), Setters = { new Setter(ScaleTransform.ScaleYProperty, 0.97) } },
                new KeyFrame { Cue = new Cue(1), Setters = { new Setter(ScaleTransform.ScaleYProperty, 1.0) } },
            }
        };

        _ = scaleInX.RunAsync(this);
        _ = scaleInY.RunAsync(this);
        await fadeIn.RunAsync(this);
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);

        // コントロール取得（FindControl パターン）
        _formatPlain = this.FindControl<RadioButton>("FormatPlain");
        _formatMarkdown = this.FindControl<RadioButton>("FormatMarkdown");
        _formatJson = this.FindControl<RadioButton>("FormatJson");
        _rangeAll = this.FindControl<RadioButton>("RangeAll");
        _rangeSelected = this.FindControl<RadioButton>("RangeSelected");
        _entryCountLabel = this.FindControl<TextBlock>("EntryCountLabel");
        _previewBox = this.FindControl<TextBox>("PreviewBox");

        // 選択エントリがない場合は「選択中のみ」を無効化
        if (_rangeSelected != null && _selectedEntries.Count == 0)
            _rangeSelected.IsEnabled = false;

        // イベントハンドラ登録
        if (_formatPlain != null) _formatPlain.IsCheckedChanged += OnOptionChanged;
        if (_formatMarkdown != null) _formatMarkdown.IsCheckedChanged += OnOptionChanged;
        if (_formatJson != null) _formatJson.IsCheckedChanged += OnOptionChanged;
        if (_rangeAll != null) _rangeAll.IsCheckedChanged += OnOptionChanged;
        if (_rangeSelected != null) _rangeSelected.IsCheckedChanged += OnOptionChanged;

        UpdateEntryCountLabel();
        UpdatePreview();
    }

    /// <summary>
    /// 現在の範囲選択に基づいてエントリ一覧を取得する
    /// </summary>
    private IReadOnlyList<LogEntry> GetCurrentEntries()
    {
        if (_rangeSelected?.IsChecked == true && _selectedEntries.Count > 0)
            return _selectedEntries;
        return _allEntries;
    }

    /// <summary>
    /// 現在のフォーマット選択に基づいてフォーマット名を取得する
    /// </summary>
    private string GetCurrentFormat()
    {
        if (_formatMarkdown?.IsChecked == true) return "markdown";
        if (_formatJson?.IsChecked == true) return "json";
        return "plain";
    }

    /// <summary>
    /// エントリ数ラベルを更新する
    /// </summary>
    private void UpdateEntryCountLabel()
    {
        if (_entryCountLabel == null) return;
        var entries = GetCurrentEntries();
        _entryCountLabel.Text = $"{entries.Count} entries";
    }

    /// <summary>
    /// プレビューエリアを更新する（最大10行分）
    /// </summary>
    private void UpdatePreview()
    {
        if (_previewBox == null) return;

        var entries = GetCurrentEntries();
        if (entries.Count == 0)
        {
            _previewBox.Text = "(no entries)";
            return;
        }

        // プレビュー用に最大10エントリを使用
        var previewEntries = entries.Take(10).ToList();
        var format = GetCurrentFormat();

        var text = format switch
        {
            "markdown" => LogExporter.ToMarkdown(previewEntries),
            "json" => LogExporter.ToJson(previewEntries),
            _ => LogExporter.ToPlainText(previewEntries),
        };

        if (entries.Count > 10)
            text += $"\n\n... and {entries.Count - 10} more entries";

        _previewBox.Text = text;
    }

    /// <summary>
    /// フォーマットまたは範囲が変更されたときにプレビューを更新する
    /// </summary>
    private void OnOptionChanged(object? sender, RoutedEventArgs e)
    {
        UpdateEntryCountLabel();
        UpdatePreview();
    }

    /// <summary>
    /// 保存ボタン: SaveFileDialogでファイルに書き出す
    /// </summary>
    private async void OnSaveClick(object? sender, RoutedEventArgs e)
    {
        var entries = GetCurrentEntries();
        if (entries.Count == 0) return;

        var format = GetCurrentFormat();

        // ファイル拡張子とフィルタを決定
        var (extension, filterName) = format switch
        {
            "markdown" => ("md", "Markdown"),
            "json" => ("json", "JSON"),
            _ => ("txt", "Text"),
        };

        // Avalonia StorageProvider を使用
        var storageProvider = GetTopLevel(this)?.StorageProvider;
        if (storageProvider == null) return;

        var file = await storageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = "Export Log",
            SuggestedFileName = $"noalog_export.{extension}",
            FileTypeChoices = new[]
            {
                new FilePickerFileType(filterName) { Patterns = new[] { $"*.{extension}" } },
                new FilePickerFileType("All Files") { Patterns = new[] { "*.*" } },
            },
        });

        if (file == null) return;

        // エクスポートテキスト生成
        var text = format switch
        {
            "markdown" => LogExporter.ToMarkdown(entries),
            "json" => LogExporter.ToJson(entries),
            _ => LogExporter.ToPlainText(entries),
        };

        // ファイル書き込み
        await using var stream = await file.OpenWriteAsync();
        await using var writer = new StreamWriter(stream);
        await writer.WriteAsync(text);

        Close(true);
    }

    /// <summary>
    /// キャンセルボタン: ダイアログを閉じる
    /// </summary>
    private void OnCancelClick(object? sender, RoutedEventArgs e)
    {
        Close(null);
    }
}
