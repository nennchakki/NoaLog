using System;
using Avalonia;
using Avalonia.Animation;
using Avalonia.Animation.Easings;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Styling;

namespace NoaLog.App.Controls;

public partial class LogCard : UserControl
{
    // --- Styled / Direct Properties ---

    public static readonly StyledProperty<string> EntryIdProperty =
        AvaloniaProperty.Register<LogCard, string>(nameof(EntryId), string.Empty);

    public static readonly StyledProperty<string> SpeakerNameTextProperty =
        AvaloniaProperty.Register<LogCard, string>(nameof(SpeakerNameText), string.Empty);

    public static readonly StyledProperty<string> OrgTextProperty =
        AvaloniaProperty.Register<LogCard, string>(nameof(OrgText), string.Empty);

    public static readonly StyledProperty<string> BodyTextProperty =
        AvaloniaProperty.Register<LogCard, string>(nameof(BodyText), string.Empty);

    public static readonly StyledProperty<string> TimestampTextProperty =
        AvaloniaProperty.Register<LogCard, string>(nameof(TimestampText), string.Empty);

    public static readonly StyledProperty<int> IndexNumberProperty =
        AvaloniaProperty.Register<LogCard, int>(nameof(IndexNumber), 0);

    public static readonly StyledProperty<bool> IsEditedProperty =
        AvaloniaProperty.Register<LogCard, bool>(nameof(IsEdited), false);

    public static readonly StyledProperty<bool> IsNarrationProperty =
        AvaloniaProperty.Register<LogCard, bool>(nameof(IsNarration), false);

    public static readonly StyledProperty<bool> LowConfidenceProperty =
        AvaloniaProperty.Register<LogCard, bool>(nameof(LowConfidence), false);

    public static readonly StyledProperty<bool> IsCardSelectedProperty =
        AvaloniaProperty.Register<LogCard, bool>(nameof(IsCardSelected), false);

    // --- CLR wrappers ---

    public string EntryId
    {
        get => GetValue(EntryIdProperty);
        set => SetValue(EntryIdProperty, value);
    }

    public string SpeakerNameText
    {
        get => GetValue(SpeakerNameTextProperty);
        set => SetValue(SpeakerNameTextProperty, value);
    }

    public string OrgText
    {
        get => GetValue(OrgTextProperty);
        set => SetValue(OrgTextProperty, value);
    }

    public string BodyText
    {
        get => GetValue(BodyTextProperty);
        set => SetValue(BodyTextProperty, value);
    }

    public string TimestampText
    {
        get => GetValue(TimestampTextProperty);
        set => SetValue(TimestampTextProperty, value);
    }

    public int IndexNumber
    {
        get => GetValue(IndexNumberProperty);
        set => SetValue(IndexNumberProperty, value);
    }

    public bool IsEdited
    {
        get => GetValue(IsEditedProperty);
        set => SetValue(IsEditedProperty, value);
    }

    public bool IsNarration
    {
        get => GetValue(IsNarrationProperty);
        set => SetValue(IsNarrationProperty, value);
    }

    public bool LowConfidence
    {
        get => GetValue(LowConfidenceProperty);
        set => SetValue(LowConfidenceProperty, value);
    }

    public bool IsCardSelected
    {
        get => GetValue(IsCardSelectedProperty);
        set => SetValue(IsCardSelectedProperty, value);
    }

    // --- Events ---

    public static readonly RoutedEvent<RoutedEventArgs> CardClickedEvent =
        RoutedEvent.Register<LogCard, RoutedEventArgs>(nameof(CardClicked), RoutingStrategies.Bubble);

    public event EventHandler<RoutedEventArgs>? CardClicked
    {
        add => AddHandler(CardClickedEvent, value);
        remove => RemoveHandler(CardClickedEvent, value);
    }

    // --- Private references ---
    private Border? _cardBorder;
    private TextBlock? _speakerName;
    private TextBlock? _orgName;
    private TextBlock? _indexLabel;
    private TextBlock? _bodyPreview;
    private TextBlock? _timestamp;
    private Border? _editedBadge;
    private Border? _narrationBadge;
    private Border? _lowConfBadge;
    private CheckBox? _selectCheckBox;
    private bool _suppressCheckBoxSync;

    // --- Brushes ---
    private static readonly IBrush NormalBackground = SolidColorBrush.Parse("#FFFFFF");
    private static readonly IBrush HoverBackground = SolidColorBrush.Parse("#F0F4F8");
    private static readonly IBrush SelectedBackground = SolidColorBrush.Parse("#E8F4FB");
    private static readonly IBrush SelectedBorderBrush = SolidColorBrush.Parse("#7EC8E3");
    private static readonly IBrush TransparentBrush = Brushes.Transparent;

    public LogCard()
    {
        InitializeComponent();
    }

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);

        _cardBorder = this.FindControl<Border>("CardBorder");
        _speakerName = this.FindControl<TextBlock>("SpeakerName");
        _orgName = this.FindControl<TextBlock>("OrgName");
        _indexLabel = this.FindControl<TextBlock>("IndexLabel");
        _bodyPreview = this.FindControl<TextBlock>("BodyPreview");
        _timestamp = this.FindControl<TextBlock>("Timestamp");
        _editedBadge = this.FindControl<Border>("EditedBadge");
        _narrationBadge = this.FindControl<Border>("NarrationBadge");
        _lowConfBadge = this.FindControl<Border>("LowConfBadge");
        _selectCheckBox = this.FindControl<CheckBox>("SelectCheckBox");

        // CheckBox連動
        if (_selectCheckBox != null)
        {
            _selectCheckBox.IsCheckedChanged += (_, _) =>
            {
                if (_suppressCheckBoxSync) return;
                IsCardSelected = _selectCheckBox.IsChecked == true;
                RaiseEvent(new RoutedEventArgs(CardClickedEvent));
            };
        }

        ApplyPropertyValues();
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);

        if (change.Property == SpeakerNameTextProperty)
        {
            if (_speakerName is not null)
                _speakerName.Text = SpeakerNameText;
        }
        else if (change.Property == OrgTextProperty)
        {
            if (_orgName is not null)
                _orgName.Text = OrgText;
        }
        else if (change.Property == BodyTextProperty)
        {
            if (_bodyPreview is not null)
                _bodyPreview.Text = BodyText;
        }
        else if (change.Property == TimestampTextProperty)
        {
            if (_timestamp is not null)
                _timestamp.Text = TimestampText;
        }
        else if (change.Property == IndexNumberProperty)
        {
            if (_indexLabel is not null)
                _indexLabel.Text = $"#{IndexNumber}";
        }
        else if (change.Property == IsEditedProperty)
        {
            if (_editedBadge is not null)
                _editedBadge.IsVisible = IsEdited;
        }
        else if (change.Property == IsNarrationProperty)
        {
            if (_narrationBadge is not null)
                _narrationBadge.IsVisible = IsNarration;
        }
        else if (change.Property == LowConfidenceProperty)
        {
            if (_lowConfBadge is not null)
                _lowConfBadge.IsVisible = LowConfidence;
        }
        else if (change.Property == IsCardSelectedProperty)
        {
            ApplySelectionVisual();
        }
    }

    // --- Hover handlers ---

    protected override void OnPointerEntered(PointerEventArgs e)
    {
        base.OnPointerEntered(e);

        if (!IsCardSelected && _cardBorder is not null)
        {
            _cardBorder.Background = HoverBackground;
        }
    }

    protected override void OnPointerExited(PointerEventArgs e)
    {
        base.OnPointerExited(e);

        if (!IsCardSelected && _cardBorder is not null)
        {
            _cardBorder.Background = NormalBackground;
        }
    }

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        RaiseEvent(new RoutedEventArgs(CardClickedEvent));
    }

    // --- Helpers ---

    private void ApplyPropertyValues()
    {
        if (_speakerName is not null)
            _speakerName.Text = SpeakerNameText;

        if (_orgName is not null)
            _orgName.Text = OrgText;

        if (_bodyPreview is not null)
            _bodyPreview.Text = BodyText;

        if (_timestamp is not null)
            _timestamp.Text = TimestampText;

        if (_indexLabel is not null)
            _indexLabel.Text = $"#{IndexNumber}";

        if (_editedBadge is not null)
            _editedBadge.IsVisible = IsEdited;

        if (_narrationBadge is not null)
            _narrationBadge.IsVisible = IsNarration;

        if (_lowConfBadge is not null)
            _lowConfBadge.IsVisible = LowConfidence;

        ApplySelectionVisual();
    }

    private void ApplySelectionVisual()
    {
        if (_cardBorder is null) return;

        if (IsCardSelected)
        {
            _cardBorder.Background = SelectedBackground;
            _cardBorder.BorderBrush = SelectedBorderBrush;
        }
        else
        {
            _cardBorder.Background = NormalBackground;
            _cardBorder.BorderBrush = TransparentBrush;
        }

        // CheckBox同期（無限ループ防止）
        if (_selectCheckBox != null)
        {
            _suppressCheckBoxSync = true;
            _selectCheckBox.IsChecked = IsCardSelected;
            _suppressCheckBoxSync = false;
        }
    }
}
