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

        // Ring radii as ratios of base radius
        double outerRadius = 0.92 * baseRadius;
        double innerRadius = 0.78 * baseRadius;
        double centerRadius = 0.35 * baseRadius;

        // Apply transforms for Success (pulse) and Failed (fade)
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

        // Pens
        var whitePen = new Pen(new SolidColorBrush(WhiteColor), OuterRingWidth);
        var accentLightPen = new Pen(new SolidColorBrush(AccentLightColor), 2.0);
        var accentPen = new Pen(new SolidColorBrush(AccentColor), 2.0);

        // 1. White outer ring
        context.DrawEllipse(null, whitePen, center, outerRadius, outerRadius);

        // 2. Light blue inner ring
        context.DrawEllipse(null, accentLightPen, center, innerRadius, innerRadius);

        // 3. Blue center ring (not filled)
        context.DrawEllipse(null, accentPen, center, centerRadius, centerRadius);

        // 4. Blue segment between outer and inner ring
        // The segment is a thick arc at the average radius between outer and inner rings
        double segmentRadius = (outerRadius + innerRadius) / 2.0;
        double segmentPenWidth = outerRadius - innerRadius + OuterRingWidth;

        var segmentPen = new Pen(new SolidColorBrush(AccentColor), segmentPenWidth)
        {
            LineCap = PenLineCap.Flat,
        };

        // In Python/Qt: start_angle = 90*16, span_angle = 90*16
        // That means: start at 90° (top/12 o'clock), sweep counter-clockwise 90° to 180° (9 o'clock)
        // In Avalonia math coords: 90° is straight up (negative Y), 180° is left (negative X)
        // We draw from 90° to 180° counter-clockwise in standard math orientation.
        //
        // In screen coordinates (Y flipped):
        //   Math 90° (up) = screen -90° or 270°
        //   Math 180° (left) = screen 180°
        // So in screen coords we go clockwise from 270° to 180°... but it's easier to just
        // compute the points directly.
        //
        // Qt angles: 0° = 3 o'clock, 90° = 12 o'clock, counter-clockwise positive
        // For Avalonia (screen coords, Y down): 0° = 3 o'clock, angles go clockwise
        //   Qt 90° (12 o'clock) = Avalonia -90° = 270°
        //   Qt 180° (9 o'clock) = Avalonia -180° = 180°
        //
        // The arc from 12 o'clock to 9 o'clock going counter-clockwise (in Qt)
        // = arc from 270° to 180° going counter-clockwise in screen coords
        // = arc from 270° sweeping -90° in screen coords
        // But ArcTo uses sweep direction, so:
        //   Start at 270° (top), end at 180° (left), sweep CounterClockwise
        //   OR equivalently: start at 270°, end at 180°, counter-clockwise (going through 270->180)
        //   That's actually clockwise if going 270->360->0->...->180, so we want CounterClockwise
        //   going 270->225->180 which is the short way.

        // During Processing, add rotation offset
        double rotationOffset = (state == HaloState.Processing) ? _rotationAngle : 0.0;

        // Start angle: 270° in screen coords (12 o'clock) + rotation
        // End angle: 180° in screen coords (9 o'clock) + rotation
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
