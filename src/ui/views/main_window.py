"""
NoaLog Main Window

メインウィンドウUI実装。
ログ表示、プロファイル選択、キャプチャ操作を提供。
"""

import logging
from pathlib import Path
from typing import Optional, List

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
    QMenuBar,
    QMenu,
    QToolBar,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
    QLineEdit,
    QTextEdit,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QEvent
from PySide6.QtGui import QAction, QKeySequence, QIcon

from models import Profile, LogEntry
from config import Config

logger = logging.getLogger(__name__)


class LogEntryWidget(QFrame):
    """ログエントリ表示ウィジェット。"""

    clicked = Signal(str)  # entry_id
    double_clicked = Signal(str)  # entry_id for editing
    entry_edited = Signal(str, str, str)  # entry_id, field_name, new_value

    def __init__(self, entry: LogEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("logEntryFrame")
        self._editing = False
        self._edit_widget: Optional[QLineEdit] = None
        self._body_label: Optional[QLabel] = None
        self._setup_ui()

    def _setup_ui(self):
        """UIを構築。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # ヘッダー行（話者名 + 所属 + タイムスタンプ）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # 話者名（最大15文字で省略）
        speaker_name = self.entry.display_name or "不明"
        if len(speaker_name) > 15:
            speaker_name = speaker_name[:14] + "…"
        speaker_label = QLabel(speaker_name)
        speaker_label.setObjectName("speakerLabel")
        speaker_label.setMinimumWidth(40)
        speaker_label.setMaximumWidth(120)
        header_layout.addWidget(speaker_label)

        # 所属（最大10文字で省略）
        if self.entry.display_org:
            org_text = self.entry.display_org
            if len(org_text) > 10:
                org_text = org_text[:9] + "…"
            org_label = QLabel(f"({org_text})")
            org_label.setObjectName("organizationLabel")
            org_label.setStyleSheet("color: #6b7280; font-size: 11px;")
            org_label.setMaximumWidth(100)
            header_layout.addWidget(org_label)

        header_layout.addStretch()

        # タイムスタンプ（固定幅）
        from datetime import datetime
        try:
            ts = datetime.fromisoformat(self.entry.timestamp)
            timestamp_str = ts.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            timestamp_str = str(self.entry.timestamp)[:8]
        timestamp_label = QLabel(timestamp_str)
        timestamp_label.setObjectName("timestampLabel")
        timestamp_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        timestamp_label.setFixedWidth(60)
        timestamp_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(timestamp_label)

        layout.addLayout(header_layout)

        # 本文（プレビュー：最大60文字で省略、1行表示）
        body_text = self.entry.display_body or ""
        # 改行を空白に置換して1行にする
        body_text = body_text.replace('\n', ' ').replace('\r', '')
        if len(body_text) > 60:
            body_text = body_text[:57] + "..."
        self._body_label = QLabel(body_text)
        self._body_label.setWordWrap(False)  # 1行で表示
        self._body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._body_label.setStyleSheet("color: #374151;")
        layout.addWidget(self._body_label)

        # 固定高さを設定してリストの一貫性を保つ
        self.setFixedHeight(65)

    def mousePressEvent(self, event):
        """クリックイベント処理。"""
        super().mousePressEvent(event)
        self.clicked.emit(self.entry.id)

    def mouseDoubleClickEvent(self, event):
        """ダブルクリックで編集モード。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.entry.id)
            self._start_edit_mode()
        super().mouseDoubleClickEvent(event)

    def _start_edit_mode(self) -> None:
        """Start inline editing of the body text."""
        if self._editing:
            return

        self._editing = True

        # Create edit widget
        if self._body_label:
            self._edit_widget = QLineEdit(self.entry.display_body or "", self)
            self._edit_widget.setGeometry(self._body_label.geometry())
            self._edit_widget.setFocus()
            self._edit_widget.selectAll()

            # Connect signals
            self._edit_widget.returnPressed.connect(self._finish_edit)
            self._edit_widget.editingFinished.connect(self._finish_edit)

            # Install event filter for Escape
            self._edit_widget.installEventFilter(self)

            self._body_label.hide()
            self._edit_widget.show()

    def _finish_edit(self) -> None:
        """Finish editing and save changes."""
        if not self._editing or not self._edit_widget:
            return

        new_value = self._edit_widget.text().strip()
        old_value = self.entry.display_body or ""

        if new_value != old_value:
            self.entry.edited_body_text = new_value
            self.entry_edited.emit(self.entry.id, "body_text", new_value)

            # Update the label (1行表示、60文字で省略)
            display_text = new_value.replace('\n', ' ').replace('\r', '')
            if len(display_text) > 60:
                display_text = display_text[:57] + "..."
            if self._body_label:
                self._body_label.setText(display_text)

        self._cancel_edit()

    def _cancel_edit(self) -> None:
        """Cancel editing without saving."""
        if self._edit_widget:
            self._edit_widget.deleteLater()
            self._edit_widget = None

        if self._body_label:
            self._body_label.show()

        self._editing = False

    def eventFilter(self, obj, event) -> bool:
        """Handle Escape key to cancel edit."""
        if obj == self._edit_widget and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._cancel_edit()
                return True
        return super().eventFilter(obj, event)


class EditableLabel(QLabel):
    """Label that becomes editable on double-click."""

    value_changed = Signal(str, str)  # field_name, new_value

    def __init__(self, field_name: str, text: str = "", parent=None, multiline: bool = False):
        super().__init__(text, parent)
        self.field_name = field_name
        self._multiline = multiline
        self._edit_widget = None  # QLineEdit or QTextEdit
        self._editing = False
        self._original_text = ""
        self._finished = False  # Prevent double-triggering

    def mouseDoubleClickEvent(self, event):
        """Double-click to start editing."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_edit()
        super().mouseDoubleClickEvent(event)

    def _start_edit(self) -> None:
        """Start inline editing."""
        if self._editing:
            return

        self._editing = True
        self._finished = False
        self._original_text = self.text()

        # Get geometry with minimum height
        geo = self.geometry()
        min_height = max(geo.height(), 30)

        if self._multiline:
            # Use QTextEdit for multiline content
            from PySide6.QtWidgets import QTextEdit
            self._edit_widget = QTextEdit(self.parent())
            self._edit_widget.setPlainText(self._original_text)
            self._edit_widget.setFont(self.font())
            # Set reasonable height for multiline
            edit_height = max(min_height, 80)
            self._edit_widget.setGeometry(geo.x(), geo.y(), geo.width(), edit_height)
            self._edit_widget.setFocus()
            self._edit_widget.selectAll()
            # Install event filter for Enter and Escape
            self._edit_widget.installEventFilter(self)
        else:
            # Use QLineEdit for single-line content
            self._edit_widget = QLineEdit(self._original_text, self.parent())
            self._edit_widget.setGeometry(geo.x(), geo.y(), geo.width(), min_height)
            self._edit_widget.setFont(self.font())
            self._edit_widget.setFocus()
            self._edit_widget.selectAll()
            self._edit_widget.returnPressed.connect(self._finish_edit)
            self._edit_widget.installEventFilter(self)

        # Handle focus loss (clicking outside)
        self._edit_widget.focusOutEvent = self._on_focus_out

        self.hide()
        self._edit_widget.show()

    def _on_focus_out(self, event) -> None:
        """Handle focus loss - finish editing."""
        # Call original focusOutEvent
        if self._multiline:
            from PySide6.QtWidgets import QTextEdit
            QTextEdit.focusOutEvent(self._edit_widget, event)
        else:
            QLineEdit.focusOutEvent(self._edit_widget, event)
        # Finish editing
        self._finish_edit()

    def _finish_edit(self) -> None:
        """Finish editing."""
        if not self._editing or not self._edit_widget or self._finished:
            return

        self._finished = True  # Prevent double-triggering

        if self._multiline:
            new_value = self._edit_widget.toPlainText().strip()
        else:
            new_value = self._edit_widget.text().strip()

        if new_value != self._original_text:
            self.setText(new_value)
            self.value_changed.emit(self.field_name, new_value)

        self._cleanup_edit()

    def _cleanup_edit(self) -> None:
        """Clean up edit widget."""
        if self._edit_widget:
            self._edit_widget.deleteLater()
            self._edit_widget = None
        self.show()
        self._editing = False

    def eventFilter(self, obj, event) -> bool:
        """Handle Escape key to cancel edit, Enter to confirm."""
        if obj == self._edit_widget and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._cleanup_edit()
                return True
            # For multiline, Ctrl+Enter or just Enter confirms
            if self._multiline and event.key() == Qt.Key.Key_Return:
                if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                    self._finish_edit()
                    return True
        return super().eventFilter(obj, event)


class DetailPanel(QFrame):
    """詳細パネル - 選択したログエントリの詳細を表示。"""

    copy_requested = Signal(LogEntry)
    edit_requested = Signal(LogEntry)
    delete_requested = Signal(LogEntry)
    entry_field_changed = Signal(str, str, str)  # entry_id, field_name, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self._current_entry: Optional[LogEntry] = None
        self._setup_ui()

    def _setup_ui(self):
        """UIを構築。"""
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ヘッダー
        header = QLabel("詳細")
        header.setObjectName("titleLabel")
        layout.addWidget(header)

        # 編集説明
        edit_hint = QLabel("(ダブルクリックで編集)")
        edit_hint.setObjectName("timestampLabel")
        edit_hint.setStyleSheet("color: #8a9ab3; font-size: 11px;")
        layout.addWidget(edit_hint)

        # コンテンツエリア
        self.content_frame = QFrame()
        self.content_frame.setObjectName("profileCard")
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # 話者名
        self.name_title = QLabel("話者")
        self.name_title.setObjectName("subtitleLabel")
        content_layout.addWidget(self.name_title)

        self.name_label = EditableLabel("speaker_name", "")
        self.name_label.setObjectName("speakerLabel")
        self.name_label.setWordWrap(True)
        self.name_label.value_changed.connect(self._on_field_changed)
        content_layout.addWidget(self.name_label)

        # 所属
        self.org_title = QLabel("所属")
        self.org_title.setObjectName("subtitleLabel")
        content_layout.addWidget(self.org_title)

        self.org_label = EditableLabel("speaker_org", "")
        self.org_label.setObjectName("organizationLabel")
        self.org_label.setWordWrap(True)
        self.org_label.value_changed.connect(self._on_field_changed)
        content_layout.addWidget(self.org_label)

        # 本文
        self.body_title = QLabel("本文")
        self.body_title.setObjectName("subtitleLabel")
        content_layout.addWidget(self.body_title)

        self.body_label = EditableLabel("body_text", "", multiline=True)
        self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.body_label.value_changed.connect(self._on_field_changed)
        content_layout.addWidget(self.body_label)

        # タイムスタンプ
        self.timestamp_label = QLabel("")
        self.timestamp_label.setObjectName("timestampLabel")
        content_layout.addWidget(self.timestamp_label)

        content_layout.addStretch()

        layout.addWidget(self.content_frame, 1)

        # アクションボタン
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.copy_btn = QPushButton("コピー")
        self.copy_btn.setObjectName("primaryButton")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        button_layout.addWidget(self.copy_btn)

        self.edit_btn = QPushButton("編集")
        self.edit_btn.setObjectName("secondaryButton")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("削除")
        self.delete_btn.setObjectName("dangerButton")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self.delete_btn)

        layout.addLayout(button_layout)

        # 初期状態: 空
        self._show_empty_state()

    def _on_field_changed(self, field_name: str, new_value: str) -> None:
        """Handle field value change from editable labels."""
        if self._current_entry:
            self.entry_field_changed.emit(
                self._current_entry.id, field_name, new_value
            )
            logger.info(f"Field changed: {field_name} = {new_value}")

    def _show_empty_state(self):
        """空の状態を表示。"""
        self.name_label.setText("-")
        self.org_label.setText("-")
        self.body_label.setText("ログを選択すると詳細が表示されます")
        self.timestamp_label.setText("")
        self.copy_btn.setEnabled(False)
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self._current_entry = None

    def show_log_detail(self, entry: LogEntry):
        """ログエントリの詳細を表示。"""
        self._current_entry = entry

        # 話者名
        self.name_label.setText(entry.display_name or "(不明)")

        # 所属
        self.org_label.setText(entry.display_org or "(なし)")

        # 本文
        self.body_label.setText(entry.display_body or "(本文なし)")

        # タイムスタンプ
        from datetime import datetime
        try:
            ts = datetime.fromisoformat(entry.timestamp)
            timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            timestamp_str = str(entry.timestamp)
        self.timestamp_label.setText(f"記録: {timestamp_str}")

        # ボタン有効化
        self.copy_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    @Slot()
    def _on_copy_clicked(self):
        """コピーボタンクリック時の処理。"""
        if self._current_entry:
            self.copy_requested.emit(self._current_entry)

    @Slot()
    def _on_edit_clicked(self):
        """編集ボタンクリック時の処理。"""
        if self._current_entry:
            self.edit_requested.emit(self._current_entry)

    @Slot()
    def _on_delete_clicked(self):
        """削除ボタンクリック時の処理。"""
        if self._current_entry:
            self.delete_requested.emit(self._current_entry)


class MainWindow(QMainWindow):
    """NoaLogメインウィンドウ。"""

    # シグナル
    capture_requested = Signal()
    profile_changed = Signal(str)  # profile_id
    export_requested = Signal(str)  # format
    hotkey_settings_changed = Signal(dict)  # settings dict

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._profiles: List[Profile] = []
        self._current_profile: Optional[Profile] = None
        self._log_entries: List[LogEntry] = []

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._apply_theme()
        self._connect_signals()

        logger.info("MainWindow initialized")

    def _setup_ui(self):
        """UIを構築。"""
        self.setWindowTitle("NoaLog - OCR会話ログツール")
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)

        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # メインレイアウト
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # メインスプリッター（3ペイン）
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # 左サイドバー（プロファイル選択・キャプチャ操作）
        sidebar = self._create_sidebar()
        self.main_splitter.addWidget(sidebar)

        # 中央パネル（ログ一覧）
        log_panel = self._create_log_list()
        self.main_splitter.addWidget(log_panel)

        # 右パネル（詳細ビュー）
        self.detail_panel = DetailPanel()
        self.main_splitter.addWidget(self.detail_panel)

        # スプリッター比率（サイドバー:ログ一覧:詳細 = 220:450:350）
        self.main_splitter.setSizes([220, 450, 350])
        self.main_splitter.setStretchFactor(0, 0)  # サイドバーは固定幅
        self.main_splitter.setStretchFactor(1, 1)  # ログ一覧は伸縮
        self.main_splitter.setStretchFactor(2, 0)  # 詳細パネルは固定幅

    def _create_sidebar(self) -> QWidget:
        """サイドバーを作成。"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMaximumWidth(300)
        sidebar.setMinimumWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # タイトル
        title = QLabel("プロファイル")
        title.setObjectName("subtitleLabel")
        layout.addWidget(title)

        # プロファイル選択
        self.profile_combo = QComboBox()
        self.profile_combo.setPlaceholderText("プロファイルを選択...")
        layout.addWidget(self.profile_combo)

        # プロファイル管理ボタン
        profile_buttons = QHBoxLayout()
        profile_buttons.setSpacing(8)

        self.new_profile_btn = QPushButton("新規")
        self.new_profile_btn.setObjectName("secondaryButton")
        profile_buttons.addWidget(self.new_profile_btn)

        self.edit_profile_btn = QPushButton("編集")
        self.edit_profile_btn.setObjectName("secondaryButton")
        profile_buttons.addWidget(self.edit_profile_btn)

        layout.addLayout(profile_buttons)

        # 区切り線
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # キャプチャ設定
        capture_title = QLabel("キャプチャ")
        capture_title.setObjectName("subtitleLabel")
        layout.addWidget(capture_title)

        # ホットキー表示と設定ボタン
        hotkey_row = QHBoxLayout()
        self.hotkey_label = QLabel("ホットキー: Cmd+Option+L")
        hotkey_row.addWidget(self.hotkey_label)
        hotkey_row.addStretch()
        self.hotkey_settings_btn = QPushButton("設定")
        self.hotkey_settings_btn.setObjectName("secondaryButton")
        self.hotkey_settings_btn.setMaximumWidth(60)
        self.hotkey_settings_btn.clicked.connect(self._on_hotkey_settings_clicked)
        hotkey_row.addWidget(self.hotkey_settings_btn)
        layout.addLayout(hotkey_row)

        # キャプチャボタン
        self.capture_btn = QPushButton("キャプチャ実行")
        self.capture_btn.setObjectName("primaryButton")
        self.capture_btn.setMinimumHeight(48)
        layout.addWidget(self.capture_btn)

        layout.addStretch()

        # 統計情報
        stats_frame = QFrame()
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(0, 0, 0, 0)

        self.entry_count_label = QLabel("ログ数: 0")
        stats_layout.addWidget(self.entry_count_label)

        layout.addWidget(stats_frame)

        return sidebar

    def _create_log_list(self) -> QWidget:
        """ログ一覧パネルを作成（setup_log_list）。"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ヘッダー
        header_layout = QHBoxLayout()

        title = QLabel("会話ログ")
        title.setObjectName("titleLabel")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # フィルター/検索（将来用）
        self.search_placeholder = QLabel("")
        header_layout.addWidget(self.search_placeholder)

        layout.addLayout(header_layout)

        # ログリスト
        self.log_list = QListWidget()
        self.log_list.setAlternatingRowColors(True)
        self.log_list.setSpacing(2)
        self.log_list.setUniformItemSizes(True)  # 均一なサイズで描画を最適化
        self.log_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e5e5e5;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QListWidget::item {
                border-bottom: 1px solid #f0f0f0;
                padding: 2px;
            }
            QListWidget::item:selected {
                background-color: #e8f4fc;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        layout.addWidget(self.log_list)

        # フッター（エクスポートボタン）
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        self.export_btn = QPushButton("エクスポート")
        self.export_btn.setObjectName("secondaryButton")
        footer_layout.addWidget(self.export_btn)

        self.clear_btn = QPushButton("クリア")
        self.clear_btn.setObjectName("dangerButton")
        footer_layout.addWidget(self.clear_btn)

        layout.addLayout(footer_layout)

        return panel

    def setup_log_list(self):
        """ログリストを初期化（外部呼び出し用）。"""
        self.log_list.clear()
        self._log_entries.clear()
        self._update_stats()

    def setup_detail_view(self):
        """詳細ビューを初期化（外部呼び出し用）。"""
        self.detail_panel._show_empty_state()

    def _setup_menu(self):
        """メニューバーを設定。"""
        menubar = self.menuBar()

        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル")

        self.action_new_session = QAction("新規セッション", self)
        self.action_new_session.setShortcut(QKeySequence.New)
        file_menu.addAction(self.action_new_session)

        self.action_open = QAction("開く...", self)
        self.action_open.setShortcut(QKeySequence.Open)
        file_menu.addAction(self.action_open)

        self.action_save = QAction("保存", self)
        self.action_save.setShortcut(QKeySequence.Save)
        file_menu.addAction(self.action_save)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu("エクスポート")
        self.action_export_txt = QAction("テキスト (.txt)", self)
        export_menu.addAction(self.action_export_txt)
        self.action_export_csv = QAction("CSV (.csv)", self)
        export_menu.addAction(self.action_export_csv)
        self.action_export_json = QAction("JSON (.json)", self)
        export_menu.addAction(self.action_export_json)

        file_menu.addSeparator()

        self.action_quit = QAction("終了", self)
        self.action_quit.setShortcut(QKeySequence.Quit)
        file_menu.addAction(self.action_quit)

        # 編集メニュー
        edit_menu = menubar.addMenu("編集")

        self.action_undo = QAction("元に戻す", self)
        self.action_undo.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(self.action_undo)

        self.action_redo = QAction("やり直し", self)
        self.action_redo.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(self.action_redo)

        edit_menu.addSeparator()

        self.action_copy = QAction("コピー", self)
        self.action_copy.setShortcut(QKeySequence.Copy)
        edit_menu.addAction(self.action_copy)

        self.action_delete = QAction("削除", self)
        self.action_delete.setShortcut(QKeySequence.Delete)
        edit_menu.addAction(self.action_delete)

        # プロファイルメニュー
        profile_menu = menubar.addMenu("プロファイル")

        self.action_new_profile = QAction("新規プロファイル...", self)
        profile_menu.addAction(self.action_new_profile)

        self.action_edit_profile = QAction("プロファイル編集...", self)
        profile_menu.addAction(self.action_edit_profile)

        self.action_import_profile = QAction("インポート...", self)
        profile_menu.addAction(self.action_import_profile)

        self.action_export_profile = QAction("エクスポート...", self)
        profile_menu.addAction(self.action_export_profile)

        # 設定メニュー
        settings_menu = menubar.addMenu("設定")

        self.action_hotkey_settings = QAction("ホットキー設定...", self)
        self.action_hotkey_settings.triggered.connect(self._on_hotkey_settings_clicked)
        settings_menu.addAction(self.action_hotkey_settings)

        settings_menu.addSeparator()

        self.action_reset_confirmations = QAction("確認ダイアログを再表示", self)
        self.action_reset_confirmations.setToolTip("「次から確認しない」を解除します")
        self.action_reset_confirmations.triggered.connect(self._on_reset_confirmations)
        settings_menu.addAction(self.action_reset_confirmations)

        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ")

        self.action_about = QAction("NoaLogについて", self)
        help_menu.addAction(self.action_about)

        self.action_shortcuts = QAction("キーボードショートカット", self)
        help_menu.addAction(self.action_shortcuts)

    def _setup_toolbar(self):
        """ツールバーを設定。"""
        toolbar = QToolBar("メインツールバー")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # キャプチャアクション
        self.action_capture = QAction("キャプチャ", self)
        self.action_capture.setToolTip("画面をキャプチャしてOCR実行 (Cmd+Option+L)")
        toolbar.addAction(self.action_capture)

        toolbar.addSeparator()

        # プロファイル選択
        profile_label = QLabel(" プロファイル: ")
        toolbar.addWidget(profile_label)

        self.toolbar_profile_combo = QComboBox()
        self.toolbar_profile_combo.setMinimumWidth(150)
        toolbar.addWidget(self.toolbar_profile_combo)

    def _setup_statusbar(self):
        """ステータスバーを設定。"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # ステータスラベル
        self.status_label = QLabel("準備完了")
        self.statusbar.addWidget(self.status_label, 1)

        # OCRエンジン状態
        self.ocr_status_label = QLabel("OCR: 初期化中...")
        self.statusbar.addPermanentWidget(self.ocr_status_label)

    def _apply_theme(self):
        """テーマを適用。"""
        theme_path = Path(__file__).parent.parent / "styles" / "theme.qss"
        if theme_path.exists():
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            logger.info(f"Theme loaded from {theme_path}")
        else:
            logger.warning(f"Theme file not found: {theme_path}")

    def _connect_signals(self):
        """シグナルを接続。"""
        # キャプチャボタン
        self.capture_btn.clicked.connect(self.capture_requested.emit)
        self.action_capture.triggered.connect(self.capture_requested.emit)

        # プロファイル選択
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        self.toolbar_profile_combo.currentIndexChanged.connect(self._on_toolbar_profile_changed)

        # エクスポート
        self.export_btn.clicked.connect(lambda: self.export_requested.emit("txt"))
        self.action_export_txt.triggered.connect(lambda: self.export_requested.emit("txt"))
        self.action_export_csv.triggered.connect(lambda: self.export_requested.emit("csv"))
        self.action_export_json.triggered.connect(lambda: self.export_requested.emit("json"))

        # クリア
        self.clear_btn.clicked.connect(self._on_clear_clicked)

        # 終了
        self.action_quit.triggered.connect(self.close)

        # ログ一覧選択時に詳細パネルを更新
        self.log_list.currentRowChanged.connect(self._on_log_selected)

        # Detail panel events
        self.detail_panel.entry_field_changed.connect(self._on_entry_field_changed)
        self.detail_panel.delete_requested.connect(self._on_entry_delete_requested)
        self.detail_panel.copy_requested.connect(self._on_entry_copy_requested)

    @Slot()
    def _on_profile_changed(self):
        """プロファイル選択変更時の処理。"""
        index = self.profile_combo.currentIndex()
        if index >= 0 and index < len(self._profiles):
            profile = self._profiles[index]
            self._current_profile = profile
            self.profile_changed.emit(profile.id)

            # ツールバーのコンボも同期
            self.toolbar_profile_combo.blockSignals(True)
            self.toolbar_profile_combo.setCurrentIndex(index)
            self.toolbar_profile_combo.blockSignals(False)

            logger.info(f"Profile changed: {profile.name}")

    @Slot()
    def _on_toolbar_profile_changed(self):
        """ツールバーのプロファイル選択変更時の処理。"""
        index = self.toolbar_profile_combo.currentIndex()
        # サイドバーのコンボを同期
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)
        self._on_profile_changed()

    @Slot()
    def _on_clear_clicked(self):
        """クリアボタンクリック時の処理。"""
        reply = QMessageBox.question(
            self,
            "確認",
            "すべてのログを削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.clear_logs()

    def set_profiles(self, profiles: List[Profile]):
        """プロファイルリストを設定。"""
        self._profiles = profiles

        # コンボボックス更新
        self.profile_combo.clear()
        self.toolbar_profile_combo.clear()

        for profile in profiles:
            self.profile_combo.addItem(profile.name, profile.id)
            self.toolbar_profile_combo.addItem(profile.name, profile.id)

        if profiles:
            self.profile_combo.setCurrentIndex(0)
            self.toolbar_profile_combo.setCurrentIndex(0)
            self._current_profile = profiles[0]

    def add_log_entry(self, entry: LogEntry):
        """ログエントリを追加。"""
        self._log_entries.append(entry)

        # ウィジェット作成
        widget = LogEntryWidget(entry)
        widget.clicked.connect(lambda eid=entry.id: self._on_entry_clicked(eid))
        widget.entry_edited.connect(self._on_entry_field_changed)

        # リストアイテム作成
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())

        # リストに追加（先頭に）
        self.log_list.insertItem(0, item)
        self.log_list.setItemWidget(item, widget)

        # 統計更新
        self._update_stats()

        logger.debug(f"Log entry added: {entry.id}")

    def clear_logs(self):
        """ログをクリア。"""
        self._log_entries.clear()
        self.log_list.clear()
        self._update_stats()
        logger.info("Logs cleared")

    def _update_stats(self):
        """統計情報を更新。"""
        count = len(self._log_entries)
        self.entry_count_label.setText(f"ログ数: {count}")

    def set_status(self, message: str):
        """ステータスメッセージを設定。"""
        self.status_label.setText(message)

    def set_ocr_status(self, status: str):
        """OCRステータスを設定。"""
        self.ocr_status_label.setText(f"OCR: {status}")

    def get_current_profile(self) -> Optional[Profile]:
        """現在のプロファイルを取得。"""
        return self._current_profile

    def get_log_entries(self) -> List[LogEntry]:
        """ログエントリリストを取得。"""
        return self._log_entries.copy()

    @Slot(int)
    def _on_log_selected(self, row: int):
        """ログ選択時の処理。"""
        if row < 0 or row >= len(self._log_entries):
            self.detail_panel._show_empty_state()
            return

        # ログは先頭に追加されるため、インデックスを反転
        entry_index = len(self._log_entries) - 1 - row
        if 0 <= entry_index < len(self._log_entries):
            entry = self._log_entries[entry_index]
            self.show_log_detail(entry)

    def show_log_detail(self, entry: LogEntry):
        """ログエントリの詳細を表示。"""
        self.detail_panel.show_log_detail(entry)
        logger.debug(f"Showing detail for entry: {entry.id}")

    def get_detail_panel(self) -> DetailPanel:
        """詳細パネルを取得。"""
        return self.detail_panel

    @Slot(str, str, str)
    def _on_entry_field_changed(self, entry_id: str, field_name: str, new_value: str) -> None:
        """Handle entry field edit from detail panel."""
        # Find and update the entry
        for entry in self._log_entries:
            if entry.id == entry_id:
                if field_name == "speaker_name":
                    entry.edited_speaker_name = new_value
                elif field_name == "speaker_org":
                    entry.edited_speaker_org = new_value
                elif field_name == "body_text":
                    entry.edited_body_text = new_value

                logger.info(f"Entry {entry_id} field '{field_name}' updated to: {new_value}")

                # Refresh the list widget
                self._refresh_log_entry(entry)
                break

    def _refresh_log_entry(self, entry: LogEntry) -> None:
        """Refresh a specific log entry in the list."""
        # Find and update the widget
        for i in range(self.log_list.count()):
            item = self.log_list.item(i)
            widget = self.log_list.itemWidget(item)
            if isinstance(widget, LogEntryWidget) and widget.entry.id == entry.id:
                # Create updated widget
                new_widget = LogEntryWidget(entry)
                new_widget.clicked.connect(lambda eid=entry.id: self._on_entry_clicked(eid))
                new_widget.entry_edited.connect(self._on_entry_field_changed)
                item.setSizeHint(new_widget.sizeHint())
                self.log_list.setItemWidget(item, new_widget)
                break

    def _on_entry_clicked(self, entry_id: str) -> None:
        """Handle entry click from widget."""
        for entry in self._log_entries:
            if entry.id == entry_id:
                self.show_log_detail(entry)
                break

    @Slot()
    def _on_hotkey_settings_clicked(self) -> None:
        """ホットキー設定ダイアログを開く。"""
        from ui.widgets.hotkey_input import HotkeySettingsPanel
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("ホットキー設定")
        dialog.setMinimumSize(450, 300)

        layout = QVBoxLayout(dialog)

        # ホットキー設定パネル
        panel = HotkeySettingsPanel()

        # 現在の設定を読み込み
        config_data = self.config.load_config() if hasattr(self, 'config') else {}
        hotkey_config = config_data.get("hotkey", {})

        # キャプチャホットキー（2キー）
        # Changed default from cmd+shift to cmd+option to avoid Chrome extension conflicts
        capture_keys = hotkey_config.get("capture", ["cmd", "option", "l"])
        panel.add_hotkey_setting(
            action_id="capture",
            action_name="キャプチャ",
            required_keys=2,
            current_keys=capture_keys,
            default_keys=["cmd", "option", "l"]
        )

        # 範囲指定ホットキー（3キー）
        region_keys = hotkey_config.get("region_selection", ["cmd", "option", "r"])
        panel.add_hotkey_setting(
            action_id="region_selection",
            action_name="範囲指定",
            required_keys=3,
            current_keys=region_keys,
            default_keys=["cmd", "option", "r"]
        )

        layout.addWidget(panel)

        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 設定を保存
            new_settings = panel.get_all_settings()
            self._apply_hotkey_settings(new_settings)

    def _apply_hotkey_settings(self, settings: dict) -> None:
        """ホットキー設定を適用。"""
        # ホットキー表示を更新
        capture_keys = settings.get("capture", ["cmd", "option", "l"])
        keys_str = " + ".join(k.capitalize() for k in capture_keys)
        self.hotkey_label.setText(f"ホットキー: {keys_str}")

        # シグナルを発行（AppControllerで処理）
        self.hotkey_settings_changed.emit(settings)
        logger.info(f"Hotkey settings applied: {settings}")

    @Slot()
    def _on_reset_confirmations(self) -> None:
        """確認ダイアログの設定をリセット（再表示する）。"""
        config_data = self.config.load_config()

        # UI設定をリセット
        if "ui" in config_data:
            config_data["ui"]["skip_delete_confirmation"] = False
            # 他の確認スキップ設定もここに追加可能
            self.config.save_config(config_data)

        QMessageBox.information(
            self,
            "設定リセット",
            "確認ダイアログが再表示されるようになりました。"
        )
        logger.info("Confirmation dialogs reset to show again")

    @Slot(LogEntry)
    def _on_entry_delete_requested(self, entry: LogEntry) -> None:
        """ログエントリ削除要求の処理。"""
        # 確認スキップ設定を確認
        config_data = self.config.load_config()
        skip_delete_confirm = config_data.get("ui", {}).get("skip_delete_confirmation", False)

        if not skip_delete_confirm:
            # 「次から聞かない」チェックボックス付き確認ダイアログ
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("削除確認")
            msg_box.setText(f"このログエントリを削除しますか?")
            msg_box.setInformativeText(
                f"話者: {entry.display_name or '(不明)'}\n"
                f"本文: {(entry.display_body or '')[:50]}..."
            )
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)

            # チェックボックスを追加
            checkbox = QCheckBox("次から確認しない")
            msg_box.setCheckBox(checkbox)

            reply = msg_box.exec()

            # チェックボックスの状態を保存
            if checkbox.isChecked():
                config_data.setdefault("ui", {})["skip_delete_confirmation"] = True
                self.config.save_config(config_data)
                logger.info("Skip delete confirmation enabled")

            if reply != QMessageBox.Yes:
                return

        # エントリをリストから削除
        entry_id = entry.id
        entry_index = -1

        for i, e in enumerate(self._log_entries):
            if e.id == entry_id:
                entry_index = i
                break

        if entry_index < 0:
            logger.warning(f"Entry not found for deletion: {entry_id}")
            return

        # リストから削除
        self._log_entries.pop(entry_index)

        # リストウィジェットから削除（表示順は逆順）
        list_row = len(self._log_entries) - entry_index
        if 0 <= list_row < self.log_list.count():
            item = self.log_list.takeItem(list_row)
            del item

        # 詳細パネルをリセット
        self.detail_panel._show_empty_state()

        # 統計更新
        self._update_stats()

        self.set_status(f"ログを削除しました")
        logger.info(f"Entry deleted: {entry_id}")

    @Slot(LogEntry)
    def _on_entry_copy_requested(self, entry: LogEntry) -> None:
        """ログエントリコピー要求の処理。"""
        from PySide6.QtWidgets import QApplication

        # コピーするテキストを構築
        lines = []

        if entry.display_name:
            lines.append(f"話者: {entry.display_name}")
        if entry.display_org:
            lines.append(f"所属: {entry.display_org}")
        if entry.display_body:
            lines.append(f"\n{entry.display_body}")

        text = "\n".join(lines)

        # クリップボードにコピー
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        self.set_status("クリップボードにコピーしました")
        logger.info(f"Entry copied to clipboard: {entry.id}")
