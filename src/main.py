"""
NoaLog - Cross-platform OCR Conversation Log Tool

Main entry point for the application.
"""

import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("NOALOG_DEV") else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Setup environment for development or production."""
    # Add src to path for imports
    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Set development flag if running from source
    if not getattr(sys, 'frozen', False):
        os.environ["NOALOG_DEV"] = "1"


def check_permissions():
    """Check required system permissions (macOS)."""
    if sys.platform != "darwin":
        return True, []

    missing = []

    # Check Screen Recording permission
    # This will be implemented in utils/permissions.py
    # For now, we'll check when capture is first attempted

    # Check Accessibility permission
    # This will be implemented in utils/permissions.py
    # For now, we'll check when hotkey is first registered

    return len(missing) == 0, missing


def main():
    """Main entry point."""
    setup_environment()

    # Import after environment setup
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    # Enable high DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("NoaLog")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("NoaLog")

    # Check permissions
    ok, missing = check_permissions()
    if not ok:
        logger.warning(f"Missing permissions: {missing}")

    # Import modules
    from config import Config
    from models import Profile, Hotkey, Rect
    from ui.widgets.system_tray import SystemTrayManager
    from app_controller import AppController, AppControllerError

    # Use new Noa UI by default, set NOALOG_CLASSIC=1 for old UI
    use_classic_ui = os.environ.get("NOALOG_CLASSIC", "0") == "1"
    if use_classic_ui:
        from ui.views.main_window import MainWindow
        logger.info("Using classic UI")
    else:
        from ui.views.noa_main_window import NoaMainWindow as MainWindow
        logger.info("Using new Noa UI")

    # Load configuration
    config = Config()

    # Create main window first
    window = MainWindow(config)

    # Create system tray manager for menu bar access (especially for fullscreen)
    tray_manager = SystemTrayManager()

    # Create and initialize AppController
    controller = AppController(config)

    try:
        # Initialize controller (ScreenCapture, HotkeyManager, OCREngine)
        controller.initialize()
    except AppControllerError as e:
        logger.error(f"Failed to initialize controller: {e}")
        # Show warning but continue - some features may not work
        window.set_status(f"Warning: {e}")

    # Connect controller to window
    controller.set_main_window(window)

    # Load saved profiles (or empty list if none exist)
    saved_profiles = controller.load_profiles()

    if saved_profiles:
        controller.set_profiles(saved_profiles)
    else:
        # No profiles - show guidance to user
        controller.set_profiles([])
        window.set_status("プロファイルがありません。「新規」ボタンからプロファイルを作成してください。")
        logger.info("No profiles found. User should create a new profile.")

    # Register global hotkeys from config
    controller.register_global_hotkeys()

    # Start hotkey listener
    controller.start_hotkey_listener()

    # Connect system tray signals
    if tray_manager.is_available:
        # Quick Capture from tray - uses saved regions (works in fullscreen)
        tray_manager.quick_capture_triggered.connect(controller.trigger_quick_capture)

        # Region Selection from tray
        tray_manager.region_selection_triggered.connect(controller.start_region_selection)

        # Show Window from tray
        def show_window():
            window.show()
            window.raise_()
            window.activateWindow()
        tray_manager.show_window_triggered.connect(show_window)

        # Quit from tray
        tray_manager.quit_triggered.connect(app.quit)

        # Show tray icon
        tray_manager.show()
        logger.info("System tray initialized for menu bar access")

        # Update tray status based on profile
        def update_tray_status():
            profile = controller._current_profile
            if profile and (profile.header_rect or profile.body_rect):
                tray_manager.update_quick_capture_status(
                    True,
                    f"Quick capture using profile: {profile.name}"
                )
            else:
                tray_manager.update_quick_capture_status(
                    False,
                    "No capture regions defined - select regions first"
                )

        controller.profile_changed.connect(lambda p: update_tray_status())
        controller.region_selection_completed.connect(lambda h, b: update_tray_status())

        # Initial status update
        update_tray_status()

    # Update UI status
    ocr_info = controller.get_ocr_engine_info()
    if ocr_info:
        window.set_ocr_status(ocr_info["engine_type"])
    else:
        window.set_ocr_status("Not available")

    window.set_status("Ready")

    # Show window
    window.show()
    logger.info("NoaLog started")

    # Cleanup on exit
    def cleanup():
        """Cleanup resources on application exit."""
        logger.info("Cleaning up...")
        controller.shutdown()

    app.aboutToQuit.connect(cleanup)

    # Run event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
