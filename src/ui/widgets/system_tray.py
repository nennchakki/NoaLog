"""
NoaLog System Tray Icon

Provides a menu bar icon for macOS with quick access to capture functions.
Especially useful when working in fullscreen applications where hotkeys
may not work reliably due to macOS Space isolation.
"""

import logging
import platform
from typing import Optional, Callable

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PySide6.QtCore import Signal, QObject

logger = logging.getLogger(__name__)


def create_tray_icon_pixmap(size: int = 22) -> QPixmap:
    """
    Create a simple tray icon pixmap.

    Args:
        size: Icon size in pixels (default 22 for macOS menu bar)

    Returns:
        QPixmap: The generated icon
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw a simple "N" for NoaLog
    # Use template image colors (will be inverted on dark menu bar)
    if platform.system() == "Darwin":
        # macOS: Use black which will become white on dark menu bars
        color = QColor(0, 0, 0)
    else:
        # Windows/Linux: Use a visible color
        color = QColor(94, 179, 240)  # NoaLog accent blue

    painter.setPen(color)
    painter.setBrush(color)

    # Draw a stylized "N" shape
    margin = size * 0.15
    inner_size = size - (margin * 2)

    # Left vertical bar
    painter.drawRect(int(margin), int(margin), int(inner_size * 0.25), int(inner_size))

    # Right vertical bar
    painter.drawRect(int(size - margin - inner_size * 0.25), int(margin),
                     int(inner_size * 0.25), int(inner_size))

    # Diagonal connector (simplified as a rectangle)
    painter.save()
    painter.translate(size / 2, size / 2)
    painter.rotate(-30)
    painter.drawRect(int(-inner_size * 0.4), int(-inner_size * 0.1),
                     int(inner_size * 0.8), int(inner_size * 0.2))
    painter.restore()

    painter.end()

    return pixmap


class SystemTrayManager(QObject):
    """
    Manages the system tray icon and menu for NoaLog.

    Provides quick access to:
    - Quick Capture (uses saved regions)
    - Region Selection (opens overlay)
    - Show/Hide main window
    - Quit

    Signals:
        quick_capture_triggered: Emitted when Quick Capture is selected
        region_selection_triggered: Emitted when Region Selection is selected
        show_window_triggered: Emitted when Show Window is selected
        quit_triggered: Emitted when Quit is selected
    """

    quick_capture_triggered = Signal()
    region_selection_triggered = Signal()
    show_window_triggered = Signal()
    quit_triggered = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize the system tray manager.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None
        self._is_available = QSystemTrayIcon.isSystemTrayAvailable()

        if not self._is_available:
            logger.warning("System tray is not available on this system")
            return

        self._setup_tray_icon()

    def _setup_tray_icon(self) -> None:
        """Set up the system tray icon and menu."""
        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self)

        # Create icon
        icon = QIcon(create_tray_icon_pixmap())
        self._tray_icon.setIcon(icon)

        # Create menu
        self._menu = QMenu()

        # Quick Capture action (uses saved regions - works in fullscreen)
        self._quick_capture_action = QAction("Quick Capture", self._menu)
        self._quick_capture_action.setToolTip(
            "Capture using saved regions (works in fullscreen)"
        )
        self._quick_capture_action.triggered.connect(self._on_quick_capture)
        self._menu.addAction(self._quick_capture_action)

        # Region Selection action
        self._region_action = QAction("Select Regions...", self._menu)
        self._region_action.setToolTip(
            "Select header and body capture regions"
        )
        self._region_action.triggered.connect(self._on_region_selection)
        self._menu.addAction(self._region_action)

        self._menu.addSeparator()

        # Show/Hide window action
        self._show_action = QAction("Show NoaLog", self._menu)
        self._show_action.triggered.connect(self._on_show_window)
        self._menu.addAction(self._show_action)

        self._menu.addSeparator()

        # Quit action
        self._quit_action = QAction("Quit", self._menu)
        self._quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(self._quit_action)

        # Set menu
        self._tray_icon.setContextMenu(self._menu)

        # Set tooltip
        self._tray_icon.setToolTip("NoaLog - Click for quick capture menu")

        # Connect activation signal (for left-click on some platforms)
        self._tray_icon.activated.connect(self._on_tray_activated)

        logger.info("System tray icon created")

    def _on_quick_capture(self) -> None:
        """Handle Quick Capture action."""
        logger.debug("Quick Capture triggered from tray")
        self.quick_capture_triggered.emit()

    def _on_region_selection(self) -> None:
        """Handle Region Selection action."""
        logger.debug("Region Selection triggered from tray")
        self.region_selection_triggered.emit()

    def _on_show_window(self) -> None:
        """Handle Show Window action."""
        logger.debug("Show Window triggered from tray")
        self.show_window_triggered.emit()

    def _on_quit(self) -> None:
        """Handle Quit action."""
        logger.debug("Quit triggered from tray")
        self.quit_triggered.emit()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Handle tray icon activation.

        On macOS, clicking the menu bar icon shows the menu.
        On Windows, left-click might trigger quick capture.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - on Windows, trigger quick capture
            if platform.system() == "Windows":
                self._on_quick_capture()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click - show window
            self._on_show_window()

    def show(self) -> None:
        """Show the system tray icon."""
        if self._tray_icon and self._is_available:
            self._tray_icon.show()
            logger.info("System tray icon shown")

    def hide(self) -> None:
        """Hide the system tray icon."""
        if self._tray_icon:
            self._tray_icon.hide()
            logger.info("System tray icon hidden")

    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        timeout_ms: int = 3000
    ) -> None:
        """
        Show a notification message from the tray icon.

        Args:
            title: Notification title
            message: Notification message
            icon: Icon type (Information, Warning, Critical)
            timeout_ms: Display duration in milliseconds
        """
        if self._tray_icon and self._is_available:
            self._tray_icon.showMessage(title, message, icon, timeout_ms)

    def update_quick_capture_status(self, enabled: bool, tooltip: str = "") -> None:
        """
        Update the Quick Capture action status.

        Args:
            enabled: Whether quick capture is available
            tooltip: Optional tooltip text
        """
        if self._quick_capture_action:
            self._quick_capture_action.setEnabled(enabled)
            if tooltip:
                self._quick_capture_action.setToolTip(tooltip)

    @property
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return self._is_available

    @property
    def is_visible(self) -> bool:
        """Check if the tray icon is currently visible."""
        return self._tray_icon.isVisible() if self._tray_icon else False
