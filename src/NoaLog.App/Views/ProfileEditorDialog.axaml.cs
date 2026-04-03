using System;
using Avalonia.Animation;
using Avalonia.Animation.Easings;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Styling;
using NoaLog.Core.Models;

namespace NoaLog.App.Views;

public partial class ProfileEditorDialog : Window
{
    private Profile? _profile;
    private List<string> _captureHotkeyKeys = new();
    private List<string> _narratorHotkeyKeys = new();

    public Profile? Result { get; private set; }

    public ProfileEditorDialog()
    {
        InitializeComponent();
        AttachRegionPreviewHandlers();
    }

    public ProfileEditorDialog(Profile? existingProfile = null) : this()
    {
        _profile = existingProfile;
        if (_profile != null)
            LoadProfile(_profile);
    }

    protected override void OnOpened(EventArgs e)
    {
        base.OnOpened(e);
    }

    private void LoadProfile(Profile profile)
    {
        ProfileNameBox.Text = profile.Name;
        DescriptionBox.Text = profile.Description;
        NarratorLabelBox.Text = profile.NarratorLabel;

        if (profile.TextAreaRect is { } ta)
        {
            HeaderX.Value = ta.X;
            HeaderY.Value = ta.Y;
            HeaderW.Value = ta.Width;
            HeaderH.Value = ta.Height;
        }

        if (profile.NarratorRect is { } nr)
        {
            NarratorX.Value = nr.X;
            NarratorY.Value = nr.Y;
            NarratorW.Value = nr.Width;
            NarratorH.Value = nr.Height;
        }

        if (profile.Hotkey is { } hk)
        {
            _captureHotkeyKeys = new List<string>(hk.Keys);
            CaptureHotkeyBox.Text = hk.ToString();
        }

        if (profile.NarratorHotkey is { } nhk)
        {
            _narratorHotkeyKeys = new List<string>(nhk.Keys);
            NarratorHotkeyBox.Text = nhk.ToString();
        }

        UpdateAllPreviews();
    }

    private Profile BuildProfile()
    {
        var profile = _profile != null
            ? new Profile
            {
                Id = _profile.Id,
                CreatedAt = _profile.CreatedAt,
                IsActive = _profile.IsActive,
                OcrSettings = _profile.OcrSettings,
            }
            : new Profile();

        profile.Name = ProfileNameBox.Text?.Trim() ?? "";
        profile.Description = DescriptionBox.Text?.Trim() ?? "";
        profile.NarratorLabel = NarratorLabelBox.Text?.Trim() ?? "語り部";
        profile.UpdatedAt = DateTime.UtcNow;

        profile.TextAreaRect = new Rect(
            (int)(HeaderX.Value ?? 0),
            (int)(HeaderY.Value ?? 0),
            (int)(HeaderW.Value ?? 0),
            (int)(HeaderH.Value ?? 0));

        profile.NarratorRect = new Rect(
            (int)(NarratorX.Value ?? 0),
            (int)(NarratorY.Value ?? 0),
            (int)(NarratorW.Value ?? 0),
            (int)(NarratorH.Value ?? 0));

        profile.Hotkey = _captureHotkeyKeys.Count > 0 ? new Hotkey(_captureHotkeyKeys) : null;
        profile.NarratorHotkey = _narratorHotkeyKeys.Count > 0 ? new Hotkey(_narratorHotkeyKeys) : null;

        return profile;
    }

    private void OnSaveClick(object? sender, RoutedEventArgs e)
    {
        Result = BuildProfile();
        Close(Result);
    }

    private void OnCancelClick(object? sender, RoutedEventArgs e)
    {
        Close(null);
    }

    // ── Hotkey Capture ──

    private void OnCaptureHotkeyKeyDown(object? sender, KeyEventArgs e)
    {
        e.Handled = true;
        var keys = BuildKeyList(e);
        if (keys.Count == 0) return;

        _captureHotkeyKeys = keys;
        CaptureHotkeyBox.Text = string.Join("+", keys);
    }

    private void OnNarratorHotkeyKeyDown(object? sender, KeyEventArgs e)
    {
        e.Handled = true;
        var keys = BuildKeyList(e);
        if (keys.Count == 0) return;

        _narratorHotkeyKeys = keys;
        NarratorHotkeyBox.Text = string.Join("+", keys);
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
        {
            // Modifier-only press: don't record yet
            return keys.Count > 0 ? keys : new List<string>();
        }

        keys.Add(key.ToString());
        return keys;
    }

    private void OnClearCaptureHotkey(object? sender, RoutedEventArgs e)
    {
        _captureHotkeyKeys.Clear();
        CaptureHotkeyBox.Text = "";
    }

    private void OnClearNarratorHotkey(object? sender, RoutedEventArgs e)
    {
        _narratorHotkeyKeys.Clear();
        NarratorHotkeyBox.Text = "";
    }

    // ── Region Preview ──

    private void AttachRegionPreviewHandlers()
    {
        HeaderX.ValueChanged += (_, _) => UpdateHeaderPreview();
        HeaderY.ValueChanged += (_, _) => UpdateHeaderPreview();
        HeaderW.ValueChanged += (_, _) => UpdateHeaderPreview();
        HeaderH.ValueChanged += (_, _) => UpdateHeaderPreview();

        BodyX.ValueChanged += (_, _) => UpdateBodyPreview();
        BodyY.ValueChanged += (_, _) => UpdateBodyPreview();
        BodyW.ValueChanged += (_, _) => UpdateBodyPreview();
        BodyH.ValueChanged += (_, _) => UpdateBodyPreview();

        NarratorX.ValueChanged += (_, _) => UpdateNarratorPreview();
        NarratorY.ValueChanged += (_, _) => UpdateNarratorPreview();
        NarratorW.ValueChanged += (_, _) => UpdateNarratorPreview();
        NarratorH.ValueChanged += (_, _) => UpdateNarratorPreview();
    }

    private void UpdateAllPreviews()
    {
        UpdateHeaderPreview();
        UpdateBodyPreview();
        UpdateNarratorPreview();
    }

    private void UpdateHeaderPreview()
    {
        var x = (int)(HeaderX.Value ?? 0);
        var y = (int)(HeaderY.Value ?? 0);
        var w = (int)(HeaderW.Value ?? 0);
        var h = (int)(HeaderH.Value ?? 0);
        HeaderPreview.Text = $"({x}, {y}) - ({x + w}, {y + h})";
    }

    private void UpdateBodyPreview()
    {
        var x = (int)(BodyX.Value ?? 0);
        var y = (int)(BodyY.Value ?? 0);
        var w = (int)(BodyW.Value ?? 0);
        var h = (int)(BodyH.Value ?? 0);
        BodyPreview.Text = $"({x}, {y}) - ({x + w}, {y + h})";
    }

    private void UpdateNarratorPreview()
    {
        var x = (int)(NarratorX.Value ?? 0);
        var y = (int)(NarratorY.Value ?? 0);
        var w = (int)(NarratorW.Value ?? 0);
        var h = (int)(NarratorH.Value ?? 0);
        NarratorPreview.Text = $"({x}, {y}) - ({x + w}, {y + h})";
    }
}
