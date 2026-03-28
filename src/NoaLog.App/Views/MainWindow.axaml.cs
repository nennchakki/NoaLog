using System;
using System.Runtime.InteropServices;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using NoaLog.App.Controls;
using NoaLog.Core.Models;
using NoaLog.Core.Storage;

namespace NoaLog.App.Views;

public partial class MainWindow : Window
{
    private HaloIndicator? _haloIndicator;
    private TextBlock? _regionHotkeyLabel;
    private TextBlock? _captureHotkeyLabel;
    private TextBlock? _narratorHotkeyLabel;
    private ComboBox? _profileCombo;

    // Current profile (selected in combo)
    private Profile? _currentProfile;
#pragma warning disable CS0649 // Will be assigned when storage is initialized
    private SqliteStorage? _storage;
#pragma warning restore CS0649

    public MainWindow()
    {
        InitializeComponent();
    }

    protected override void OnOpened(EventArgs e)
    {
        base.OnOpened(e);

        // Find named controls
        _haloIndicator = this.FindControl<HaloIndicator>("HaloIndicator");
        _regionHotkeyLabel = this.FindControl<TextBlock>("RegionHotkeyLabel");
        _captureHotkeyLabel = this.FindControl<TextBlock>("CaptureHotkeyLabel");
        _narratorHotkeyLabel = this.FindControl<TextBlock>("NarratorHotkeyLabel");
        _profileCombo = this.FindControl<ComboBox>("ProfileCombo");

        UpdateHotkeyLabels();
    }

    // ── Hotkey Display ──

    private void UpdateHotkeyLabels()
    {
        bool isMac = RuntimeInformation.IsOSPlatform(OSPlatform.OSX);

        if (_regionHotkeyLabel != null)
            _regionHotkeyLabel.Text = isMac ? "⌃R" : "Ctrl+R";

        if (_captureHotkeyLabel != null)
            _captureHotkeyLabel.Text = isMac ? "⌃L" : "Ctrl+L";

        if (_narratorHotkeyLabel != null)
            _narratorHotkeyLabel.Text = isMac ? "⌃N" : "Ctrl+N";
    }

    // ── Keyboard Shortcuts ──

    protected override void OnKeyDown(KeyEventArgs e)
    {
        base.OnKeyDown(e);

        if (e.KeyModifiers.HasFlag(KeyModifiers.Control) && e.Key == Key.R)
        {
            e.Handled = true;
            OpenCaptureOverlay();
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
        // Region selection completed — results available in e.HeaderRect, e.BodyRect, e.NarratorRect
        // If editing a profile, apply selected regions to it
        if (_currentProfile != null)
        {
            if (e.HeaderRect is { } hr)
                _currentProfile.HeaderRect = new Rect((int)hr.X, (int)hr.Y, (int)hr.Width, (int)hr.Height);
            if (e.BodyRect is { } br)
                _currentProfile.BodyRect = new Rect((int)br.X, (int)br.Y, (int)br.Width, (int)br.Height);
            if (e.NarratorRect is { } nr)
                _currentProfile.NarratorRect = new Rect((int)nr.X, (int)nr.Y, (int)nr.Width, (int)nr.Height);
        }
    }

    // ── Button Handlers ──

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
            _currentProfile = newProfile;
            // Add to combo if available
            _profileCombo?.Items.Add(newProfile.Name);
            if (_profileCombo != null)
                _profileCombo.SelectedIndex = _profileCombo.Items.Count - 1;
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
            _currentProfile = updatedProfile;
        }
    }

    private void OnCaptureClick(object? sender, RoutedEventArgs e)
    {
        // Set HaloIndicator to Processing state (demo)
        if (_haloIndicator != null)
            _haloIndicator.State = HaloState.Processing;
    }
}
