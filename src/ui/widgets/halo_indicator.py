"""
Halo Indicator Widget

A dual-circle indicator that visually represents processing state.
Inner solid circle + outer ring with accent color segment.
"""

from enum import Enum
from typing import Optional

from PySide6.QtCore import (
    Qt, Signal, Property, QTimer,
    QPropertyAnimation, QEasingCurve, QPointF, QRectF
)
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtWidgets import QWidget

from ..styles.tokens import COLORS, LAYOUT, ANIMATION


class HaloState(Enum):
    """Halo indicator states."""
    IDLE = "idle"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class HaloIndicator(QWidget):
    """
    A dual-circle indicator widget for displaying processing state.

    Design:
    - Inner circle: Small solid circle (accent color)
    - Outer ring: Thick ring with 90° accent segment + 270° white segment
    - Processing: Outer ring rotates

    States:
    - IDLE: Static display (accent at top-left quadrant)
    - PROCESSING: Outer ring rotates continuously
    - SUCCESS: Brief pulse animation then return to IDLE
    - FAILED: Brief fade animation then return to IDLE

    Signals:
        state_changed(str): Emitted when state changes, with state name.

    Usage:
        halo = HaloIndicator()
        halo.start_processing()
        # ... later ...
        halo.show_success()
    """

    # Signals
    state_changed = Signal(str)

    # Default sizes
    DEFAULT_SIZE = LAYOUT.get("halo_size", 32)

    # Design constants
    OUTER_RING_WIDTH = 4          # White outer ring thickness
    INNER_RING_WIDTH = 2          # Blue inner ring thickness
    CENTER_RING_WIDTH = 2         # Center ring thickness
    CENTER_RING_RATIO = 0.35      # Center ring radius
    OUTER_RING_RATIO = 0.92       # White outer ring radius (larger)
    INNER_RING_RATIO = 0.78       # Blue inner ring radius
    SEGMENT_SPAN_DEGREES = 90     # Blue segment span

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the halo indicator.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        # State
        self._state = HaloState.IDLE

        # Animation properties
        self._rotation_angle = 0.0
        self._scale = 1.0
        self._opacity = 1.0

        # Colors from tokens
        self._color_accent = QColor(COLORS.get("accent", "#63C6FF"))
        self._color_accent_light = QColor(COLORS.get("accent_light", "#A7E4FF"))
        self._color_white = QColor("#FFFFFF")

        # Timers
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._update_rotation)

        # Animation durations from tokens
        self._rotation_duration = ANIMATION.get("halo_rotation_duration", 2000)
        self._pulse_duration = ANIMATION.get("halo_pulse_duration", 600)

        # Property animations
        self._scale_animation: Optional[QPropertyAnimation] = None
        self._opacity_animation: Optional[QPropertyAnimation] = None

        # Setup
        self._setup_widget()

    def _setup_widget(self) -> None:
        """Configure widget properties."""
        # Add margin to widget size to prevent clipping of thick pen strokes
        # Account for: segment overhang + scale animation (1.2x) + safety buffer
        margin = 12
        size = self.DEFAULT_SIZE + margin
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # =========================================================================
    # Properties for Animation
    # =========================================================================

    def _get_rotation_angle(self) -> float:
        return self._rotation_angle

    def _set_rotation_angle(self, value: float) -> None:
        self._rotation_angle = value
        self.update()

    def _get_scale(self) -> float:
        return self._scale

    def _set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    rotationAngle = Property(float, _get_rotation_angle, _set_rotation_angle)
    scale = Property(float, _get_scale, _set_scale)
    opacity = Property(float, _get_opacity, _set_opacity)

    # =========================================================================
    # Public Methods
    # =========================================================================

    @property
    def state(self) -> HaloState:
        """Get current state."""
        return self._state

    def set_state(self, state: str) -> None:
        """
        Set the indicator state.

        Args:
            state: State name ('idle', 'processing', 'success', 'failed').
        """
        # Handle legacy state names for compatibility
        state_lower = state.lower()
        if state_lower == "recording":
            state_lower = "processing"

        try:
            new_state = HaloState(state_lower)
        except ValueError:
            return

        if new_state == self._state:
            return

        self._state = new_state

        # Stop any running animations
        self._stop_animations()

        # Start appropriate animation for new state
        if new_state == HaloState.PROCESSING:
            self._start_rotation()
        elif new_state == HaloState.SUCCESS:
            self._start_success_animation()
        elif new_state == HaloState.FAILED:
            self._start_failed_animation()
        else:
            # IDLE - reset properties
            self._reset_properties()

        self.state_changed.emit(new_state.value)
        self.update()

    def start_processing(self) -> None:
        """Transition to PROCESSING state."""
        self.set_state(HaloState.PROCESSING.value)

    def start_recording(self) -> None:
        """Alias for start_processing() for backward compatibility."""
        self.start_processing()

    def show_success(self) -> None:
        """
        Show SUCCESS animation then return to IDLE.

        Displays a pulse animation.
        """
        self.set_state(HaloState.SUCCESS.value)

    def show_failed(self) -> None:
        """
        Show FAILED animation then return to IDLE.

        Displays a fade animation.
        """
        self.set_state(HaloState.FAILED.value)

    def set_debounce(self, active: bool) -> None:
        """
        Set debounce state ON/OFF (legacy compatibility).

        Args:
            active: True to show processing state, False to return to IDLE.
        """
        if active:
            self.set_state(HaloState.PROCESSING.value)
        else:
            self.set_state(HaloState.IDLE.value)

    # =========================================================================
    # Animation Methods
    # =========================================================================

    def _stop_animations(self) -> None:
        """Stop all running animations."""
        self._rotation_timer.stop()

        if self._scale_animation:
            self._scale_animation.stop()
            self._scale_animation.deleteLater()
            self._scale_animation = None

        if self._opacity_animation:
            self._opacity_animation.stop()
            self._opacity_animation.deleteLater()
            self._opacity_animation = None

    def _reset_properties(self) -> None:
        """Reset animation properties to default."""
        self._rotation_angle = 0.0
        self._scale = 1.0
        self._opacity = 1.0
        self.update()

    def _start_rotation(self) -> None:
        """Start rotation animation for PROCESSING state."""
        # Calculate rotation step for smooth animation
        # 360 degrees over rotation_duration ms, update every 16ms (~60fps)
        update_interval = 16
        steps_per_rotation = self._rotation_duration / update_interval
        self._rotation_step = 360.0 / steps_per_rotation

        self._rotation_timer.start(update_interval)

    def _update_rotation(self) -> None:
        """Update rotation angle."""
        self._rotation_angle = (self._rotation_angle + self._rotation_step) % 360.0
        self.update()

    def _start_success_animation(self) -> None:
        """Start success pulse animation."""
        # Reset
        self._scale = 1.0
        self._opacity = 1.0

        # Create scale animation: 1.0 -> 1.2 -> 1.0
        self._scale_animation = QPropertyAnimation(self, b"scale")
        self._scale_animation.setDuration(self._pulse_duration)
        self._scale_animation.setKeyValueAt(0.0, 1.0)
        self._scale_animation.setKeyValueAt(0.5, 1.2)
        self._scale_animation.setKeyValueAt(1.0, 1.0)
        self._scale_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Connect finished signal to return to IDLE
        self._scale_animation.finished.connect(self._on_animation_finished)

        # Start animation
        self._scale_animation.start()

    def _start_failed_animation(self) -> None:
        """Start failed fade animation."""
        # Reset
        self._scale = 1.0
        self._opacity = 1.0

        # Create opacity animation: 1.0 -> 0.3 -> 1.0
        self._opacity_animation = QPropertyAnimation(self, b"opacity")
        self._opacity_animation.setDuration(int(self._pulse_duration * 0.8))
        self._opacity_animation.setKeyValueAt(0.0, 1.0)
        self._opacity_animation.setKeyValueAt(0.5, 0.3)
        self._opacity_animation.setKeyValueAt(1.0, 1.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Connect finished signal to return to IDLE
        self._opacity_animation.finished.connect(self._on_animation_finished)

        # Start animation
        self._opacity_animation.start()

    def _on_animation_finished(self) -> None:
        """Handle animation completion."""
        # Return to IDLE state without triggering new animations
        self._state = HaloState.IDLE
        self._reset_properties()
        self.state_changed.emit(HaloState.IDLE.value)

    # =========================================================================
    # Paint Methods
    # =========================================================================

    def paintEvent(self, event) -> None:
        """Paint the halo indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Apply opacity
        painter.setOpacity(self._opacity)

        # Calculate center and sizes
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        # Use the original DEFAULT_SIZE as base for drawing, regardless of widget size
        base_radius = self.DEFAULT_SIZE / 2.0

        # Apply scale
        center_ring_radius = base_radius * self.CENTER_RING_RATIO * self._scale
        outer_ring_radius = base_radius * self.OUTER_RING_RATIO * self._scale
        inner_ring_radius = base_radius * self.INNER_RING_RATIO * self._scale

        if center_ring_radius <= 0 or outer_ring_radius <= 0:
            painter.end()
            return

        # Draw white outer ring (complete circle - the "mechanical" ring)
        self._draw_white_outer_ring(painter, center, outer_ring_radius)

        # Draw light blue inner ring (complete circle - inside the outer ring)
        self._draw_blue_inner_ring(painter, center, inner_ring_radius)

        # Draw blue segment at top-left (the "meshing" part, 90°-180°)
        self._draw_blue_segment(painter, center, outer_ring_radius, inner_ring_radius)

        # Draw center ring (not filled)
        self._draw_center_ring(painter, center, center_ring_radius)

        painter.end()

    def _draw_center_ring(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float
    ) -> None:
        """Draw the center ring (not filled)."""
        pen = QPen(self._color_accent)
        pen.setWidth(self.CENTER_RING_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

    def _draw_white_outer_ring(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float
    ) -> None:
        """Draw the white outer ring (complete circle)."""
        pen = QPen(self._color_white)
        pen.setWidth(self.OUTER_RING_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

    def _draw_blue_inner_ring(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float
    ) -> None:
        """Draw the light blue inner ring (complete circle)."""
        pen = QPen(self._color_accent_light)
        pen.setWidth(self.INNER_RING_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

    def _draw_blue_segment(
        self,
        painter: QPainter,
        center: QPointF,
        outer_radius: float,
        inner_radius: float
    ) -> None:
        """
        Draw the blue segment that "meshes" with the rings.

        The segment spans from the outer ring to the inner ring,
        positioned at top-left (90°-180° in coordinate plane) and rotates during processing.

        In Qt coordinate system:
        - 0 degrees is at 3 o'clock (right side)
        - 90 degrees is at 12 o'clock (top)
        - 180 degrees is at 9 o'clock (left)
        - Positive angles go counter-clockwise

        So 90°-180° means from top to left.
        """
        painter.save()

        # Translate to center for rotation
        painter.translate(center)

        # Apply rotation for processing state
        if self._state == HaloState.PROCESSING:
            painter.rotate(self._rotation_angle)

        # The segment is drawn as a thick arc between inner and outer ring
        segment_radius = (outer_radius + inner_radius) / 2.0
        segment_width = outer_radius - inner_radius + self.OUTER_RING_WIDTH

        pen = QPen(self._color_accent)
        pen.setWidth(int(segment_width))
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        rect = QRectF(-segment_radius, -segment_radius,
                      segment_radius * 2, segment_radius * 2)

        # Draw arc from 90° (top) to 180° (left)
        # Start at 90°, span 90° counter-clockwise
        start_angle = 90 * 16
        span_angle = 90 * 16
        painter.drawArc(rect, start_angle, span_angle)

        painter.restore()


if __name__ == "__main__":
    # Demo / test code
    import sys
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

    app = QApplication(sys.argv)

    # Create demo window
    window = QWidget()
    window.setWindowTitle("Halo Indicator Demo")
    window.setStyleSheet("background-color: #0B1B2B;")  # Dark background to see white ring

    layout = QVBoxLayout(window)

    # Create halo indicator
    halo = HaloIndicator()
    halo_container = QWidget()
    halo_layout = QHBoxLayout(halo_container)
    halo_layout.addStretch()
    halo_layout.addWidget(halo)
    halo_layout.addStretch()
    layout.addWidget(halo_container)

    # Status label
    status_label = QLabel("State: idle")
    status_label.setStyleSheet("color: white;")
    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(status_label)

    def update_status(state: str):
        status_label.setText(f"State: {state}")

    halo.state_changed.connect(update_status)

    # Control buttons
    btn_layout = QHBoxLayout()

    btn_idle = QPushButton("IDLE")
    btn_idle.clicked.connect(lambda: halo.set_state("idle"))
    btn_layout.addWidget(btn_idle)

    btn_processing = QPushButton("PROCESSING")
    btn_processing.clicked.connect(lambda: halo.start_processing())
    btn_layout.addWidget(btn_processing)

    btn_success = QPushButton("SUCCESS")
    btn_success.clicked.connect(lambda: halo.show_success())
    btn_layout.addWidget(btn_success)

    btn_failed = QPushButton("FAILED")
    btn_failed.clicked.connect(lambda: halo.show_failed())
    btn_layout.addWidget(btn_failed)

    layout.addLayout(btn_layout)

    window.resize(400, 200)
    window.show()

    sys.exit(app.exec())
