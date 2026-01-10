"""
Halo Indicator Widget

A circular ring (halo) indicator that visually represents recording state.
Supports multiple states: IDLE, RECORDING, SUCCESS, FAILED, DEBOUNCE.
"""

from enum import Enum
from typing import Optional

from PySide6.QtCore import (
    Qt, Signal, Property, QTimer,
    QPropertyAnimation, QEasingCurve, QPointF
)
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtWidgets import QWidget

from ..styles.tokens import COLORS, LAYOUT, ANIMATION


class HaloState(Enum):
    """Halo indicator states."""
    IDLE = "idle"
    RECORDING = "recording"
    SUCCESS = "success"
    FAILED = "failed"
    DEBOUNCE = "debounce"


class HaloIndicator(QWidget):
    """
    A circular halo indicator widget for displaying recording state.

    The halo displays different visual states:
    - IDLE: Gray static ring
    - RECORDING: Cyan ring with slow rotation animation
    - SUCCESS: Cyan pulse (expand -> contract) then return to IDLE
    - FAILED: Gray shrink animation then return to IDLE
    - DEBOUNCE: Light gray ring with X mark in center

    Signals:
        state_changed(str): Emitted when state changes, with state name.

    Usage:
        halo = HaloIndicator()
        halo.start_recording()
        # ... later ...
        halo.show_success()
    """

    # Signals
    state_changed = Signal(str)

    # Default sizes
    DEFAULT_SIZE = LAYOUT.get("halo_size", 32)

    # Ring properties
    RING_WIDTH_IDLE = 2
    RING_WIDTH_ACTIVE = 3

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
        self._color_idle = QColor(COLORS.get("halo_idle", "#C8D2E0"))
        self._color_active = QColor(COLORS.get("halo_active", "#63C6FF"))
        self._color_success = QColor(COLORS.get("halo_success", "#63C6FF"))
        self._color_failed = QColor(COLORS.get("halo_failed", "#8A95A8"))
        self._color_debounce = QColor(COLORS.get("halo_debounce", "#E5EAF2"))

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
        size = self.DEFAULT_SIZE
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
            state: State name ('idle', 'recording', 'success', 'failed', 'debounce').
        """
        try:
            new_state = HaloState(state.lower())
        except ValueError:
            return

        if new_state == self._state:
            return

        old_state = self._state
        self._state = new_state

        # Stop any running animations
        self._stop_animations()

        # Start appropriate animation for new state
        if new_state == HaloState.RECORDING:
            self._start_rotation()
        elif new_state == HaloState.SUCCESS:
            self._start_success_animation()
        elif new_state == HaloState.FAILED:
            self._start_failed_animation()
        else:
            # IDLE or DEBOUNCE - reset properties
            self._reset_properties()

        self.state_changed.emit(new_state.value)
        self.update()

    def start_recording(self) -> None:
        """Transition to RECORDING state."""
        self.set_state(HaloState.RECORDING.value)

    def show_success(self) -> None:
        """
        Show SUCCESS animation then return to IDLE.

        Displays a pulse animation (expand -> contract) in cyan.
        """
        self.set_state(HaloState.SUCCESS.value)

    def show_failed(self) -> None:
        """
        Show FAILED animation then return to IDLE.

        Displays a shrink animation in gray.
        """
        self.set_state(HaloState.FAILED.value)

    def set_debounce(self, active: bool) -> None:
        """
        Set debounce state ON/OFF.

        Args:
            active: True to show debounce state, False to return to IDLE.
        """
        if active:
            self.set_state(HaloState.DEBOUNCE.value)
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
        """Start rotation animation for RECORDING state."""
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

        # Create scale animation: 1.0 -> 1.3 -> 0.0
        self._scale_animation = QPropertyAnimation(self, b"scale")
        self._scale_animation.setDuration(self._pulse_duration)
        self._scale_animation.setKeyValueAt(0.0, 1.0)
        self._scale_animation.setKeyValueAt(0.4, 1.3)  # Expand
        self._scale_animation.setKeyValueAt(1.0, 0.0)  # Contract to nothing
        self._scale_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Create opacity animation: 1.0 -> 1.0 -> 0.0
        self._opacity_animation = QPropertyAnimation(self, b"opacity")
        self._opacity_animation.setDuration(self._pulse_duration)
        self._opacity_animation.setKeyValueAt(0.0, 1.0)
        self._opacity_animation.setKeyValueAt(0.5, 1.0)
        self._opacity_animation.setKeyValueAt(1.0, 0.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Connect finished signal to return to IDLE
        self._scale_animation.finished.connect(self._on_animation_finished)

        # Start animations
        self._scale_animation.start()
        self._opacity_animation.start()

    def _start_failed_animation(self) -> None:
        """Start failed shrink animation."""
        # Reset
        self._scale = 1.0
        self._opacity = 1.0

        # Create scale animation: 1.0 -> 0.0 (shrink)
        self._scale_animation = QPropertyAnimation(self, b"scale")
        self._scale_animation.setDuration(int(self._pulse_duration * 0.8))
        self._scale_animation.setStartValue(1.0)
        self._scale_animation.setEndValue(0.0)
        self._scale_animation.setEasingCurve(QEasingCurve.Type.InQuad)

        # Create opacity animation
        self._opacity_animation = QPropertyAnimation(self, b"opacity")
        self._opacity_animation.setDuration(int(self._pulse_duration * 0.8))
        self._opacity_animation.setStartValue(1.0)
        self._opacity_animation.setEndValue(0.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.InQuad)

        # Connect finished signal to return to IDLE
        self._scale_animation.finished.connect(self._on_animation_finished)

        # Start animations
        self._scale_animation.start()
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

        # Calculate center and size
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        base_radius = min(self.width(), self.height()) / 2.0 - 2

        # Apply scale
        radius = base_radius * self._scale

        if radius <= 0:
            painter.end()
            return

        # Choose color and width based on state
        if self._state == HaloState.IDLE:
            color = self._color_idle
            ring_width = self.RING_WIDTH_IDLE
            self._draw_ring(painter, center, radius, color, ring_width)

        elif self._state == HaloState.RECORDING:
            color = self._color_active
            ring_width = self.RING_WIDTH_ACTIVE
            self._draw_rotating_ring(painter, center, radius, color, ring_width)

        elif self._state == HaloState.SUCCESS:
            color = self._color_success
            ring_width = self.RING_WIDTH_ACTIVE
            self._draw_ring(painter, center, radius, color, ring_width)

        elif self._state == HaloState.FAILED:
            color = self._color_failed
            ring_width = self.RING_WIDTH_ACTIVE
            self._draw_ring(painter, center, radius, color, ring_width)

        elif self._state == HaloState.DEBOUNCE:
            color = self._color_debounce
            ring_width = self.RING_WIDTH_IDLE
            self._draw_ring(painter, center, radius, color, ring_width)
            self._draw_x_mark(painter, center, radius * 0.5)

        painter.end()

    def _draw_ring(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        color: QColor,
        width: int
    ) -> None:
        """Draw a simple ring."""
        pen = QPen(color)
        pen.setWidth(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawEllipse(center, radius, radius)

    def _draw_rotating_ring(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        color: QColor,
        width: int
    ) -> None:
        """
        Draw a rotating ring with gradient effect.

        Creates a visual effect where part of the ring appears brighter,
        giving the impression of rotation.
        """
        # Save painter state
        painter.save()

        # Translate to center and rotate
        painter.translate(center)
        painter.rotate(self._rotation_angle)

        # Draw the base ring in a lighter shade
        base_color = QColor(color)
        base_color.setAlpha(100)
        pen = QPen(base_color)
        pen.setWidth(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Draw bright arc segment (the "rotating" part)
        pen = QPen(color)
        pen.setWidth(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Draw arc - Qt uses 1/16th of a degree
        # Draw a 90-degree bright arc
        rect_size = radius * 2
        arc_rect = QPointF(-radius, -radius)

        from PySide6.QtCore import QRectF
        rect = QRectF(-radius, -radius, rect_size, rect_size)

        # Start at 0 degrees, span 90 degrees (in 1/16th degree units)
        start_angle = 0 * 16
        span_angle = 90 * 16
        painter.drawArc(rect, start_angle, span_angle)

        # Restore painter state
        painter.restore()

    def _draw_x_mark(
        self,
        painter: QPainter,
        center: QPointF,
        size: float
    ) -> None:
        """Draw an X mark in the center for debounce state."""
        # Use a darker shade of debounce color for the X
        x_color = QColor(self._color_failed)
        x_color.setAlpha(180)

        pen = QPen(x_color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Calculate X endpoints
        half_size = size / 2.0

        # Draw X (two diagonal lines)
        painter.drawLine(
            QPointF(center.x() - half_size, center.y() - half_size),
            QPointF(center.x() + half_size, center.y() + half_size)
        )
        painter.drawLine(
            QPointF(center.x() + half_size, center.y() - half_size),
            QPointF(center.x() - half_size, center.y() + half_size)
        )


if __name__ == "__main__":
    # Demo / test code
    import sys
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QPushButton

    app = QApplication(sys.argv)

    # Create demo window
    window = QWidget()
    window.setWindowTitle("Halo Indicator Demo")
    window.setStyleSheet("background-color: #F6F1E6;")

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
    from PySide6.QtWidgets import QLabel
    status_label = QLabel("State: idle")
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

    btn_recording = QPushButton("RECORDING")
    btn_recording.clicked.connect(lambda: halo.start_recording())
    btn_layout.addWidget(btn_recording)

    btn_success = QPushButton("SUCCESS")
    btn_success.clicked.connect(lambda: halo.show_success())
    btn_layout.addWidget(btn_success)

    btn_failed = QPushButton("FAILED")
    btn_failed.clicked.connect(lambda: halo.show_failed())
    btn_layout.addWidget(btn_failed)

    btn_debounce = QPushButton("DEBOUNCE")
    btn_debounce.clicked.connect(lambda: halo.set_debounce(True))
    btn_layout.addWidget(btn_debounce)

    layout.addLayout(btn_layout)

    window.resize(400, 200)
    window.show()

    sys.exit(app.exec())
