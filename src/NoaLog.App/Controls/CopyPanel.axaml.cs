using System;
using System.Windows.Input;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace NoaLog.App.Controls;

public partial class CopyPanel : UserControl
{
    // --- Styled Properties ---

    public static readonly StyledProperty<string> SelectedFormatProperty =
        AvaloniaProperty.Register<CopyPanel, string>(nameof(SelectedFormat), "plain");

    public string SelectedFormat
    {
        get => GetValue(SelectedFormatProperty);
        set => SetValue(SelectedFormatProperty, value);
    }

    public static readonly StyledProperty<ICommand?> CopyCommandProperty =
        AvaloniaProperty.Register<CopyPanel, ICommand?>(nameof(CopyCommand));

    public ICommand? CopyCommand
    {
        get => GetValue(CopyCommandProperty);
        set => SetValue(CopyCommandProperty, value);
    }

    public static readonly StyledProperty<ICommand?> ExportCommandProperty =
        AvaloniaProperty.Register<CopyPanel, ICommand?>(nameof(ExportCommand));

    public ICommand? ExportCommand
    {
        get => GetValue(ExportCommandProperty);
        set => SetValue(ExportCommandProperty, value);
    }

    // --- Events ---

    public event EventHandler? CopyRequested;
    public event EventHandler? ExportRequested;

    // --- Controls ---

    private RadioButton? _formatPlain;
    private RadioButton? _formatMarkdown;
    private RadioButton? _formatJson;
    private Button? _copyButton;
    private Button? _exportButton;

    public CopyPanel()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);

        _formatPlain = this.FindControl<RadioButton>("FormatPlain");
        _formatMarkdown = this.FindControl<RadioButton>("FormatMarkdown");
        _formatJson = this.FindControl<RadioButton>("FormatJson");
        _copyButton = this.FindControl<Button>("CopyButton");
        _exportButton = this.FindControl<Button>("ExportButton");

        // Format toggle handlers
        if (_formatPlain is not null)
            _formatPlain.IsCheckedChanged += OnFormatChanged;

        if (_formatMarkdown is not null)
            _formatMarkdown.IsCheckedChanged += OnFormatChanged;

        if (_formatJson is not null)
            _formatJson.IsCheckedChanged += OnFormatChanged;

        // Button handlers
        if (_copyButton is not null)
            _copyButton.Click += OnCopyClicked;

        if (_exportButton is not null)
            _exportButton.Click += OnExportClicked;
    }

    private void OnFormatChanged(object? sender, RoutedEventArgs e)
    {
        if (_formatPlain?.IsChecked == true)
            SelectedFormat = "plain";
        else if (_formatMarkdown?.IsChecked == true)
            SelectedFormat = "markdown";
        else if (_formatJson?.IsChecked == true)
            SelectedFormat = "json";
    }

    private void OnCopyClicked(object? sender, RoutedEventArgs e)
    {
        CopyRequested?.Invoke(this, EventArgs.Empty);

        if (CopyCommand?.CanExecute(SelectedFormat) == true)
            CopyCommand.Execute(SelectedFormat);
    }

    private void OnExportClicked(object? sender, RoutedEventArgs e)
    {
        ExportRequested?.Invoke(this, EventArgs.Empty);

        if (ExportCommand?.CanExecute(SelectedFormat) == true)
            ExportCommand.Execute(SelectedFormat);
    }
}
