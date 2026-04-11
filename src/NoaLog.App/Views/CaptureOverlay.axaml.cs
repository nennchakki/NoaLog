using System;
using System.Globalization;
using System.IO;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.Media.Imaging;
using Avalonia.Threading;

namespace NoaLog.App.Views;

public partial class CaptureOverlay : Window
{
    // Selection stages
    private enum SelectionStage { TextArea, Narrator }

    private static readonly string[] StageInstructions =
    {
        "ステップ 1/2: テキスト領域を選択（名前+本文）— 余裕を持って大きめに選択してください",
        "ステップ 2/2: 語り部領域を選択 (任意 — S でスキップ) — 余裕を持って大きめに選択してください",
    };

    private static readonly string[] StageLabels =
    {
        "TextArea (名前+本文)",
        "Narrator (語り部)",
    };

    // State
    private SelectionStage _currentStage = SelectionStage.TextArea;
    private bool _isSelecting;
    private Point _startPoint;
    private Point _currentPoint;
    private Rect? _currentRect;

    // Confirmed regions
    private Rect? _textAreaRect;
    private Rect? _narratorRect;

    // Minimum selection size
    private const double MinSelectionSize = 10;

    // Selection blink animation
    private DispatcherTimer? _selectionBlinkTimer;
    private double _blinkPhase;
    private double _selectionOpacity = 1.0;

    // Screenshot background
    private Bitmap? _screenshotBitmap;

    // Confirm flash animation fields
    private DispatcherTimer? _confirmFlashTimer;
    private double _confirmFlashProgress;
    private Rect _confirmFlashRect;
    private bool _isConfirmFlashActive;

    // Colors / Brushes — ice-blue selection
    private static readonly Color OverlayBgColor = Color.FromArgb(77, 26, 39, 68); // #1A2744 @ 30%
    private static readonly Color SelectionBorderColor = Color.Parse("#7EC8E3");
    private static readonly Color SelectionFillColor = Color.FromArgb(51, 126, 200, 227); // #337EC8E3
    private static readonly IBrush ConfirmedBorderBrush = new SolidColorBrush(Color.Parse("#64C864"));
    private static readonly IBrush ConfirmedFillBrush = new SolidColorBrush(Color.FromArgb(26, 100, 200, 100));
    private static readonly IBrush InstructionBgBrush = new SolidColorBrush(Color.FromArgb(204, 26, 39, 68));
    private static readonly IBrush AccentIndicatorBrush = new SolidColorBrush(Color.Parse("#7EC8E3"));
    private static readonly IBrush HandleBorderBrush = new SolidColorBrush(Color.Parse("#7EC8E3"));
    private static readonly IBrush DimensionBgBrush = new SolidColorBrush(Color.FromArgb(200, 20, 30, 50));

    // Pens
    private static readonly IPen ConfirmedPen = new Pen(ConfirmedBorderBrush, 2);
    private static readonly IPen HandlePen = new Pen(HandleBorderBrush, 2);

    // Typeface
    private static readonly Typeface DefaultTypeface =
        new Typeface("Hiragino Sans, Segoe UI, sans-serif", FontStyle.Normal, FontWeight.Bold);

    private static readonly Typeface NormalTypeface =
        new Typeface("Hiragino Sans, Segoe UI, sans-serif", FontStyle.Normal, FontWeight.Normal);

    // Events
    public event EventHandler<RegionsSelectedEventArgs>? RegionsSelected;
    public event EventHandler? SelectionCancelled;

    public CaptureOverlay()
    {
        InitializeComponent();
        Cursor = new Cursor(StandardCursorType.Cross);
    }

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    protected override async void OnOpened(EventArgs e)
    {
        base.OnOpened(e);
        var screen = Screens.Primary;
        if (screen != null)
        {
            var scaling = screen.Scaling;
            // WorkingArea を使用（メニューバー・Dockを除いた領域）
            var workArea = screen.WorkingArea;
            Position = new PixelPoint(
                (int)(workArea.X / scaling),
                (int)(workArea.Y / scaling));
            Width = workArea.Width / scaling;
            Height = workArea.Height / scaling;
        }

        // オーバーレイを一時非表示にしてスクリーンショットを撮る
        Opacity = 0;
        await Task.Delay(200);

        var capture = App.ScreenCapture;
        if (capture != null && screen != null)
        {
            try
            {
                // WorkingArea の領域だけキャプチャ（メニューバー除外）
                var workArea = screen.WorkingArea;
                var rect = new NoaLog.Core.Models.Rect(
                    (int)workArea.X, (int)workArea.Y,
                    (int)workArea.Width, (int)workArea.Height);
                var imageData = await capture.CaptureRegionAsync(rect);
                if (imageData.Length > 0)
                {
                    using var ms = new MemoryStream(imageData);
                    _screenshotBitmap = new Bitmap(ms);
                }
            }
            catch { /* スクリーンショット失敗時は背景なしで続行 */ }
        }

        Opacity = 1;
        Activate();
        Focus();
        InvalidateVisual();
    }

    // ------------------------------------------------------------------
    // Pointer events
    // ------------------------------------------------------------------

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        if (e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
        {
            _isSelecting = true;
            _startPoint = e.GetPosition(this);
            _currentPoint = _startPoint;
            _currentRect = null;
            StartSelectionBlink();
            InvalidateVisual();
        }
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);
        if (!_isSelecting) return;

        _currentPoint = e.GetPosition(this);
        _currentRect = NormalizeRect(_startPoint, _currentPoint);
        InvalidateVisual();
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        if (!_isSelecting) return;

        _isSelecting = false;
        _currentPoint = e.GetPosition(this);

        var rect = NormalizeRect(_startPoint, _currentPoint);
        if (rect.Width >= MinSelectionSize && rect.Height >= MinSelectionSize)
        {
            _currentRect = rect;
        }
        else
        {
            _currentRect = null;
            StopSelectionBlink();
        }

        InvalidateVisual();
    }

    // ------------------------------------------------------------------
    // Keyboard
    // ------------------------------------------------------------------

    protected override void OnKeyDown(KeyEventArgs e)
    {
        base.OnKeyDown(e);
        switch (e.Key)
        {
            case Key.Return:
                ConfirmStage();
                break;
            case Key.Escape:
                Cancel();
                break;
            case Key.S:
                // Sキーでスキップ（Narrator段階ならスキップ完了、それ以外は無視）
                if (_currentStage == SelectionStage.Narrator)
                    SkipNarrator();
                break;
        }
    }

    // ------------------------------------------------------------------
    // Stage logic
    // ------------------------------------------------------------------

    private void ConfirmStage()
    {
        Console.Error.WriteLine($"[Overlay] ConfirmStage: stage={_currentStage}, currentRect={_currentRect}");
        if (!_currentRect.HasValue) return;

        StopSelectionBlink();
        StartConfirmFlash(_currentRect.Value);

        switch (_currentStage)
        {
            case SelectionStage.TextArea:
                _textAreaRect = _currentRect;
                _currentRect = null;
                _currentStage = SelectionStage.Narrator;
                break;

            case SelectionStage.Narrator:
                _narratorRect = _currentRect;
                _currentRect = null;
                CompleteSelection();
                return;
        }

        InvalidateVisual();
    }

    private void SkipNarrator()
    {
        _narratorRect = null;
        CompleteSelection();
    }

    private void CompleteSelection()
    {
        Console.Error.WriteLine($"[Overlay] CompleteSelection: TextArea={_textAreaRect}, Narrator={_narratorRect}");
        StopSelectionBlink();
        StopConfirmFlash();
        RegionsSelected?.Invoke(this, new RegionsSelectedEventArgs
        {
            TextAreaRect = _textAreaRect,
            NarratorRect = _narratorRect,
        });
        Close();
    }

    private void Cancel()
    {
        StopSelectionBlink();
        StopConfirmFlash();
        SelectionCancelled?.Invoke(this, EventArgs.Empty);
        Close();
    }

    protected override void OnClosed(EventArgs e)
    {
        base.OnClosed(e);
        _screenshotBitmap?.Dispose();
        _screenshotBitmap = null;
    }

    // ------------------------------------------------------------------
    // Rendering
    // ------------------------------------------------------------------

    public override void Render(DrawingContext context)
    {
        base.Render(context);

        var bounds = new Rect(0, 0, Bounds.Width, Bounds.Height);

        // 0. スクリーンショット背景を描画
        if (_screenshotBitmap != null)
        {
            context.DrawImage(_screenshotBitmap,
                new Rect(0, 0, Bounds.Width, Bounds.Height));
        }

        // 1. Semi-transparent overlay background
        context.DrawRectangle(new SolidColorBrush(OverlayBgColor), null, bounds);

        // 2. Confirmed regions (green solid border)
        DrawConfirmedRegion(context, _textAreaRect, StageLabels[0]);
        DrawConfirmedRegion(context, _narratorRect, StageLabels[1]);

        // 3. Current selection (ice-blue solid 1px with blink)
        if (_currentRect.HasValue)
        {
            DrawSelection(context, _currentRect.Value);
        }

        // 4. Confirm flash effect (opacity 1 -> 0, 300ms)
        if (_isConfirmFlashActive)
        {
            double flashOpacity = Math.Max(0.0, 1.0 - _confirmFlashProgress);
            byte borderAlpha = (byte)(255 * flashOpacity);
            byte fillAlpha = (byte)(80 * flashOpacity);
            var flashBorderColor = Color.FromArgb(borderAlpha,
                SelectionBorderColor.R, SelectionBorderColor.G, SelectionBorderColor.B);
            var flashFillColor = Color.FromArgb(fillAlpha,
                SelectionBorderColor.R, SelectionBorderColor.G, SelectionBorderColor.B);
            var flashPen = new Pen(new SolidColorBrush(flashBorderColor), 2);
            context.DrawRectangle(new SolidColorBrush(flashFillColor), flashPen, _confirmFlashRect);
        }

        // 5. Instruction banner at top center
        DrawInstruction(context);
    }

    // ------------------------------------------------------------------
    // Drawing helpers
    // ------------------------------------------------------------------

    private void DrawSelection(DrawingContext context, Rect rect)
    {
        // Apply blink opacity to selection brushes
        byte borderAlpha = (byte)(SelectionBorderColor.A * _selectionOpacity);
        byte fillAlpha = (byte)(SelectionFillColor.A * _selectionOpacity);
        var borderColor = Color.FromArgb(borderAlpha,
            SelectionBorderColor.R, SelectionBorderColor.G, SelectionBorderColor.B);
        var fillColor = Color.FromArgb(fillAlpha,
            SelectionFillColor.R, SelectionFillColor.G, SelectionFillColor.B);

        var fillBrush = new SolidColorBrush(fillColor);
        var borderPen = new Pen(new SolidColorBrush(borderColor), 1);

        // Fill
        context.DrawRectangle(fillBrush, null, rect);
        // Solid border (1px ice-blue)
        context.DrawRectangle(null, borderPen, rect);
        // Corner handles
        DrawCornerHandles(context, rect);
        // Dimension label
        DrawDimensionLabel(context, rect);
    }

    private void DrawCornerHandles(DrawingContext context, Rect rect)
    {
        const double size = 8;
        const double half = size / 2;

        var corners = new[]
        {
            rect.TopLeft,
            rect.TopRight,
            rect.BottomLeft,
            rect.BottomRight,
        };

        foreach (var corner in corners)
        {
            var handleRect = new Rect(corner.X - half, corner.Y - half, size, size);
            context.DrawRectangle(Brushes.White, HandlePen, handleRect);
        }
    }

    private void DrawDimensionLabel(DrawingContext context, Rect rect)
    {
        var label = $"{(int)rect.Width} × {(int)rect.Height}";
        var ft = new FormattedText(
            label,
            CultureInfo.CurrentCulture,
            FlowDirection.LeftToRight,
            DefaultTypeface,
            12,
            Brushes.White);

        var padding = 6.0;
        var bgWidth = ft.Width + padding * 2;
        var bgHeight = ft.Height + padding * 2;
        var bgX = rect.X + (rect.Width - bgWidth) / 2;
        var bgY = rect.Bottom + 6;

        // Clamp to screen
        if (bgY + bgHeight > Bounds.Height)
            bgY = rect.Top - bgHeight - 6;

        var bgRect = new Rect(bgX, bgY, bgWidth, bgHeight);
        context.DrawRectangle(DimensionBgBrush, null, bgRect, 4, 4);

        var textOrigin = new Point(bgX + padding, bgY + padding);
        context.DrawText(ft, textOrigin);
    }

    private void DrawConfirmedRegion(DrawingContext context, Rect? rect, string label)
    {
        if (!rect.HasValue) return;

        var r = rect.Value;

        // Subtle fill
        context.DrawRectangle(ConfirmedFillBrush, null, r);
        // Solid green border
        context.DrawRectangle(null, ConfirmedPen, r);

        // Label at top-left of the region
        var ft = new FormattedText(
            label,
            CultureInfo.CurrentCulture,
            FlowDirection.LeftToRight,
            NormalTypeface,
            11,
            Brushes.White);

        var padding = 4.0;
        var bgWidth = ft.Width + padding * 2;
        var bgHeight = ft.Height + padding * 2;
        var bgX = r.X;
        var bgY = r.Y - bgHeight - 2;

        // If no room above, draw inside top
        if (bgY < 0)
            bgY = r.Y + 2;

        var bgRect = new Rect(bgX, bgY, bgWidth, bgHeight);
        context.DrawRectangle(new SolidColorBrush(Color.FromArgb(200, 30, 80, 30)), null, bgRect, 3, 3);
        context.DrawText(ft, new Point(bgX + padding, bgY + padding));
    }

    private void DrawInstruction(DrawingContext context)
    {
        var instruction = StageInstructions[(int)_currentStage];
        var subtext = _currentStage == SelectionStage.Narrator
            ? "領域を選択して Enter で確定 / S でスキップ / Esc でキャンセル"
            : "領域を選択して Enter で確定 / Esc でキャンセル";

        var ftMain = new FormattedText(
            instruction,
            CultureInfo.CurrentCulture,
            FlowDirection.LeftToRight,
            DefaultTypeface,
            14,
            Brushes.White);

        var ftSub = new FormattedText(
            subtext,
            CultureInfo.CurrentCulture,
            FlowDirection.LeftToRight,
            NormalTypeface,
            12,
            new SolidColorBrush(Color.FromArgb(180, 255, 255, 255)));

        var indicatorWidth = 4.0;
        var paddingH = 16.0;
        var paddingV = 10.0;
        var gap = 4.0;

        var contentWidth = Math.Max(ftMain.Width, ftSub.Width);
        var totalWidth = indicatorWidth + paddingH + contentWidth + paddingH;
        var totalHeight = paddingV + ftMain.Height + gap + ftSub.Height + paddingV;

        var x = (Bounds.Width - totalWidth) / 2;
        var y = 40;

        // Background
        var bgRect = new Rect(x, y, totalWidth, totalHeight);
        context.DrawRectangle(InstructionBgBrush, null, bgRect, 6, 6);

        // Left accent indicator
        var indicatorRect = new Rect(x, y, indicatorWidth, totalHeight);
        context.DrawRectangle(AccentIndicatorBrush, null, indicatorRect, 3, 0);

        // Main text
        var textX = x + indicatorWidth + paddingH;
        var textY = y + paddingV;
        context.DrawText(ftMain, new Point(textX, textY));

        // Sub text
        context.DrawText(ftSub, new Point(textX, textY + ftMain.Height + gap));
    }

    // ------------------------------------------------------------------
    // Selection blink animation — opacity 0.6 <-> 1.0, 1s cycle
    // ------------------------------------------------------------------

    private void StartSelectionBlink()
    {
        StopSelectionBlink();
        _blinkPhase = 0;
        _selectionOpacity = 1.0;
        _selectionBlinkTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(16) };
        _selectionBlinkTimer.Tick += OnBlinkTimerTick;
        _selectionBlinkTimer.Start();
    }

    private void OnBlinkTimerTick(object? sender, EventArgs e)
    {
        _blinkPhase += 0.016;
        // sin wave: opacity oscillates 0.6 ~ 1.0 with 1s cycle
        _selectionOpacity = 0.8 + 0.2 * Math.Sin(2 * Math.PI * _blinkPhase);
        InvalidateVisual();
    }

    private void StopSelectionBlink()
    {
        if (_selectionBlinkTimer != null)
        {
            _selectionBlinkTimer.Stop();
            _selectionBlinkTimer.Tick -= OnBlinkTimerTick;
            _selectionBlinkTimer = null;
        }
        _selectionOpacity = 1.0;
    }

    // ------------------------------------------------------------------
    // Confirm flash animation — opacity 1 -> 0, 300ms
    // ------------------------------------------------------------------

    private void StartConfirmFlash(Rect rect)
    {
        StopConfirmFlash();
        _confirmFlashRect = rect;
        _confirmFlashProgress = 0.0;
        _isConfirmFlashActive = true;
        _confirmFlashTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(16) };
        _confirmFlashTimer.Tick += OnConfirmFlashTick;
        _confirmFlashTimer.Start();
    }

    private void OnConfirmFlashTick(object? sender, EventArgs e)
    {
        _confirmFlashProgress += 16.0 / 300.0;
        if (_confirmFlashProgress >= 1.0)
        {
            StopConfirmFlash();
        }
        InvalidateVisual();
    }

    private void StopConfirmFlash()
    {
        if (_confirmFlashTimer != null)
        {
            _confirmFlashTimer.Stop();
            _confirmFlashTimer.Tick -= OnConfirmFlashTick;
            _confirmFlashTimer = null;
        }
        _isConfirmFlashActive = false;
        _confirmFlashProgress = 0.0;
    }

    // ------------------------------------------------------------------
    // Utility
    // ------------------------------------------------------------------

    private static Rect NormalizeRect(Point a, Point b)
    {
        var x = Math.Min(a.X, b.X);
        var y = Math.Min(a.Y, b.Y);
        var w = Math.Abs(a.X - b.X);
        var h = Math.Abs(a.Y - b.Y);
        return new Rect(x, y, w, h);
    }
}

public class RegionsSelectedEventArgs : EventArgs
{
    public Rect? TextAreaRect { get; init; }
    public Rect? NarratorRect { get; init; }
}
