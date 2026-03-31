using System;
using Avalonia;
using Avalonia.Animation;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Styling;
using NoaLog.Core.Models;

namespace NoaLog.App.Controls;

public partial class DetailPanel : UserControl
{
    // --- Styled Properties ---

    public static readonly StyledProperty<bool> IsEditingProperty =
        AvaloniaProperty.Register<DetailPanel, bool>(nameof(IsEditing), false);

    public bool IsEditing
    {
        get => GetValue(IsEditingProperty);
        set => SetValue(IsEditingProperty, value);
    }

    // --- Private state ---

    private LogEntry? _selectedEntry;

    public LogEntry? SelectedEntry => _selectedEntry;

    // --- Controls ---

    private TextBlock? _emptyState;
    private DockPanel? _detailContent;
    private TextBlock? _headerSpeakerName;
    private TextBlock? _headerOrganization;
    private TextBlock? _headerTimestamp;
    private TextBlock? _editSpeakerLabel;
    private TextBox? _editSpeakerInput;
    private TextBlock? _editOrgLabel;
    private TextBox? _editOrgInput;
    private TextBox? _editBodyText;
    private TextBlock? _rawText;
    private TextBlock? _diffText;
    private Button? _undoButton;
    private Button? _redoButton;

    public DetailPanel()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);

        _emptyState = this.FindControl<TextBlock>("EmptyState");
        _detailContent = this.FindControl<DockPanel>("DetailContent");
        _headerSpeakerName = this.FindControl<TextBlock>("HeaderSpeakerName");
        _headerOrganization = this.FindControl<TextBlock>("HeaderOrganization");
        _headerTimestamp = this.FindControl<TextBlock>("HeaderTimestamp");
        _editSpeakerLabel = this.FindControl<TextBlock>("EditSpeakerLabel");
        _editSpeakerInput = this.FindControl<TextBox>("EditSpeakerInput");
        _editOrgLabel = this.FindControl<TextBlock>("EditOrgLabel");
        _editOrgInput = this.FindControl<TextBox>("EditOrgInput");
        _editBodyText = this.FindControl<TextBox>("EditBodyText");
        _rawText = this.FindControl<TextBlock>("RawText");
        _diffText = this.FindControl<TextBlock>("DiffText");
        _undoButton = this.FindControl<Button>("UndoButton");
        _redoButton = this.FindControl<Button>("RedoButton");

        // Double-click to edit speaker name
        if (_editSpeakerLabel is not null)
            _editSpeakerLabel.DoubleTapped += OnSpeakerLabelDoubleTapped;

        // Double-click to edit organization
        if (_editOrgLabel is not null)
            _editOrgLabel.DoubleTapped += OnOrgLabelDoubleTapped;

        // Commit on lost focus
        if (_editSpeakerInput is not null)
            _editSpeakerInput.LostFocus += OnSpeakerInputLostFocus;

        if (_editOrgInput is not null)
            _editOrgInput.LostFocus += OnOrgInputLostFocus;

        ApplyVisualState();
    }

    // --- Public methods ---

    public void SetEntry(LogEntry entry)
    {
        _selectedEntry = entry;
        IsEditing = false;
        ApplyVisualState();
        PopulateFields();
    }

    public void ClearEntry()
    {
        _selectedEntry = null;
        IsEditing = false;
        ApplyVisualState();
    }

    // --- Event handlers ---

    private void OnSpeakerLabelDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (_editSpeakerLabel is null || _editSpeakerInput is null) return;

        _editSpeakerInput.Text = _editSpeakerLabel.Text;
        _editSpeakerLabel.IsVisible = false;
        _editSpeakerInput.IsVisible = true;
        _editSpeakerInput.Focus();
        IsEditing = true;
    }

    private void OnOrgLabelDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (_editOrgLabel is null || _editOrgInput is null) return;

        _editOrgInput.Text = _editOrgLabel.Text;
        _editOrgLabel.IsVisible = false;
        _editOrgInput.IsVisible = true;
        _editOrgInput.Focus();
        IsEditing = true;
    }

    private void OnSpeakerInputLostFocus(object? sender, RoutedEventArgs e)
    {
        if (_editSpeakerLabel is null || _editSpeakerInput is null) return;

        _editSpeakerLabel.Text = _editSpeakerInput.Text ?? "";
        _editSpeakerLabel.IsVisible = true;
        _editSpeakerInput.IsVisible = false;

        if (_selectedEntry is not null)
            _selectedEntry.EditedSpeakerName = _editSpeakerInput.Text;

        UpdateHeader();
    }

    private void OnOrgInputLostFocus(object? sender, RoutedEventArgs e)
    {
        if (_editOrgLabel is null || _editOrgInput is null) return;

        _editOrgLabel.Text = _editOrgInput.Text ?? "";
        _editOrgLabel.IsVisible = true;
        _editOrgInput.IsVisible = false;

        if (_selectedEntry is not null)
            _selectedEntry.EditedSpeakerOrg = _editOrgInput.Text;

        UpdateHeader();
    }

    // --- Helpers ---

    private void ApplyVisualState()
    {
        bool hasEntry = _selectedEntry is not null;

        if (_emptyState is not null)
            _emptyState.IsVisible = !hasEntry;

        if (_detailContent is not null)
            _detailContent.IsVisible = hasEntry;
    }

    private void PopulateFields()
    {
        if (_selectedEntry is null) return;

        // Header
        UpdateHeader();

        if (_headerTimestamp is not null)
            _headerTimestamp.Text = _selectedEntry.Timestamp.ToString("yyyy-MM-dd HH:mm:ss");

        // Edited tab
        if (_editSpeakerLabel is not null)
            _editSpeakerLabel.Text = _selectedEntry.DisplayName;

        if (_editOrgLabel is not null)
            _editOrgLabel.Text = _selectedEntry.DisplayOrg;

        if (_editBodyText is not null)
            _editBodyText.Text = _selectedEntry.DisplayBody;

        // Raw tab
        if (_rawText is not null)
        {
            var rawContent = string.IsNullOrEmpty(_selectedEntry.RawHeader)
                ? _selectedEntry.RawBody
                : $"{_selectedEntry.RawHeader}\n{_selectedEntry.RawBody}";
            _rawText.Text = rawContent;
        }

        // Diff tab
        if (_diffText is not null)
            _diffText.Text = BuildSimpleDiff();

        // Reset inline edit states
        if (_editSpeakerLabel is not null) _editSpeakerLabel.IsVisible = true;
        if (_editSpeakerInput is not null) _editSpeakerInput.IsVisible = false;
        if (_editOrgLabel is not null) _editOrgLabel.IsVisible = true;
        if (_editOrgInput is not null) _editOrgInput.IsVisible = false;
    }

    private void UpdateHeader()
    {
        if (_selectedEntry is null) return;

        if (_headerSpeakerName is not null)
            _headerSpeakerName.Text = _selectedEntry.DisplayName;

        if (_headerOrganization is not null)
            _headerOrganization.Text = _selectedEntry.DisplayOrg;
    }

    private string BuildSimpleDiff()
    {
        if (_selectedEntry is null) return "";

        var lines = new System.Text.StringBuilder();

        if (_selectedEntry.EditedSpeakerName is not null &&
            _selectedEntry.EditedSpeakerName != _selectedEntry.SpeakerName)
        {
            lines.AppendLine($"- Speaker: {_selectedEntry.SpeakerName}");
            lines.AppendLine($"+ Speaker: {_selectedEntry.EditedSpeakerName}");
        }

        if (_selectedEntry.EditedSpeakerOrg is not null &&
            _selectedEntry.EditedSpeakerOrg != _selectedEntry.SpeakerOrg)
        {
            lines.AppendLine($"- Org: {_selectedEntry.SpeakerOrg}");
            lines.AppendLine($"+ Org: {_selectedEntry.EditedSpeakerOrg}");
        }

        if (_selectedEntry.EditedBodyText is not null &&
            _selectedEntry.EditedBodyText != _selectedEntry.BodyText)
        {
            lines.AppendLine($"- Body: {_selectedEntry.BodyText}");
            lines.AppendLine($"+ Body: {_selectedEntry.EditedBodyText}");
        }

        return lines.Length > 0 ? lines.ToString() : "(no changes)";
    }
}
