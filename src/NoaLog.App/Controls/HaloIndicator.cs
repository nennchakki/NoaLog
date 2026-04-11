using System;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Threading;

namespace NoaLog.App.Controls;

/// <summary>
/// Animated halo indicator control showing capture state with concentric rings.
/// Fixed size: 48x48px with 12px margin for clipping prevention (total 60x60).
/// </summary>
public enum HaloState
{
    Idle,
    Processing,
    Success,
    Failed,
}

public class HaloIndicator : Control
{
    public static readonly StyledProperty<HaloState> StateProperty =
        AvaloniaProperty.Register<HaloIndicator, HaloState>(nameof(State), HaloState.Idle);

    private static readonly Color AccentColor = Color.Parse("#7EC8E3");
    private static readonly Color AccentLightColor = Color.Parse("#B8E0F0");
    private static readonly Color WhiteColor = Colors.White;

    private const double DefaultSize = 48.0;
    private const double ClipMargin = 12.0;
    private const double TotalSize = DefaultSize + ClipMargin; // 60
    private const double OuterRingWidth = 4.0;
    private const double RotationDurationMs = 2000.0;
    private const double PulseDurationMs = 600.0;
    private const double FadeDurationMs = 480.0; // 0.8 * 600
    private const int TimerIntervalMs = 16; // ~60fps

    private DispatcherTimer? _timer;
    private double _rotationAngle;
    private double _pulseScale = 1.0;
    private double _fadeOpacity = 1.0;
    private double _animationElapsed;

    public HaloState State
    {
        get => GetValue(StateProperty);
        set => SetValue(StateProperty, value);
    }

    static HaloIndicator()
    {
        AffectsRender<HaloIndicator>(StateProperty);
    }

    public HaloIndicator()
    {
        Width = TotalSize;
        Height = TotalSize;
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);

        if (change.Property == StateProperty)
        {
            OnStateChanged((HaloState)change.NewValue!);
        }
    }

    private void OnStateChanged(HaloState newState)
    {
        // Reset animation state
        _rotationAngle = 0;
        _pulseScale = 1.0;
        _fadeOpacity = 1.0;
        _animationElapsed = 0;

        if (newState == HaloState.Idle)
        {
            StopTimer();
        }
        else
        {
            StartTimer();
        }

        InvalidateVisual();
    }

    private void StartTimer()
    {
        if (_timer != null) return;

        _timer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(TimerIntervalMs),
        };
        _timer.Tick += OnTimerTick;
        _timer.Start();
    }

    private void StopTimer()
    {
        if (_timer == null) return;

        _timer.Stop();
        _timer.Tick -= OnTimerTick;
        _timer = null;
    }

    private void OnTimerTick(object? sender, EventArgs e)
    {
        var state = State;

        switch (state)
        {
            case HaloState.Processing:
                // 360 degrees per RotationDurationMs
                _rotationAngle += 360.0 * TimerIntervalMs / RotationDurationMs;
                if (_rotationAngle >= 360.0)
                    _rotationAngle -= 360.0;
                break;

            case HaloState.Success:
                _animationElapsed += TimerIntervalMs;
                double pulseHalf = PulseDurationMs / 2.0;
                if (_animationElapsed <= pulseHalf)
                {
                    // Scale up: 1.0 -> 1.2 with OutQuad easing
                    double t = _animationElapsed / pulseHalf;
                    double eased = EaseOutQuad(t);
                    _pulseScale = 1.0 + 0.2 * eased;
                }
                else if (_animationElapsed <= PulseDurationMs)
                {
                    // Scale down: 1.2 -> 1.0 with OutQuad easing
                    double t = (_animationElapsed - pulseHalf) / pulseHalf;
                    double eased = EaseOutQuad(t);
                    _pulseScale = 1.2 - 0.2 * eased;
                }
                else
                {
                    // Animation complete, return to Idle
                    _pulseScale = 1.0;
                    State = HaloState.Idle;
                    return;
                }
                break;

            case HaloState.Failed:
                _animationElapsed += TimerIntervalMs;
                double fadeHalf = FadeDurationMs / 2.0;
                if (_animationElapsed <= fadeHalf)
                {
                    // Fade out: 1.0 -> 0.3 with InOutQuad easing
                    double t = _animationElapsed / fadeHalf;
                    double eased = EaseInOutQuad(t);
                    _fadeOpacity = 1.0 - 0.7 * eased;
                }
                else if (_animationElapsed <= FadeDurationMs)
                {
                    // Fade in: 0.3 -> 1.0 with InOutQuad easing
                    double t = (_animationElapsed - fadeHalf) / fadeHalf;
                    double eased = EaseInOutQuad(t);
                    _fadeOpacity = 0.3 + 0.7 * eased;
                }
                else
                {
                    // Animation complete, return to Idle
                    _fadeOpacity = 1.0;
                    State = HaloState.Idle;
                    return;
                }
                break;

            case HaloState.Idle:
                StopTimer();
                return;
        }

        InvalidateVisual();
    }

    /// <summary>OutQuad easing: t * (2 - t)</summary>
    private static double EaseOutQuad(double t) => t * (2.0 - t);

    /// <summary>InOutQuad easing</summary>
    private static double EaseInOutQuad(double t) =>
        t < 0.5 ? 2.0 * t * t : 1.0 - (-2.0 * t + 2.0) * (-2.0 * t + 2.0) / 2.0;

    public override void Render(DrawingContext context)
    {
        base.Render(context);

        var bounds = Bounds;
        double width = bounds.Width;
        double height = bounds.Height;

        if (width <= 0 || height <= 0) return;

        // Center of the total widget area (60x60)
        var center = new Point(width / 2.0, height / 2.0);

        // Base radius is half of DEFAULT_SIZE (48/2 = 24)
        double baseRadius = DefaultSize / 2.0;

        // アイコンと同じ比率
        double outerRadius = 0.92 * baseRadius;
        double innerRadius = 0.45 * baseRadius;

        var state = State;

        using var _ = state switch
        {
            HaloState.Success => context.PushTransform(
                Matrix.CreateTranslation(-center.X, -center.Y) *
                Matrix.CreateScale(_pulseScale, _pulseScale) *
                Matrix.CreateTranslation(center.X, center.Y)),
            HaloState.Failed => context.PushOpacity(_fadeOpacity),
            _ => default(DrawingContext.PushedState),
        };

        // 1. 白い外側リング
        var whitePen = new Pen(new SolidColorBrush(WhiteColor), OuterRingWidth);
        context.DrawEllipse(null, whitePen, center, outerRadius, outerRadius);

        // 2. ライトブルー内側リング
        var accentLightPen = new Pen(new SolidColorBrush(AccentLightColor), 2.0);
        context.DrawEllipse(null, accentLightPen, center, innerRadius, innerRadius);

        // 3. 青いアーク（外側リングに沿って回転）
        double segmentRadius = outerRadius;
        var segmentPen = new Pen(new SolidColorBrush(AccentColor), OuterRingWidth)
        {
            LineCap = PenLineCap.Flat,
        };

        double rotationOffset = (state == HaloState.Processing) ? _rotationAngle : 0.0;

        // 12時→9時（90度分）
        double startAngleScreen = 270.0 + rotationOffset;
        double endAngleScreen = 180.0 + rotationOffset;

        double startRad = startAngleScreen * Math.PI / 180.0;
        double endRad = endAngleScreen * Math.PI / 180.0;

        var arcStart = new Point(
            center.X + segmentRadius * Math.Cos(startRad),
            center.Y + segmentRadius * Math.Sin(startRad));
        var arcEnd = new Point(
            center.X + segmentRadius * Math.Cos(endRad),
            center.Y + segmentRadius * Math.Sin(endRad));

        var geometry = new StreamGeometry();
        using (var ctx = geometry.Open())
        {
            ctx.BeginFigure(arcStart, false);
            ctx.ArcTo(
                arcEnd,
                new Size(segmentRadius, segmentRadius),
                rotationAngle: 0,
                isLargeArc: false,
                sweepDirection: SweepDirection.CounterClockwise);
        }

        context.DrawGeometry(null, segmentPen, geometry);
    }

    protected override Size MeasureOverride(Size availableSize)
    {
        return new Size(TotalSize, TotalSize);
    }

    protected override Size ArrangeOverride(Size finalSize)
    {
        return new Size(TotalSize, TotalSize);
    }
}
