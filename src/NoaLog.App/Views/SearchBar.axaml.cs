using System;
using System.Collections.Generic;
using Avalonia.Animation;
using Avalonia.Animation.Easings;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Styling;

namespace NoaLog.App.Views;

/// <summary>
/// 検索・置換バー UserControl。
/// 検索ロジック自体は持たず、イベントで外部に通知する。
/// </summary>
public partial class SearchBar : UserControl
{
    // --- コントロール参照 ---
    private TextBox? _searchInput;
    private TextBox? _replaceInput;
    private StackPanel? _replaceSection;
    private TextBlock? _matchCountLabel;
    private ToggleButton? _regexToggle;
    private Button? _nextMatchButton;
    private Button? _prevMatchButton;
    private Button? _closeButton;
    private Button? _replaceButton;
    private Button? _replaceAllButton;

    // --- 状態 ---
    private bool _isReplaceMode;
    private List<int> _matchIndices = new();
    private int _currentMatchIndex = -1;

    // --- イベント ---

    /// <summary>検索テキストまたは正規表現トグルが変更された時に発火</summary>
    public event EventHandler<SearchEventArgs>? SearchChanged;

    /// <summary>F3/Shift+F3でマッチ位置へのナビゲーションを要求する時に発火</summary>
    public event EventHandler<int>? NavigateToMatch;

    /// <summary>「置換」ボタン押下時に発火</summary>
    public event EventHandler<ReplaceEventArgs>? ReplaceRequested;

    /// <summary>「すべて置換」ボタン押下時に発火</summary>
    public event EventHandler<ReplaceEventArgs>? ReplaceAllRequested;

    /// <summary>検索バーを閉じた時に発火</summary>
    public event EventHandler? SearchClosed;

    // --- コンストラクタ ---

    public SearchBar()
    {
        InitializeComponent();
    }

    // --- 初期化 ---

    protected override void OnLoaded(RoutedEventArgs e)
    {
        base.OnLoaded(e);

        // FindControl でコントロール参照を取得
        _searchInput = this.FindControl<TextBox>("SearchInput");
        _replaceInput = this.FindControl<TextBox>("ReplaceInput");
        _replaceSection = this.FindControl<StackPanel>("ReplaceSection");
        _matchCountLabel = this.FindControl<TextBlock>("MatchCountLabel");
        _regexToggle = this.FindControl<ToggleButton>("RegexToggle");
        _nextMatchButton = this.FindControl<Button>("NextMatchButton");
        _prevMatchButton = this.FindControl<Button>("PrevMatchButton");
        _closeButton = this.FindControl<Button>("CloseButton");
        _replaceButton = this.FindControl<Button>("ReplaceButton");
        _replaceAllButton = this.FindControl<Button>("ReplaceAllButton");

        // イベントハンドラ登録
        if (_searchInput is not null)
        {
            _searchInput.TextChanged += OnSearchTextChanged;
        }

        if (_regexToggle is not null)
        {
            _regexToggle.IsCheckedChanged += OnRegexToggleChanged;
        }

        if (_nextMatchButton is not null)
        {
            _nextMatchButton.Click += OnNextMatchClick;
        }

        if (_prevMatchButton is not null)
        {
            _prevMatchButton.Click += OnPrevMatchClick;
        }

        if (_closeButton is not null)
        {
            _closeButton.Click += OnCloseClick;
        }

        if (_replaceButton is not null)
        {
            _replaceButton.Click += OnReplaceClick;
        }

        if (_replaceAllButton is not null)
        {
            _replaceAllButton.Click += OnReplaceAllClick;
        }
    }

    // --- キーボードショートカット ---

    protected override void OnKeyDown(KeyEventArgs e)
    {
        base.OnKeyDown(e);

        switch (e.Key)
        {
            case Key.Escape:
                Hide();
                e.Handled = true;
                break;

            case Key.F3 when e.KeyModifiers.HasFlag(KeyModifiers.Shift):
                // Shift+F3: 前の一致へ
                NavigatePrevious();
                e.Handled = true;
                break;

            case Key.F3:
                // F3: 次の一致へ
                NavigateNext();
                e.Handled = true;
                break;

            case Key.Enter:
                // Enter: 次の一致へ（検索フィールドにフォーカスがある場合）
                NavigateNext();
                e.Handled = true;
                break;
        }
    }

    // --- 公開メソッド ---

    /// <summary>
    /// 検索バーを表示し、検索フィールドにフォーカスを設定する。
    /// </summary>
    /// <param name="replaceMode">true の場合、置換セクションも表示する</param>
    public void Show(bool replaceMode)
    {
        _isReplaceMode = replaceMode;

        if (_replaceSection is not null)
        {
            _replaceSection.IsVisible = replaceMode;
        }

        IsVisible = true;

        // スライドインアニメーション
        var translateTransform = new TranslateTransform(0, -30);
        RenderTransform = translateTransform;
        Opacity = 0;

        var slideIn = new Animation
        {
            Duration = TimeSpan.FromMilliseconds(200),
            Easing = new CubicEaseOut(),
            Children =
            {
                new KeyFrame { Cue = new Cue(0), Setters = { new Setter(TranslateTransform.YProperty, -30.0) } },
                new KeyFrame { Cue = new Cue(1), Setters = { new Setter(TranslateTransform.YProperty, 0.0) } },
            }
        };
        slideIn.RunAsync(this);

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
        fadeIn.RunAsync(this);

        // 検索フィールドにフォーカスを設定し、テキストを全選択
        _searchInput?.Focus();
        _searchInput?.SelectAll();
    }

    /// <summary>
    /// 検索バーを非表示にし、状態をリセットする。
    /// </summary>
    public async void Hide()
    {
        var slideOut = new Animation
        {
            Duration = TimeSpan.FromMilliseconds(200),
            Easing = new CubicEaseIn(),
            FillMode = FillMode.Forward,
            Children =
            {
                new KeyFrame { Cue = new Cue(0), Setters = { new Setter(TranslateTransform.YProperty, 0.0) } },
                new KeyFrame { Cue = new Cue(1), Setters = { new Setter(TranslateTransform.YProperty, -30.0) } },
            }
        };
        var fadeOut = new Animation
        {
            Duration = TimeSpan.FromMilliseconds(200),
            Easing = new CubicEaseIn(),
            FillMode = FillMode.Forward,
            Children =
            {
                new KeyFrame { Cue = new Cue(0), Setters = { new Setter(OpacityProperty, 1.0) } },
                new KeyFrame { Cue = new Cue(1), Setters = { new Setter(OpacityProperty, 0.0) } },
            }
        };

        _ = slideOut.RunAsync(this);
        await fadeOut.RunAsync(this);

        IsVisible = false;
        Opacity = 1; // リセット
        RenderTransform = null;

        _matchIndices.Clear();
        _currentMatchIndex = -1;
        UpdateMatchCountDisplay();
        SearchClosed?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>
    /// マッチ数と現在位置の表示を更新する。
    /// </summary>
    /// <param name="count">総マッチ数</param>
    /// <param name="currentIndex">現在のマッチインデックス（0始まり、-1は未選択）</param>
    public void UpdateMatchCount(int count, int currentIndex)
    {
        _currentMatchIndex = currentIndex;

        // マッチインデックスリストを再構築（外部から設定される場合に対応）
        if (_matchIndices.Count != count)
        {
            _matchIndices.Clear();
            for (var i = 0; i < count; i++)
            {
                _matchIndices.Add(i);
            }
        }

        UpdateMatchCountDisplay();
    }

    // --- 内部メソッド ---

    /// <summary>マッチ数ラベルの表示を更新する</summary>
    private void UpdateMatchCountDisplay()
    {
        if (_matchCountLabel is null) return;

        if (_matchIndices.Count == 0)
        {
            var hasQuery = !string.IsNullOrEmpty(_searchInput?.Text);
            _matchCountLabel.Text = hasQuery ? "0/0" : "";
        }
        else
        {
            // 表示は1始まり
            _matchCountLabel.Text = $"{_currentMatchIndex + 1}/{_matchIndices.Count}";
        }
    }

    /// <summary>次の一致へ移動</summary>
    private void NavigateNext()
    {
        if (_matchIndices.Count == 0) return;

        _currentMatchIndex = (_currentMatchIndex + 1) % _matchIndices.Count;
        UpdateMatchCountDisplay();
        NavigateToMatch?.Invoke(this, _matchIndices[_currentMatchIndex]);
    }

    /// <summary>前の一致へ移動</summary>
    private void NavigatePrevious()
    {
        if (_matchIndices.Count == 0) return;

        _currentMatchIndex = (_currentMatchIndex - 1 + _matchIndices.Count) % _matchIndices.Count;
        UpdateMatchCountDisplay();
        NavigateToMatch?.Invoke(this, _matchIndices[_currentMatchIndex]);
    }

    /// <summary>現在の検索クエリと正規表現フラグを取得してSearchChangedイベントを発火</summary>
    private void RaiseSearchChanged()
    {
        var query = _searchInput?.Text ?? string.Empty;
        var isRegex = _regexToggle?.IsChecked ?? false;

        // 状態リセット
        _currentMatchIndex = -1;
        _matchIndices.Clear();
        UpdateMatchCountDisplay();

        SearchChanged?.Invoke(this, new SearchEventArgs(query, isRegex));
    }

    /// <summary>置換イベント引数を生成</summary>
    private ReplaceEventArgs CreateReplaceArgs()
    {
        var query = _searchInput?.Text ?? string.Empty;
        var replacement = _replaceInput?.Text ?? string.Empty;
        var isRegex = _regexToggle?.IsChecked ?? false;
        return new ReplaceEventArgs(query, replacement, isRegex);
    }

    // --- イベントハンドラ ---

    private void OnSearchTextChanged(object? sender, TextChangedEventArgs e)
    {
        RaiseSearchChanged();
    }

    private void OnRegexToggleChanged(object? sender, RoutedEventArgs e)
    {
        RaiseSearchChanged();
    }

    private void OnNextMatchClick(object? sender, RoutedEventArgs e)
    {
        NavigateNext();
    }

    private void OnPrevMatchClick(object? sender, RoutedEventArgs e)
    {
        NavigatePrevious();
    }

    private void OnCloseClick(object? sender, RoutedEventArgs e)
    {
        Hide();
    }

    private void OnReplaceClick(object? sender, RoutedEventArgs e)
    {
        ReplaceRequested?.Invoke(this, CreateReplaceArgs());
    }

    private void OnReplaceAllClick(object? sender, RoutedEventArgs e)
    {
        ReplaceAllRequested?.Invoke(this, CreateReplaceArgs());
    }
}

// --- イベント引数クラス ---

/// <summary>検索条件が変更された時のイベント引数</summary>
public class SearchEventArgs : EventArgs
{
    /// <summary>検索クエリ文字列</summary>
    public string Query { get; }

    /// <summary>正規表現モードかどうか</summary>
    public bool IsRegex { get; }

    public SearchEventArgs(string query, bool isRegex)
    {
        Query = query;
        IsRegex = isRegex;
    }
}

/// <summary>置換要求時のイベント引数</summary>
public class ReplaceEventArgs : EventArgs
{
    /// <summary>検索クエリ文字列</summary>
    public string Query { get; }

    /// <summary>置換文字列</summary>
    public string Replacement { get; }

    /// <summary>正規表現モードかどうか</summary>
    public bool IsRegex { get; }

    public ReplaceEventArgs(string query, string replacement, bool isRegex)
    {
        Query = query;
        Replacement = replacement;
        IsRegex = isRegex;
    }
}
