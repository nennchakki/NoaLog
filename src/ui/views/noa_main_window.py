"""
NoaMainWindow - New Main Window Implementation

3ペイン + ヘッダー + ステータスバーのレイアウトを持つ新しいメインウィンドウ。
HaloIndicator, LogCard, CopyPanel, DetailPanelを統合。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QSplitter,
    QStatusBar,
    QLineEdit,
    QSizePolicy,
    QAbstractItemView,
    QScrollArea,
    QSpacerItem,
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QFont

from models import Profile, LogEntry, LogType
from config import Config
from ui.widgets.halo_indicator import HaloIndicator
from ui.widgets.log_card import LogCard
from ui.widgets.copy_panel import CopyPanel
from ui.widgets.detail_panel import DetailPanel
from ui.styles.tokens import COLORS, TYPOGRAPHY, SPACING, SHAPES, LAYOUT

logger = logging.getLogger(__name__)


class NoaMainWindow(QMainWindow):
    """
    NoaLog New Main Window.

    3-pane layout with header and status bar:
    - Header: HaloIndicator + Title + Hotkey display + Settings button
    - Left Pane: Profile selector, Stats, Settings
    - Center Pane: Search bar + LogCard list (with multi-selection)
    - Right Pane: DetailPanel + CopyPanel
    - Status Bar: OCR status, Last capture time, Entry count

    Signals:
        capture_requested: Emitted when capture is requested
        profile_changed(str): Emitted when profile changes (profile_id)
        hotkey_settings_changed(dict): Emitted when hotkey settings change
        export_requested(str): Emitted when export is requested (format)
    """

    # Signals
    capture_requested = Signal()
    profile_changed = Signal(str)
    hotkey_settings_changed = Signal(dict)
    export_requested = Signal(str)

    def __init__(self, config: Optional[Config] = None, parent: Optional[QWidget] = None):
        """
        Initialize the main window.

        Args:
            config: Application configuration
            parent: Parent widget
        """
        super().__init__(parent)

        self._config = config
        self._profiles: List[Profile] = []
        self._current_profile: Optional[Profile] = None
        self._log_entries: List[LogEntry] = []
        self._selected_entry_ids: List[str] = []
        self._multi_select_mode: bool = False
        self._search_text: str = ""
        self._last_capture_time: Optional[datetime] = None

        # UI Components
        self._halo_indicator: Optional[HaloIndicator] = None
        self._detail_panel: Optional[DetailPanel] = None
        self._copy_panel: Optional[CopyPanel] = None
        self._log_list: Optional[QListWidget] = None
        self._log_cards: Dict[str, LogCard] = {}

        self._setup_ui()
        self._setup_shortcuts()
        self._apply_theme()
        self._connect_signals()

        logger.info("NoaMainWindow initialized")

    # =========================================================================
    # UI Setup
    # =========================================================================

    def _setup_ui(self) -> None:
        """Build the main UI structure."""
        self.setWindowTitle("NoaLog")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout (header + content + status)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Content area (3-pane splitter)
        content_splitter = self._create_content_area()
        main_layout.addWidget(content_splitter, 1)

        # Status bar
        self._setup_statusbar()

    def _create_header(self) -> QFrame:
        """Create the header bar."""
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(LAYOUT.get("header_height", 56))
        header.setStyleSheet(f"""
            QFrame#headerFrame {{
                background-color: {COLORS['bg_dark']};
                border: none;
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Halo Indicator
        self._halo_indicator = HaloIndicator()
        layout.addWidget(self._halo_indicator)

        # App title
        title_label = QLabel("NoaLog")
        title_label.setObjectName("appTitle")
        title_label.setStyleSheet(f"""
            QLabel#appTitle {{
                color: {COLORS['text_on_dark']};
                font-size: {TYPOGRAPHY['text_xl']};
                font-weight: {TYPOGRAPHY['weight_semibold']};
            }}
        """)
        layout.addWidget(title_label)

        layout.addStretch()

        # Hotkey display
        self._hotkey_label = QLabel("Hotkey: Cmd+Option+L")
        self._hotkey_label.setObjectName("hotkeyLabel")
        self._hotkey_label.setStyleSheet(f"""
            QLabel#hotkeyLabel {{
                color: {COLORS['accent_light']};
                font-size: {TYPOGRAPHY['text_sm']};
            }}
        """)
        layout.addWidget(self._hotkey_label)

        layout.addSpacerItem(QSpacerItem(24, 0))

        # Settings button
        self._settings_btn = QPushButton()
        self._settings_btn.setObjectName("headerSettingsBtn")
        self._settings_btn.setText("Settings")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setStyleSheet(f"""
            QPushButton#headerSettingsBtn {{
                background-color: transparent;
                color: {COLORS['text_on_dark']};
                border: 1px solid {COLORS['accent']};
                border-radius: {SHAPES['radius_sm']};
                padding: 6px 12px;
                font-size: {TYPOGRAPHY['text_sm']};
            }}
            QPushButton#headerSettingsBtn:hover {{
                background-color: rgba(99, 198, 255, 0.2);
            }}
        """)
        self._settings_btn.clicked.connect(self._on_settings_clicked)
        layout.addWidget(self._settings_btn)

        return header

    def _create_content_area(self) -> QSplitter:
        """Create the 3-pane content area."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS['line_light']};
            }}
        """)

        # Left Pane
        left_pane = self._create_left_pane()
        splitter.addWidget(left_pane)

        # Center Pane
        center_pane = self._create_center_pane()
        splitter.addWidget(center_pane)

        # Right Pane
        right_pane = self._create_right_pane()
        splitter.addWidget(right_pane)

        # Set pane sizes
        left_width = LAYOUT.get("left_pane_width", 240)
        right_width = LAYOUT.get("right_pane_width", 360)
        splitter.setSizes([left_width, 500, right_width])

        # Stretch factors
        splitter.setStretchFactor(0, 0)  # Left: fixed
        splitter.setStretchFactor(1, 1)  # Center: stretch
        splitter.setStretchFactor(2, 0)  # Right: fixed

        return splitter

    def _create_left_pane(self) -> QFrame:
        """Create the left pane with profile selector and stats."""
        pane = QFrame()
        pane.setObjectName("leftPane")
        pane.setMinimumWidth(LAYOUT.get("left_pane_min", 200))
        pane.setMaximumWidth(LAYOUT.get("left_pane_max", 300))
        pane.setStyleSheet(f"""
            QFrame#leftPane {{
                background-color: {COLORS['bg_panel']};
                border-right: 1px solid {COLORS['line_light']};
            }}
        """)

        layout = QVBoxLayout(pane)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Profile section
        profile_section = self._create_profile_section()
        layout.addWidget(profile_section)

        # Stats section
        stats_section = self._create_stats_section()
        layout.addWidget(stats_section)

        layout.addStretch()

        # Settings section
        settings_section = self._create_settings_section()
        layout.addWidget(settings_section)

        return pane

    def _create_profile_section(self) -> QFrame:
        """Create the profile selector section."""
        section = QFrame()
        section.setObjectName("profileSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Section title
        title = QLabel("PROFILE")
        title.setObjectName("sectionTitle")
        title.setStyleSheet(f"""
            QLabel#sectionTitle {{
                color: {COLORS['text_tertiary']};
                font-size: {TYPOGRAPHY['text_xs']};
                font-weight: {TYPOGRAPHY['weight_semibold']};
                letter-spacing: 1px;
            }}
        """)
        layout.addWidget(title)

        # Profile combo
        self._profile_combo = QComboBox()
        self._profile_combo.setObjectName("profileSelector")
        self._profile_combo.setPlaceholderText("Select profile...")
        self._profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._profile_combo.setStyleSheet(f"""
            QComboBox#profileSelector {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_md']};
                padding: 10px 12px;
                font-size: {TYPOGRAPHY['text_base']};
                color: {COLORS['text_primary']};
            }}
            QComboBox#profileSelector:hover {{
                border-color: {COLORS['accent']};
            }}
            QComboBox#profileSelector::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox#profileSelector QAbstractItemView {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_md']};
                selection-background-color: {COLORS['bg_selected']};
            }}
        """)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        layout.addWidget(self._profile_combo)

        # Profile buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._new_profile_btn = QPushButton("New")
        self._new_profile_btn.setObjectName("secondaryButton")
        self._new_profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(self._new_profile_btn)

        self._edit_profile_btn = QPushButton("Edit")
        self._edit_profile_btn.setObjectName("secondaryButton")
        self._edit_profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(self._edit_profile_btn)

        layout.addLayout(btn_layout)

        return section

    def _create_stats_section(self) -> QFrame:
        """Create the statistics section."""
        section = QFrame()
        section.setObjectName("statsPanel")
        section.setStyleSheet(f"""
            QFrame#statsPanel {{
                background-color: {COLORS['bg_light']};
                border-radius: {SHAPES['radius_md']};
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Section title
        title = QLabel("STATISTICS")
        title.setObjectName("sectionTitle")
        title.setStyleSheet(f"""
            QLabel#sectionTitle {{
                color: {COLORS['text_tertiary']};
                font-size: {TYPOGRAPHY['text_xs']};
                font-weight: {TYPOGRAPHY['weight_semibold']};
                letter-spacing: 1px;
            }}
        """)
        layout.addWidget(title)

        # Entry count
        self._entry_count_label = QLabel("0")
        self._entry_count_label.setObjectName("statValue")
        self._entry_count_label.setStyleSheet(f"""
            QLabel#statValue {{
                color: {COLORS['text_primary']};
                font-size: {TYPOGRAPHY['text_2xl']};
                font-weight: {TYPOGRAPHY['weight_bold']};
            }}
        """)
        layout.addWidget(self._entry_count_label)

        entries_label = QLabel("entries")
        entries_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {TYPOGRAPHY['text_sm']};
        """)
        layout.addWidget(entries_label)

        return section

    def _create_settings_section(self) -> QFrame:
        """Create the settings section."""
        section = QFrame()
        section.setObjectName("settingsSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Capture button
        self._capture_btn = QPushButton("Capture")
        self._capture_btn.setObjectName("primaryButton")
        self._capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._capture_btn.setMinimumHeight(44)
        self._capture_btn.setStyleSheet(f"""
            QPushButton#primaryButton {{
                background-color: {COLORS['accent']};
                color: {COLORS['text_on_accent']};
                border: none;
                border-radius: {SHAPES['radius_md']};
                padding: 12px 24px;
                font-size: {TYPOGRAPHY['text_base']};
                font-weight: {TYPOGRAPHY['weight_medium']};
            }}
            QPushButton#primaryButton:hover {{
                background-color: {COLORS['accent_dark']};
            }}
        """)
        self._capture_btn.clicked.connect(self._on_capture_clicked)
        layout.addWidget(self._capture_btn)

        return section

    def _create_center_pane(self) -> QFrame:
        """Create the center pane with search and log list."""
        pane = QFrame()
        pane.setObjectName("centerPane")
        pane.setMinimumWidth(LAYOUT.get("center_pane_min", 400))
        pane.setStyleSheet(f"""
            QFrame#centerPane {{
                background-color: {COLORS['bg_light']};
            }}
        """)

        layout = QVBoxLayout(pane)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Search bar
        search_bar = self._create_search_bar()
        layout.addWidget(search_bar)

        # Log list
        self._log_list = QListWidget()
        self._log_list.setObjectName("logCardList")
        self._log_list.setSpacing(8)
        self._log_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._log_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._log_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._log_list.setStyleSheet(f"""
            QListWidget#logCardList {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#logCardList::item {{
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
            QListWidget#logCardList::item:selected {{
                background-color: transparent;
            }}
        """)
        self._log_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._log_list.currentRowChanged.connect(self._on_current_row_changed)
        layout.addWidget(self._log_list, 1)

        return pane

    def _create_search_bar(self) -> QFrame:
        """Create the search bar."""
        search_frame = QFrame()
        search_frame.setObjectName("searchFrame")

        layout = QHBoxLayout(search_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Search icon (using text for now)
        search_icon = QLabel()
        search_icon.setStyleSheet(f"""
            color: {COLORS['text_tertiary']};
            font-size: {TYPOGRAPHY['text_base']};
        """)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setObjectName("searchInput")
        self._search_input.setPlaceholderText("Search logs...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setStyleSheet(f"""
            QLineEdit#searchInput {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_md']};
                padding: 10px 16px;
                font-size: {TYPOGRAPHY['text_base']};
                color: {COLORS['text_primary']};
            }}
            QLineEdit#searchInput:focus {{
                border-color: {COLORS['accent']};
            }}
            QLineEdit#searchInput::placeholder {{
                color: {COLORS['text_tertiary']};
            }}
        """)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self._search_input, 1)

        return search_frame

    def _create_right_pane(self) -> QFrame:
        """Create the right pane with DetailPanel and CopyPanel."""
        pane = QFrame()
        pane.setObjectName("rightPane")
        pane.setMinimumWidth(LAYOUT.get("right_pane_min", 320))
        pane.setMaximumWidth(LAYOUT.get("right_pane_max", 450))
        pane.setStyleSheet(f"""
            QFrame#rightPane {{
                background-color: {COLORS['bg_panel']};
                border-left: 1px solid {COLORS['line_light']};
            }}
        """)

        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Detail Panel
        self._detail_panel = DetailPanel()
        layout.addWidget(self._detail_panel, 1)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['line_light']};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        # Copy Panel
        self._copy_panel = CopyPanel()
        self._copy_panel.setMaximumHeight(160)
        layout.addWidget(self._copy_panel)

        return pane

    def _setup_statusbar(self) -> None:
        """Setup the status bar."""
        self._statusbar = QStatusBar()
        self._statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {COLORS['bg_panel']};
                border-top: 1px solid {COLORS['line_light']};
                padding: 4px 16px;
            }}
            QStatusBar QLabel {{
                font-size: {TYPOGRAPHY['text_sm']};
                color: {COLORS['text_secondary']};
            }}
        """)
        self.setStatusBar(self._statusbar)

        # OCR status
        self._ocr_status_label = QLabel("OCR: Initializing...")
        self._statusbar.addWidget(self._ocr_status_label)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._statusbar.addWidget(spacer, 1)

        # Last capture time
        self._last_capture_label = QLabel("Last capture: -")
        self._statusbar.addWidget(self._last_capture_label)

        # Separator
        sep1 = QLabel("|")
        sep1.setStyleSheet(f"color: {COLORS['line']};")
        self._statusbar.addWidget(sep1)

        # Entry count
        self._status_entry_count_label = QLabel("Entries: 0")
        self._statusbar.addWidget(self._status_entry_count_label)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Navigation: Up/Down
        shortcut_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        shortcut_up.activated.connect(self._on_move_selection_up)

        shortcut_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        shortcut_down.activated.connect(self._on_move_selection_down)

        # Enter: Show detail
        shortcut_enter = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        shortcut_enter.activated.connect(self._on_show_detail)

        # E: Edit mode
        shortcut_edit = QShortcut(QKeySequence("E"), self)
        shortcut_edit.activated.connect(self._on_edit_mode)

        # Cmd/Ctrl+C: Copy
        shortcut_copy = QShortcut(QKeySequence.StandardKey.Copy, self)
        shortcut_copy.activated.connect(self._on_copy_selected)

        # Cmd/Ctrl+A: Select all
        shortcut_select_all = QShortcut(QKeySequence.StandardKey.SelectAll, self)
        shortcut_select_all.activated.connect(self._on_select_all)

        # Escape: Clear selection
        shortcut_escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        shortcut_escape.activated.connect(self._on_clear_selection)

    def _apply_theme(self) -> None:
        """Apply the application theme."""
        theme_path = Path(__file__).parent.parent / "styles" / "noa_theme.qss"
        if theme_path.exists():
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            logger.info(f"Theme loaded from {theme_path}")

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Detail panel signals
        if self._detail_panel:
            self._detail_panel.entry_updated.connect(self._on_entry_updated)

        # Copy panel signals
        if self._copy_panel:
            self._copy_panel.copy_requested.connect(self._on_copy_requested)

    # =========================================================================
    # Public Methods
    # =========================================================================

    def set_profiles(self, profiles: List[Profile]) -> None:
        """
        Set the profile list.

        Args:
            profiles: List of Profile objects
        """
        self._profiles = profiles

        self._profile_combo.clear()
        for profile in profiles:
            self._profile_combo.addItem(profile.name, profile.id)

        if profiles:
            self._profile_combo.setCurrentIndex(0)
            self._current_profile = profiles[0]

    def add_log_entry(self, entry: LogEntry) -> None:
        """
        Add a new log entry to the list.

        Args:
            entry: LogEntry to add
        """
        self._log_entries.insert(0, entry)

        # Create LogCard widget
        card = LogCard(entry)
        card.clicked.connect(lambda eid=entry.id: self._on_card_clicked(eid))
        card.double_clicked.connect(lambda eid=entry.id: self._on_card_double_clicked(eid))
        card.selection_toggled.connect(self._on_card_selection_toggled)

        # Store reference
        self._log_cards[entry.id] = card

        # Create list item
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, entry.id)
        item.setSizeHint(QSize(card.width(), card.height() + 8))

        # Insert at top
        self._log_list.insertItem(0, item)
        self._log_list.setItemWidget(item, card)

        # Update stats and copy panel
        self._update_stats()
        self._update_copy_panel()

        # Update last capture time
        self._last_capture_time = datetime.now()
        self._update_last_capture_display()

        logger.debug(f"Log entry added: {entry.id}")

    def clear_logs(self) -> None:
        """Clear all log entries."""
        self._log_entries.clear()
        self._log_cards.clear()
        self._selected_entry_ids.clear()
        self._log_list.clear()

        self._detail_panel.clear()
        self._copy_panel.clear_selection()

        self._update_stats()
        logger.info("Logs cleared")

    def set_status(self, message: str) -> None:
        """
        Set the status bar message.

        Args:
            message: Status message
        """
        self._statusbar.showMessage(message, 5000)

    def set_ocr_status(self, status: str) -> None:
        """
        Set the OCR status display.

        Args:
            status: OCR status string
        """
        self._ocr_status_label.setText(f"OCR: {status}")

    def get_current_profile(self) -> Optional[Profile]:
        """
        Get the currently selected profile.

        Returns:
            Current Profile or None
        """
        return self._current_profile

    def get_log_entries(self) -> List[LogEntry]:
        """
        Get all log entries.

        Returns:
            List of LogEntry objects
        """
        return self._log_entries.copy()

    def show_recording(self) -> None:
        """Show recording state on HaloIndicator."""
        if self._halo_indicator:
            self._halo_indicator.start_recording()

    def show_success(self) -> None:
        """Show success state on HaloIndicator."""
        if self._halo_indicator:
            self._halo_indicator.show_success()

    def show_failed(self) -> None:
        """Show failed state on HaloIndicator."""
        if self._halo_indicator:
            self._halo_indicator.show_failed()

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _update_stats(self) -> None:
        """Update statistics display."""
        count = len(self._log_entries)
        self._entry_count_label.setText(str(count))
        self._status_entry_count_label.setText(f"Entries: {count}")

    def _update_last_capture_display(self) -> None:
        """Update the last capture time display."""
        if self._last_capture_time:
            time_str = self._last_capture_time.strftime("%H:%M:%S")
            self._last_capture_label.setText(f"Last capture: {time_str}")

    def _update_copy_panel(self) -> None:
        """Update the copy panel with current entries and selection."""
        if self._copy_panel:
            self._copy_panel.set_entries(self._log_entries)
            self._copy_panel.set_selected_ids(self._selected_entry_ids)

    def _get_entry_by_id(self, entry_id: str) -> Optional[LogEntry]:
        """Get entry by ID."""
        for entry in self._log_entries:
            if entry.id == entry_id:
                return entry
        return None

    def _filter_entries(self, search_text: str) -> None:
        """Filter displayed entries based on search text."""
        search_lower = search_text.lower()

        for i in range(self._log_list.count()):
            item = self._log_list.item(i)
            entry_id = item.data(Qt.ItemDataRole.UserRole)
            entry = self._get_entry_by_id(entry_id)

            if entry:
                visible = (
                    search_lower in (entry.display_name or "").lower() or
                    search_lower in (entry.display_org or "").lower() or
                    search_lower in (entry.display_body or "").lower()
                )
                item.setHidden(not visible)

    def _update_hotkey_display(self, keys: List[str]) -> None:
        """Update the hotkey display in header."""
        if keys:
            keys_str = "+".join(k.capitalize() for k in keys)
            self._hotkey_label.setText(f"Hotkey: {keys_str}")

    # =========================================================================
    # Signal Handlers
    # =========================================================================

    @Slot()
    def _on_capture_clicked(self) -> None:
        """Handle capture button click."""
        self.show_recording()
        self.capture_requested.emit()

    @Slot(int)
    def _on_profile_changed(self, index: int) -> None:
        """Handle profile selection change."""
        if 0 <= index < len(self._profiles):
            self._current_profile = self._profiles[index]
            self.profile_changed.emit(self._current_profile.id)
            logger.info(f"Profile changed: {self._current_profile.name}")

    @Slot()
    def _on_settings_clicked(self) -> None:
        """Handle settings button click."""
        logger.info("Settings clicked")
        # TODO: Open settings dialog
        self.hotkey_settings_changed.emit({})

    @Slot(str)
    def _on_search_text_changed(self, text: str) -> None:
        """Handle search text change."""
        self._search_text = text
        self._filter_entries(text)

    @Slot()
    def _on_selection_changed(self) -> None:
        """Handle log list selection change."""
        selected_items = self._log_list.selectedItems()
        self._selected_entry_ids = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in selected_items
        ]

        # Update card selection states
        for entry_id, card in self._log_cards.items():
            card.is_selected = entry_id in self._selected_entry_ids

        # Update multi-select mode
        self._multi_select_mode = len(self._selected_entry_ids) > 1
        for card in self._log_cards.values():
            card.multi_select_mode = self._multi_select_mode

        # Update copy panel
        self._update_copy_panel()

    @Slot(int)
    def _on_current_row_changed(self, row: int) -> None:
        """Handle current row change in log list."""
        if row < 0:
            self._detail_panel.clear()
            return

        item = self._log_list.item(row)
        if item:
            entry_id = item.data(Qt.ItemDataRole.UserRole)
            entry = self._get_entry_by_id(entry_id)
            if entry:
                self._detail_panel.set_entry(entry)

    @Slot(str)
    def _on_card_clicked(self, entry_id: str) -> None:
        """Handle card click."""
        # Find and select the item
        for i in range(self._log_list.count()):
            item = self._log_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == entry_id:
                self._log_list.setCurrentItem(item)
                break

    @Slot(str)
    def _on_card_double_clicked(self, entry_id: str) -> None:
        """Handle card double-click."""
        entry = self._get_entry_by_id(entry_id)
        if entry:
            self._detail_panel.set_entry(entry)
            # TODO: Enter edit mode

    @Slot(str, bool)
    def _on_card_selection_toggled(self, entry_id: str, selected: bool) -> None:
        """Handle card selection toggle (checkbox)."""
        if selected and entry_id not in self._selected_entry_ids:
            self._selected_entry_ids.append(entry_id)
        elif not selected and entry_id in self._selected_entry_ids:
            self._selected_entry_ids.remove(entry_id)

        self._update_copy_panel()

    @Slot(str, dict)
    def _on_entry_updated(self, entry_id: str, changes: dict) -> None:
        """Handle entry update from detail panel."""
        entry = self._get_entry_by_id(entry_id)
        if not entry:
            return

        # Apply changes
        for field, value in changes.items():
            if field == "speaker_name":
                entry.edited_speaker_name = value if value else None
            elif field == "speaker_org":
                entry.edited_speaker_org = value if value else None
            elif field == "body_text":
                entry.edited_body_text = value if value else None

        # Refresh card
        if entry_id in self._log_cards:
            self._log_cards[entry_id].set_entry(entry)

        logger.info(f"Entry updated: {entry_id}, changes: {changes}")

    @Slot(str, list)
    def _on_copy_requested(self, format_str: str, entry_ids: list) -> None:
        """Handle copy request from copy panel."""
        self.export_requested.emit(format_str)
        logger.info(f"Copy requested: format={format_str}, entries={len(entry_ids)}")

    # =========================================================================
    # Keyboard Shortcut Handlers
    # =========================================================================

    @Slot()
    def _on_move_selection_up(self) -> None:
        """Move selection up."""
        current_row = self._log_list.currentRow()
        if current_row > 0:
            self._log_list.setCurrentRow(current_row - 1)

    @Slot()
    def _on_move_selection_down(self) -> None:
        """Move selection down."""
        current_row = self._log_list.currentRow()
        if current_row < self._log_list.count() - 1:
            self._log_list.setCurrentRow(current_row + 1)

    @Slot()
    def _on_show_detail(self) -> None:
        """Show detail for current selection."""
        current_item = self._log_list.currentItem()
        if current_item:
            entry_id = current_item.data(Qt.ItemDataRole.UserRole)
            entry = self._get_entry_by_id(entry_id)
            if entry:
                self._detail_panel.set_entry(entry)

    @Slot()
    def _on_edit_mode(self) -> None:
        """Enter edit mode for current selection."""
        # Focus on detail panel's editable area
        logger.debug("Edit mode requested")

    @Slot()
    def _on_copy_selected(self) -> None:
        """Copy selected entries."""
        if self._copy_panel:
            self._copy_panel._on_copy_clicked()

    @Slot()
    def _on_select_all(self) -> None:
        """Select all entries."""
        self._log_list.selectAll()

    @Slot()
    def _on_clear_selection(self) -> None:
        """Clear selection."""
        self._log_list.clearSelection()
        self._selected_entry_ids.clear()

        for card in self._log_cards.values():
            card.is_selected = False
            card.multi_select_mode = False

        self._update_copy_panel()


# Demo code
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = NoaMainWindow()

    # Create sample profiles
    profiles = [
        Profile(id="1", name="Blue Archive"),
        Profile(id="2", name="Game 2"),
    ]
    window.set_profiles(profiles)

    # Add sample entries
    for i in range(5):
        entry = LogEntry(
            id=f"entry_{i}",
            speaker_name=f"Speaker {i}",
            speaker_org=f"Organization {i}",
            body_text=f"This is sample log entry {i}. It contains some text for testing purposes.",
            log_type=LogType.DIALOGUE if i % 2 == 0 else LogType.NARRATION,
        )
        window.add_log_entry(entry)

    window.show()
    sys.exit(app.exec())
