"""
Capture Overlay Widget

A fullscreen overlay for selecting capture regions via mouse drag.
Supports header/body region switching and cross-platform display.
Now includes two-stage selection mode for header and body regions.
"""

import sys
from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QScreen,
    QMouseEvent, QKeyEvent, QPaintEvent, QPixmap
)
from PySide6.QtWidgets import QWidget, QApplication


class RegionType(Enum):
    """Type of capture region being selected."""
    HEADER = "header"
    BODY = "body"


class SelectionStage(Enum):
    """Selection stage in the two-stage capture overlay."""
    IDLE = auto()      # Not started
    HEADER = auto()    # Selecting header region
    BODY = auto()      # Selecting body region
    COMPLETE = auto()  # Both regions selected


class CaptureOverlay(QWidget):
    """
    Fullscreen overlay widget for capture region selection.

    This widget displays a semi-transparent overlay over the entire screen
    and allows the user to select a rectangular region by clicking and dragging.

    Signals:
        region_selected: Emitted when a region is successfully selected.
                        Args: (x: int, y: int, width: int, height: int, region_type: str)
        selection_cancelled: Emitted when selection is cancelled (ESC pressed).

    Usage:
        overlay = CaptureOverlay(region_type=RegionType.HEADER)
        overlay.region_selected.connect(on_region_selected)
        overlay.selection_cancelled.connect(on_cancelled)
        overlay.show()
    """

    # Signals
    region_selected = Signal(int, int, int, int, str)  # x, y, width, height, region_type
    selection_cancelled = Signal()
    regions_selected = Signal(object, object)  # header_rect, body_rect (as Rect objects)

    # Theme colors (matching NoaLog theme)
    OVERLAY_COLOR = QColor(26, 39, 68, 77)  # #1a2744 with 30% opacity
    SELECTION_BORDER_COLOR = QColor(94, 179, 240)  # #5eb3f0 accent
    SELECTION_FILL_COLOR = QColor(94, 179, 240, 51)  # #5eb3f0 with 20% opacity
    TEXT_COLOR = QColor(255, 255, 255)
    TEXT_BG_COLOR = QColor(26, 39, 68, 204)  # #1a2744 with 80% opacity

    # Minimum selection size
    MIN_SELECTION_SIZE = 10

    def __init__(
        self,
        region_type: RegionType = RegionType.BODY,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the capture overlay.

        Args:
            region_type: The type of region being selected (header or body).
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._region_type = region_type
        self._is_selecting = False
        self._start_point: Optional[QPoint] = None
        self._current_point: Optional[QPoint] = None
        self._selection_rect: Optional[QRect] = None

        # Two-stage selection mode
        self._two_stage_mode = False
        self._selection_stage = SelectionStage.IDLE
        self._header_rect: Optional[QRect] = None  # Stored header selection
        self._body_rect: Optional[QRect] = None    # Stored body selection

        # Background screenshot for region selection
        self._background_screenshot: Optional[QPixmap] = None

        self._setup_window()

    def _setup_window(self) -> None:
        """Configure window properties for fullscreen overlay."""
        # Window flags for overlay behavior
        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Platform-specific adjustments
        if sys.platform == "darwin":
            # macOS: Add transparent background support
            flags |= Qt.WindowType.NoDropShadowWindowHint
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        elif sys.platform == "win32":
            # Windows: Ensure proper layered window
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            # Linux/other: Standard transparent background
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setWindowFlags(flags)

        # Allow mouse tracking without clicking
        self.setMouseTracking(True)

        # Set cursor to crosshair for selection mode
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Get the full virtual desktop geometry (all screens)
        self._set_fullscreen_geometry()

        # Note: macOS all-spaces behavior is set in start_two_stage_selection()
        # after show() is called, when the window ID becomes valid

    def _setup_macos_all_spaces(self) -> None:
        """Configure window to appear on all macOS Spaces/Desktops."""
        try:
            import objc
            from ctypes import c_void_p
            from Cocoa import NSWindow

            # Constants for collection behavior
            NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
            NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8

            # Get the native NSView from Qt window
            view_ptr = self.winId()
            if view_ptr:
                # Convert to NSView and get its window
                ns_view = objc.objc_object(c_void_p=int(view_ptr))
                ns_window = ns_view.window()

                if ns_window:
                    # Set collection behavior to appear on all spaces
                    behavior = (
                        NSWindowCollectionBehaviorCanJoinAllSpaces |
                        NSWindowCollectionBehaviorFullScreenAuxiliary
                    )
                    ns_window.setCollectionBehavior_(behavior)
                    ns_window.setLevel_(1000)  # Above normal windows

        except ImportError:
            # PyObjC not available
            import logging
            logging.getLogger(__name__).warning(
                "PyObjC not installed. Overlay may not appear on all Spaces. "
                "Install with: pip install pyobjc-framework-Cocoa"
            )
        except Exception as e:
            # Log but don't fail - overlay will still work on current space
            import logging
            logging.getLogger(__name__).debug(f"Could not set all-spaces behavior: {e}")

    def _set_fullscreen_geometry(self) -> None:
        """
        Set the overlay to cover all available screens.

        This method calculates the bounding rectangle of all connected
        monitors and sizes the overlay accordingly.
        """
        app = QApplication.instance()
        if app is None:
            return

        screens = app.screens()
        if not screens:
            return

        # Calculate the bounding rect of all screens
        combined_rect = QRect()
        for screen in screens:
            screen_geo = screen.geometry()
            combined_rect = combined_rect.united(screen_geo)

        self.setGeometry(combined_rect)

    @property
    def region_type(self) -> RegionType:
        """Get the current region type."""
        return self._region_type

    @region_type.setter
    def region_type(self, value: RegionType) -> None:
        """Set the region type and update display."""
        self._region_type = value
        self.update()

    def show(self) -> None:
        """Show the overlay and ensure it covers all screens."""
        self._set_fullscreen_geometry()
        super().show()
        self.raise_()
        self.activateWindow()

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the overlay and selection rectangle.

        Draws:
        1. Background screenshot (if available)
        2. Semi-transparent overlay background
        3. Confirmed header rect (if in body selection stage)
        4. Selection rectangle with dashed border (if selecting)
        5. Instructions and dimension info
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background screenshot first (so user can see the screen content)
        if self._background_screenshot and not self._background_screenshot.isNull():
            painter.drawPixmap(self.rect(), self._background_screenshot)

        # Draw the semi-transparent overlay on top of screenshot
        painter.fillRect(self.rect(), self.OVERLAY_COLOR)

        # Draw confirmed header rect (if in body selection stage)
        if self._two_stage_mode and self._selection_stage == SelectionStage.BODY and self._header_rect:
            self._draw_confirmed_region(painter, self._header_rect, "Header")

        # Draw current selection if active
        if self._selection_rect and not self._selection_rect.isNull():
            self._draw_selection(painter)

        # Draw instructions
        self._draw_instructions(painter)

        painter.end()

    def _draw_selection(self, painter: QPainter) -> None:
        """Draw the selection rectangle with dashed border.

        Note: We intentionally avoid using CompositionMode_Clear during selection
        as it causes the underlying window content to show through on Webviews.
        Instead, we use a semi-transparent fill that maintains visibility of the
        background screenshot while clearly indicating the selection area.
        """
        rect = self._selection_rect.normalized()

        # Draw the background screenshot in the selection area for visibility
        # This shows what will be captured without making it fully transparent
        if self._background_screenshot and not self._background_screenshot.isNull():
            # Draw the screenshot portion for the selected area
            painter.setClipRect(rect.adjusted(2, 2, -2, -2))
            painter.drawPixmap(self.rect(), self._background_screenshot)
            painter.setClipping(False)

            # Add a very light tint to indicate selection (not fully clear)
            selection_tint = QColor(94, 179, 240, 40)  # Light blue tint
            painter.fillRect(rect.adjusted(2, 2, -2, -2), selection_tint)
        else:
            # Fallback: If no screenshot, use lighter overlay
            lighter_overlay = QColor(26, 39, 68, 60)  # More visible than before
            painter.fillRect(rect, lighter_overlay)

        # Draw semi-transparent border area
        painter.fillRect(rect, self.SELECTION_FILL_COLOR)

        # Draw dashed border
        pen = QPen(self.SELECTION_BORDER_COLOR)
        pen.setWidth(3)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([8, 4])
        painter.setPen(pen)
        painter.drawRect(rect)

        # Draw corner handles
        self._draw_corner_handles(painter, rect)

        # Draw dimension label
        self._draw_dimensions(painter, rect)

    def _draw_corner_handles(self, painter: QPainter, rect: QRect) -> None:
        """Draw small squares at the corners of the selection."""
        handle_size = 8
        pen = QPen(self.SELECTION_BORDER_COLOR)
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.GlobalColor.white))

        corners = [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight()
        ]

        for corner in corners:
            handle_rect = QRect(
                corner.x() - handle_size // 2,
                corner.y() - handle_size // 2,
                handle_size,
                handle_size
            )
            painter.drawRect(handle_rect)

    def _draw_dimensions(self, painter: QPainter, rect: QRect) -> None:
        """Draw width x height label below the selection."""
        dim_text = f"{rect.width()} x {rect.height()}"

        font = QFont("Hiragino Sans", 12)
        font.setBold(True)
        painter.setFont(font)

        # Position below the rectangle
        text_x = rect.center().x()
        text_y = rect.bottom() + 25

        # Draw background for text
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(dim_text)
        bg_rect = QRect(
            text_x - text_rect.width() // 2 - 8,
            text_y - text_rect.height() // 2 - 4,
            text_rect.width() + 16,
            text_rect.height() + 8
        )

        painter.fillRect(bg_rect, self.TEXT_BG_COLOR)

        # Draw text
        painter.setPen(QPen(self.TEXT_COLOR))
        painter.drawText(
            bg_rect,
            Qt.AlignmentFlag.AlignCenter,
            dim_text
        )

    def _draw_instructions(self, painter: QPainter) -> None:
        """Draw instruction text at the top of the overlay."""
        # Determine instruction text based on mode
        if self._two_stage_mode:
            if self._selection_stage == SelectionStage.HEADER:
                instruction = "Step 1/2: Select HEADER Region (Name/Organization) - Drag to select, Enter to confirm, ESC to cancel"
            elif self._selection_stage == SelectionStage.BODY:
                instruction = "Step 2/2: Select BODY Region (Text Content) - Drag to select, Enter to confirm, ESC to cancel"
            else:
                instruction = "Selection Complete"
        else:
            # Original single-stage instructions
            region_name = "Header" if self._region_type == RegionType.HEADER else "Body"
            instruction = f"Select {region_name} Region - Drag to select, ESC to cancel, Tab to switch region"

        font = QFont("Hiragino Sans", 14)
        font.setBold(True)
        painter.setFont(font)

        # Calculate text position (top center)
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(instruction)

        x = (self.width() - text_rect.width()) // 2
        y = 50

        # Draw background
        bg_rect = QRect(
            x - 16,
            y - text_rect.height() - 8,
            text_rect.width() + 32,
            text_rect.height() + 16
        )
        painter.fillRect(bg_rect, self.TEXT_BG_COLOR)

        # Draw region type indicator
        indicator_color = self.SELECTION_BORDER_COLOR
        indicator_rect = QRect(bg_rect.x() + 8, bg_rect.y() + 8, 4, bg_rect.height() - 16)
        painter.fillRect(indicator_rect, indicator_color)

        # Draw text
        painter.setPen(QPen(self.TEXT_COLOR))
        painter.drawText(
            bg_rect.adjusted(16, 0, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            instruction
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_selecting = True
            self._start_point = event.position().toPoint()
            self._current_point = self._start_point
            self._selection_rect = QRect(self._start_point, self._start_point)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move to update selection rectangle."""
        if self._is_selecting and self._start_point:
            self._current_point = event.position().toPoint()
            self._selection_rect = QRect(self._start_point, self._current_point)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to complete selection."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False

            if self._selection_rect:
                # Normalize the rect (handle any drag direction)
                rect = self._selection_rect.normalized()

                # Validate minimum size
                if rect.width() >= self.MIN_SELECTION_SIZE and rect.height() >= self.MIN_SELECTION_SIZE:
                    # In two-stage mode, don't close - wait for Enter to confirm
                    if self._two_stage_mode:
                        # Just update the display, Enter will confirm
                        self.update()
                    else:
                        # Single-stage mode: emit and close immediately
                        self.region_selected.emit(
                            rect.x(),
                            rect.y(),
                            rect.width(),
                            rect.height(),
                            self._region_type.value
                        )
                        self.close()
                else:
                    # Selection too small, reset
                    self._selection_rect = None
                    self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            # Cancel entire selection
            self._cleanup()
            self.selection_cancelled.emit()
            self.close()

        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self._two_stage_mode:
                self._confirm_current_stage()
            else:
                # Single-stage mode: Enter confirms current selection
                if self._selection_rect:
                    rect = self._selection_rect.normalized()
                    if rect.width() >= self.MIN_SELECTION_SIZE and rect.height() >= self.MIN_SELECTION_SIZE:
                        self.region_selected.emit(
                            rect.x(),
                            rect.y(),
                            rect.width(),
                            rect.height(),
                            self._region_type.value
                        )
                        self.close()

        elif event.key() == Qt.Key.Key_Tab:
            # Toggle is disabled in two-stage mode
            if not self._two_stage_mode:
                self._toggle_region_type()
        else:
            super().keyPressEvent(event)

    def _toggle_region_type(self) -> None:
        """Toggle between header and body region types."""
        if self._region_type == RegionType.HEADER:
            self._region_type = RegionType.BODY
        else:
            self._region_type = RegionType.HEADER
        self.update()

    def _reset_selection(self) -> None:
        """Reset the current selection state."""
        self._is_selecting = False
        self._start_point = None
        self._current_point = None
        self._selection_rect = None

    def _cleanup(self) -> None:
        """Cleanup resources when overlay is closed."""
        self._reset_selection()
        self._background_screenshot = None
        self._header_rect = None
        self._body_rect = None
        self._two_stage_mode = False
        self._selection_stage = SelectionStage.IDLE

    # =========================================================================
    # Two-Stage Selection Methods
    # =========================================================================

    def start_two_stage_selection(self) -> None:
        """
        Start the two-stage selection process.
        Stage 1: Select header region
        Stage 2: Select body region
        """
        # Capture screenshot BEFORE showing overlay so user can see the screen
        self._capture_background_screenshot()

        self._two_stage_mode = True
        self._selection_stage = SelectionStage.HEADER
        self._header_rect = None
        self._body_rect = None
        self._reset_selection()
        self.show()

        # macOS: Apply all-spaces behavior AFTER show() when window ID is valid
        if sys.platform == "darwin":
            self._setup_macos_all_spaces()

    def _capture_background_screenshot(self) -> None:
        """Capture a screenshot of all screens to use as background."""
        # Get the primary screen
        screen = QApplication.primaryScreen()
        if not screen:
            return

        # Capture the entire virtual desktop
        geometry = self.geometry()
        if geometry.isEmpty():
            # Use primary screen geometry if widget geometry not set yet
            geometry = screen.geometry()

        # Grab the screen content
        self._background_screenshot = screen.grabWindow(
            0,  # Window ID 0 = entire screen
            geometry.x(),
            geometry.y(),
            geometry.width(),
            geometry.height()
        )

    def _confirm_current_stage(self) -> None:
        """Confirm the current selection and advance to next stage."""
        if not self._selection_rect:
            return  # No selection to confirm

        rect = self._selection_rect.normalized()
        if rect.width() < self.MIN_SELECTION_SIZE or rect.height() < self.MIN_SELECTION_SIZE:
            return  # Selection too small

        if self._selection_stage == SelectionStage.HEADER:
            # Store header rect and move to body stage
            self._header_rect = rect
            self._selection_stage = SelectionStage.BODY
            self._reset_selection()
            self.update()

        elif self._selection_stage == SelectionStage.BODY:
            # Store body rect and complete
            self._body_rect = rect
            self._selection_stage = SelectionStage.COMPLETE
            self._emit_two_stage_result()

    def _emit_two_stage_result(self) -> None:
        """Emit the result of two-stage selection."""
        from models import Rect

        header = Rect(
            x=self._header_rect.x(),
            y=self._header_rect.y(),
            width=self._header_rect.width(),
            height=self._header_rect.height()
        )
        body = Rect(
            x=self._body_rect.x(),
            y=self._body_rect.y(),
            width=self._body_rect.width(),
            height=self._body_rect.height()
        )

        # Emit before cleanup to preserve rect values
        self.regions_selected.emit(header, body)

        # Cleanup and close
        self._background_screenshot = None  # Free memory
        self.close()

    def _draw_confirmed_region(self, painter: QPainter, rect: QRect, label: str) -> None:
        """Draw a confirmed region with a label."""
        # Green color for confirmed regions
        confirmed_border = QColor(100, 200, 100)
        confirmed_fill = QColor(100, 200, 100, 40)

        painter.fillRect(rect, confirmed_fill)

        pen = QPen(confirmed_border)
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(rect)

        # Draw label
        font = QFont("Hiragino Sans", 10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(confirmed_border))
        painter.drawText(rect.topLeft() + QPoint(5, -5), f"{label} (confirmed)")

    # =========================================================================
    # Public Methods
    # =========================================================================

    def start_selection(self, region_type: Optional[RegionType] = None) -> None:
        """
        Start the region selection process.

        Args:
            region_type: Optional region type to set before starting.
        """
        if region_type:
            self._region_type = region_type

        self._reset_selection()
        self.show()

    def get_selection_rect(self) -> Optional[QRect]:
        """
        Get the current selection rectangle.

        Returns:
            The current selection QRect, or None if no selection.
        """
        return self._selection_rect.normalized() if self._selection_rect else None


class CaptureOverlayManager:
    """
    Manager class for handling capture overlay lifecycle.

    This class provides a convenient interface for starting region selection
    and connecting to the results without managing the overlay directly.

    Usage:
        manager = CaptureOverlayManager()
        manager.start_capture(
            RegionType.HEADER,
            on_selected=lambda x, y, w, h, t: print(f"Selected: {x}, {y}, {w}x{h}"),
            on_cancelled=lambda: print("Cancelled")
        )
    """

    def __init__(self):
        """Initialize the manager."""
        self._overlay: Optional[CaptureOverlay] = None
        self._on_selected_callback = None
        self._on_cancelled_callback = None

    def start_capture(
        self,
        region_type: RegionType = RegionType.BODY,
        on_selected=None,
        on_cancelled=None
    ) -> None:
        """
        Start a new capture selection.

        Args:
            region_type: The type of region to capture.
            on_selected: Callback function (x, y, width, height, region_type).
            on_cancelled: Callback function for cancellation.
        """
        # Clean up any existing overlay
        if self._overlay:
            self._overlay.close()
            self._overlay.deleteLater()

        # Create new overlay
        self._overlay = CaptureOverlay(region_type)

        # Store callbacks
        self._on_selected_callback = on_selected
        self._on_cancelled_callback = on_cancelled

        # Connect signals
        if on_selected:
            self._overlay.region_selected.connect(self._handle_selected)
        if on_cancelled:
            self._overlay.selection_cancelled.connect(self._handle_cancelled)

        # Start selection
        self._overlay.show()

    def _handle_selected(self, x: int, y: int, width: int, height: int, region_type: str) -> None:
        """Handle region selection."""
        if self._on_selected_callback:
            self._on_selected_callback(x, y, width, height, region_type)
        self._cleanup()

    def _handle_cancelled(self) -> None:
        """Handle selection cancellation."""
        if self._on_cancelled_callback:
            self._on_cancelled_callback()
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up overlay resources."""
        if self._overlay:
            self._overlay.deleteLater()
            self._overlay = None
        self._on_selected_callback = None
        self._on_cancelled_callback = None

    def cancel(self) -> None:
        """Cancel any active capture session."""
        if self._overlay:
            self._overlay.close()
            self._cleanup()


# Convenience function for quick region selection
def select_capture_region(
    region_type: RegionType = RegionType.BODY
) -> Optional[tuple]:
    """
    Show the capture overlay and return the selected region.

    Note: This function blocks until selection is complete or cancelled.
    For non-blocking usage, use CaptureOverlay or CaptureOverlayManager directly.

    Args:
        region_type: The type of region to select.

    Returns:
        Tuple of (x, y, width, height, region_type_str) or None if cancelled.
    """
    result = None

    def on_selected(x, y, w, h, t):
        nonlocal result
        result = (x, y, w, h, t)

    overlay = CaptureOverlay(region_type)
    overlay.region_selected.connect(on_selected)
    overlay.show()

    # Process events until overlay is closed
    app = QApplication.instance()
    while overlay.isVisible():
        app.processEvents()

    return result


if __name__ == "__main__":
    # Demo / test code
    import sys

    app = QApplication(sys.argv)

    def on_region_selected(x, y, width, height, region_type):
        print(f"Region selected: {region_type}")
        print(f"  Position: ({x}, {y})")
        print(f"  Size: {width} x {height}")
        app.quit()

    def on_cancelled():
        print("Selection cancelled")
        app.quit()

    overlay = CaptureOverlay(RegionType.HEADER)
    overlay.region_selected.connect(on_region_selected)
    overlay.selection_cancelled.connect(on_cancelled)
    overlay.show()

    sys.exit(app.exec())
