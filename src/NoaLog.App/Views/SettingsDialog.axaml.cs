using System;
using System.Collections.Generic;
using System.IO;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using NoaLog.Core.Ocr;
using NoaLog.Core.Storage;

namespace NoaLog.App.Views;

public partial class SettingsDialog : Window
{
    private SqliteStorage? _storage;
    private List<string> _regionHotkeyKeys = new();
    private List<string> _captureHotkeyKeys = new();
    private List<string> _narratorHotkeyKeys = new();

    public SettingsDialog() : this(null) { }

    public SettingsDialog(SqliteStorage? storage)
    {
        InitializeComponent();
        _storage = storage;
    }

    private void LoadSettings()
    {
        var regionBox = this.FindControl<TextBox>("RegionHotkeyBox");
        var captureBox = this.FindControl<TextBox>("CaptureHotkeyBox");
        var narratorBox = this.FindControl<TextBox>("NarratorHotkeyBox");
        var inferenceLogToggle = this.FindControl<ToggleSwitch>("InferenceLogToggle");

        // Region hotkey
        var regionSetting = _storage?.GetSetting("hotkey.region");
        if (string.IsNullOrEmpty(regionSetting))
        {
            regionSetting = "Ctrl+R";
        }
        _regionHotkeyKeys = new List<string>(regionSetting.Split('+'));
        if (regionBox != null) regionBox.Text = regionSetting;

        // Capture hotkey
        var captureSetting = _storage?.GetSetting("hotkey.capture");
        if (string.IsNullOrEmpty(captureSetting))
        {
            captureSetting = "Ctrl+L";
        }
        _captureHotkeyKeys = new List<string>(captureSetting.Split('+'));
        if (captureBox != null) captureBox.Text = captureSetting;

        // Narrator hotkey
        var narratorSetting = _storage?.GetSetting("hotkey.narrator");
        if (string.IsNullOrEmpty(narratorSetting))
        {
            narratorSetting = "Ctrl+N";
        }
        _narratorHotkeyKeys = new List<string>(narratorSetting.Split('+'));
        if (narratorBox != null) narratorBox.Text = narratorSetting;

        // 語り部の名前
        var narratorLabelBox = this.FindControl<TextBox>("NarratorLabelBox");
        var savedNarrator = _storage?.GetSetting("narrator.label") ?? "語り部";
        if (narratorLabelBox != null) narratorLabelBox.Text = savedNarrator;

        // Inference Log
        var inferenceLog = _storage?.GetSetting("inference_log.visible");
        if (inferenceLogToggle != null)
            inferenceLogToggle.IsChecked = string.Equals(inferenceLog, "True", StringComparison.OrdinalIgnoreCase);

        // Gemini設定
        var savedGeminiModel = _storage?.GetSetting("gemini.model") ?? "gemini-3.1-flash-lite";
        var radio31 = this.FindControl<RadioButton>("GeminiModel31FlashLite");
        var radio25Lite = this.FindControl<RadioButton>("GeminiModel25FlashLite");
        var radio25Pro = this.FindControl<RadioButton>("GeminiModel25Pro");
        if (radio31 != null) radio31.IsChecked = savedGeminiModel == "gemini-3.1-flash-lite";
        if (radio25Lite != null) radio25Lite.IsChecked = savedGeminiModel == "gemini-2.5-flash-lite";
        if (radio25Pro != null) radio25Pro.IsChecked = savedGeminiModel == "gemini-2.5-pro";

        var geminiStatus = this.FindControl<TextBlock>("GeminiApiKeyStatus");
        if (geminiStatus != null)
        {
            var hasKey = !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("GEMINI_API_KEY"));
            geminiStatus.Text = hasKey ? "設定済み ✓" : "未設定";
            geminiStatus.Foreground = hasKey
                ? SolidColorBrush.Parse("#16A34A")
                : SolidColorBrush.Parse("#DC2626");
        }

    }

    protected override void OnOpened(EventArgs e)
    {
        base.OnOpened(e);
        LoadSettings();
    }

    private void OnRegionHotkeyKeyDown(object? sender, KeyEventArgs e)
    {
        e.Handled = true;
        var keys = BuildKeyList(e);
        if (keys.Count == 0) return;
        _regionHotkeyKeys = keys;
        var box = this.FindControl<TextBox>("RegionHotkeyBox");
        if (box != null) box.Text = string.Join("+", keys);
    }

    private void OnCaptureHotkeyKeyDown(object? sender, KeyEventArgs e)
    {
        e.Handled = true;
        var keys = BuildKeyList(e);
        if (keys.Count == 0) return;
        _captureHotkeyKeys = keys;
        var box = this.FindControl<TextBox>("CaptureHotkeyBox");
        if (box != null) box.Text = string.Join("+", keys);
    }

    private void OnNarratorHotkeyKeyDown(object? sender, KeyEventArgs e)
    {
        e.Handled = true;
        var keys = BuildKeyList(e);
        if (keys.Count == 0) return;
        _narratorHotkeyKeys = keys;
        var box = this.FindControl<TextBox>("NarratorHotkeyBox");
        if (box != null) box.Text = string.Join("+", keys);
    }

    private void OnClearRegionHotkey(object? sender, RoutedEventArgs e)
    {
        _regionHotkeyKeys.Clear();
        var box = this.FindControl<TextBox>("RegionHotkeyBox");
        if (box != null) box.Text = string.Empty;
    }

    private void OnClearCaptureHotkey(object? sender, RoutedEventArgs e)
    {
        _captureHotkeyKeys.Clear();
        var box = this.FindControl<TextBox>("CaptureHotkeyBox");
        if (box != null) box.Text = string.Empty;
    }

    private void OnClearNarratorHotkey(object? sender, RoutedEventArgs e)
    {
        _narratorHotkeyKeys.Clear();
        var box = this.FindControl<TextBox>("NarratorHotkeyBox");
        if (box != null) box.Text = string.Empty;
    }

    private static List<string> BuildKeyList(KeyEventArgs e)
    {
        var keys = new List<string>();
        var modifiers = e.KeyModifiers;
        if (modifiers.HasFlag(KeyModifiers.Control)) keys.Add("Ctrl");
        if (modifiers.HasFlag(KeyModifiers.Alt)) keys.Add("Alt");
        if (modifiers.HasFlag(KeyModifiers.Shift)) keys.Add("Shift");
        if (modifiers.HasFlag(KeyModifiers.Meta)) keys.Add("Meta");
        var key = e.Key;
        if (key is Key.LeftCtrl or Key.RightCtrl or Key.LeftAlt or Key.RightAlt
            or Key.LeftShift or Key.RightShift or Key.LWin or Key.RWin)
            return keys.Count > 0 ? keys : new List<string>();
        keys.Add(key.ToString());
        return keys;
    }

    private void OnSaveClick(object? sender, RoutedEventArgs e)
    {
        if (_storage != null)
        {
            _storage.SetSetting("hotkey.region", string.Join("+", _regionHotkeyKeys));
            _storage.SetSetting("hotkey.capture", string.Join("+", _captureHotkeyKeys));
            _storage.SetSetting("hotkey.narrator", string.Join("+", _narratorHotkeyKeys));

            var inferenceLogToggle = this.FindControl<ToggleSwitch>("InferenceLogToggle");
            // 語り部の名前
            var narratorLabelBox = this.FindControl<TextBox>("NarratorLabelBox");
            var narratorLabel = narratorLabelBox?.Text?.Trim();
            if (!string.IsNullOrEmpty(narratorLabel))
                _storage.SetSetting("narrator.label", narratorLabel);

            _storage.SetSetting("inference_log.visible", inferenceLogToggle?.IsChecked?.ToString() ?? "False");

            // MainWindowの推論ログパネル表示を即時反映
            if (Owner is MainWindow mainWindow)
                mainWindow.SetInferenceLogVisible(inferenceLogToggle?.IsChecked == true);

            // Gemini モデル保存
            var geminiModel = "gemini-3.1-flash-lite";
            if (this.FindControl<RadioButton>("GeminiModel25FlashLite")?.IsChecked == true)
                geminiModel = "gemini-2.5-flash-lite";
            else if (this.FindControl<RadioButton>("GeminiModel25Pro")?.IsChecked == true)
                geminiModel = "gemini-2.5-pro";
            _storage.SetSetting("gemini.model", geminiModel);

            // Gemini エンジン再生成（モデル変更を反映）
            if (App.OcrEngine is GeminiOcrClient old)
                old.Dispose();
            App.OcrEngine = new GeminiOcrClient(modelId: geminiModel);
            _ = App.OcrEngine.InitializeAsync();
            App.NotifyOcrEngineChanged();
        }

        Close(true);
    }

    private void OnCancelClick(object? sender, RoutedEventArgs e)
    {
        Close(null);
    }

    private async void OnEulaClick(object? sender, RoutedEventArgs e)
    {
        var eulaText = LoadEulaText();

        var eulaWindow = new Window
        {
            Title = "利用規約 / Terms of Use",
            Width = 640,
            Height = 560,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Content = new ScrollViewer
            {
                Content = new TextBlock
                {
                    Text = eulaText,
                    TextWrapping = Avalonia.Media.TextWrapping.Wrap,
                    Margin = new Avalonia.Thickness(24),
                    FontSize = 13,
                    LineHeight = 22,
                },
            },
        };
        await eulaWindow.ShowDialog(this);
    }

    private static string LoadEulaText()
    {
        // Try to load EULA from docs/ relative to the executable
        var baseDir = AppContext.BaseDirectory;
        var candidates = new[]
        {
            Path.Combine(baseDir, "docs", "EULA_ja.md"),
            Path.Combine(baseDir, "..", "..", "..", "..", "..", "docs", "EULA_ja.md"), // dev layout
        };

        foreach (var path in candidates)
        {
            var fullPath = Path.GetFullPath(path);
            if (File.Exists(fullPath))
            {
                // Strip markdown formatting for plain-text display
                var md = File.ReadAllText(fullPath);
                return StripMarkdown(md);
            }
        }

        // Fallback: embedded text
        return "NoaLog 利用規約\n\n" +
               "Copyright (c) 2025-2026 nennchakki. All rights reserved.\n\n" +
               "本ソフトウェアはプロプライエタリライセンスの下で提供されています。\n" +
               "個人利用かつ非商用目的でのみ使用が許可されています。\n" +
               "改変、再配布、商用利用は著作権者の書面による許可なく行うことはできません。\n\n" +
               "本ソフトウェアは「現状のまま」（AS IS）で提供され、\n" +
               "いかなる保証も行いません。\n\n" +
               "【匿名データ送信について】\n" +
               "・デフォルトOFF。設定画面で明示的にONにした場合のみ動作します。\n" +
               "・送信データはOCR修正前・修正後テキストの差分のみです。\n" +
               "・スクリーンショット、ユーザー特定情報は収集しません。\n" +
               "・収集データはOCR辞書改善にのみ使用し、第三者提供はしません。\n\n" +
               "【お願い】\n" +
               "・ログ内に個人情報がある場合、匿名送信ON前に該当箇所を編集してください。\n" +
               "・記録したテキストの利用はゲームの利用規約に従ってください。\n\n" +
               "詳細はdocs/EULA_ja.mdをご参照ください。";
    }

    private static string StripMarkdown(string md)
    {
        // Simple markdown stripping for display in a TextBlock
        var lines = md.Split('\n');
        var result = new System.Text.StringBuilder();
        foreach (var line in lines)
        {
            var trimmed = line.TrimStart();
            // Convert headers to plain text with spacing
            if (trimmed.StartsWith("# "))
                result.AppendLine(trimmed[2..]);
            else if (trimmed.StartsWith("## "))
                result.AppendLine().AppendLine(trimmed[3..]);
            else if (trimmed.StartsWith("| ") && trimmed.Contains("---|"))
                continue; // Skip table separator rows
            else
                result.AppendLine(line);
        }
        return result.ToString().TrimEnd();
    }

}
