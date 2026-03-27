"""
NoaLog Profile Editor Dialog

プロファイル編集ダイアログUI実装。
プロファイル名、説明、キャプチャ領域、ホットキーの設定が可能。
"""

import logging
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFrame,
    QDialogButtonBox,
    QKeySequenceEdit,
    QMessageBox,
    QSizePolicy,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QKeySequence

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Profile, Rect, Hotkey

logger = logging.getLogger(__name__)


class RectEditorWidget(QGroupBox):
    """
    矩形領域（Rect）編集ウィジェット。
    x, y, width, height の4つの値を入力可能。
    """

    value_changed = Signal()

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._setup_ui()

    def _setup_ui(self):
        """UIを構築。"""
        layout = QGridLayout(self)
        layout.setSpacing(8)

        # X座標
        layout.addWidget(QLabel("X:"), 0, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 9999)
        self.x_spin.setSuffix(" px")
        self.x_spin.valueChanged.connect(lambda _: self.value_changed.emit())
        layout.addWidget(self.x_spin, 0, 1)

        # Y座標
        layout.addWidget(QLabel("Y:"), 0, 2)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 9999)
        self.y_spin.setSuffix(" px")
        self.y_spin.valueChanged.connect(lambda _: self.value_changed.emit())
        layout.addWidget(self.y_spin, 0, 3)

        # 幅
        layout.addWidget(QLabel("Width:"), 1, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 9999)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(lambda _: self.value_changed.emit())
        layout.addWidget(self.width_spin, 1, 1)

        # 高さ
        layout.addWidget(QLabel("Height:"), 1, 2)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 9999)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(lambda _: self.value_changed.emit())
        layout.addWidget(self.height_spin, 1, 3)

        # プレビュー情報
        self.preview_label = QLabel("")
        self.preview_label.setObjectName("subtitleLabel")
        layout.addWidget(self.preview_label, 2, 0, 1, 4)

        # 初期値
        self.width_spin.setValue(100)
        self.height_spin.setValue(50)

        self._update_preview()
        self.value_changed.connect(self._update_preview)

    def _update_preview(self):
        """プレビュー情報を更新。"""
        x = self.x_spin.value()
        y = self.y_spin.value()
        w = self.width_spin.value()
        h = self.height_spin.value()
        self.preview_label.setText(f"Area: ({x}, {y}) - ({x + w}, {y + h})")

    def get_rect(self) -> Optional[Rect]:
        """現在の値からRectを取得。"""
        return Rect(
            x=self.x_spin.value(),
            y=self.y_spin.value(),
            width=self.width_spin.value(),
            height=self.height_spin.value(),
        )

    def set_rect(self, rect: Optional[Rect]):
        """Rectの値を設定。"""
        if rect:
            self.x_spin.setValue(rect.x)
            self.y_spin.setValue(rect.y)
            self.width_spin.setValue(rect.width)
            self.height_spin.setValue(rect.height)
        else:
            self.x_spin.setValue(0)
            self.y_spin.setValue(0)
            self.width_spin.setValue(100)
            self.height_spin.setValue(50)

    def clear(self):
        """値をクリア。"""
        self.set_rect(None)


class HotkeyEditorWidget(QGroupBox):
    """
    ホットキー編集ウィジェット。
    キーシーケンスの設定が可能。
    """

    value_changed = Signal()

    def __init__(self, title: str = "Hotkey", parent=None):
        super().__init__(title, parent)
        self._setup_ui()

    def _setup_ui(self):
        """UIを構築。"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 説明ラベル
        description = QLabel("Click and press the key combination you want to use:")
        description.setWordWrap(True)
        description.setObjectName("subtitleLabel")
        layout.addWidget(description)

        # キーシーケンス入力
        input_layout = QHBoxLayout()

        self.key_sequence_edit = QKeySequenceEdit()
        # Note: QKeySequenceEdit doesn't support setPlaceholderText
        self.key_sequence_edit.keySequenceChanged.connect(self._on_key_changed)
        input_layout.addWidget(self.key_sequence_edit, 1)

        # クリアボタン
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.clicked.connect(self._clear_hotkey)
        input_layout.addWidget(self.clear_btn)

        layout.addLayout(input_layout)

        # 現在の設定表示
        self.current_label = QLabel("Current: None")
        layout.addWidget(self.current_label)

    def _on_key_changed(self):
        """キーシーケンス変更時の処理。"""
        seq = self.key_sequence_edit.keySequence()
        if seq.isEmpty():
            self.current_label.setText("Current: None")
        else:
            self.current_label.setText(f"Current: {seq.toString()}")
        self.value_changed.emit()

    def _clear_hotkey(self):
        """ホットキーをクリア。"""
        self.key_sequence_edit.clear()
        self.current_label.setText("Current: None")
        self.value_changed.emit()

    def get_hotkey(self) -> Optional[Hotkey]:
        """現在の値からHotkeyを取得。"""
        seq = self.key_sequence_edit.keySequence()
        if seq.isEmpty():
            return None

        # キーシーケンスを分解してリストに変換
        seq_str = seq.toString()
        if not seq_str:
            return None

        keys = self._parse_key_sequence(seq_str)
        if keys:
            return Hotkey(keys=keys)
        return None

    def _parse_key_sequence(self, seq_str: str) -> List[str]:
        """キーシーケンス文字列をキーリストに変換。"""
        # Qt format: "Ctrl+Shift+L" -> ["ctrl", "shift", "l"]
        if not seq_str:
            return []

        keys = []
        parts = seq_str.split("+")
        for part in parts:
            part = part.strip().lower()
            # Qtのキー名をpynputなどで使える形式に変換
            # macOS: Qt Ctrl = ⌘ Command, Qt Meta = ⌃ Control
            # Windows: Qt Ctrl = Ctrl, Qt Meta = Win key
            if sys.platform == "darwin":
                key_map = {
                    "ctrl": "cmd",      # Qt Ctrl = ⌘ Command
                    "control": "cmd",
                    "meta": "ctrl",     # Qt Meta = ⌃ Control
                    "shift": "shift",
                    "alt": "alt",
                    "cmd": "cmd",
                }
            else:
                key_map = {
                    "ctrl": "ctrl",
                    "control": "ctrl",
                    "shift": "shift",
                    "alt": "alt",
                    "meta": "meta",
                    "cmd": "cmd",
                }
            normalized = key_map.get(part, part)
            keys.append(normalized)
        return keys

    def set_hotkey(self, hotkey: Optional[Hotkey]):
        """Hotkeyの値を設定。"""
        if hotkey and hotkey.keys:
            # キーリストをQt形式に変換
            # macOS: pynput "ctrl" = ⌃ Control = Qt Meta, "cmd" = ⌘ = Qt Ctrl
            # Windows: pynput "ctrl" = Ctrl = Qt Ctrl
            qt_keys = []
            for key in hotkey.keys:
                if sys.platform == "darwin":
                    key_map = {
                        "ctrl": "Meta",     # ⌃ Control → Qt Meta
                        "cmd": "Ctrl",      # ⌘ Command → Qt Ctrl
                        "shift": "Shift",
                        "alt": "Alt",
                    }
                else:
                    key_map = {
                        "ctrl": "Ctrl",
                        "shift": "Shift",
                        "alt": "Alt",
                        "cmd": "Meta",
                    }
                qt_keys.append(key_map.get(key.lower(), key.capitalize()))

            seq_str = "+".join(qt_keys)
            self.key_sequence_edit.setKeySequence(QKeySequence(seq_str))
            self.current_label.setText(f"Current: {seq_str}")
        else:
            self.key_sequence_edit.clear()
            self.current_label.setText("Current: None")

    def clear(self):
        """値をクリア。"""
        self._clear_hotkey()


class ProfileEditorDialog(QDialog):
    """
    プロファイル編集ダイアログ。

    Features:
    - Profile name and description editing
    - Header rect (capture region) configuration
    - Body rect (capture region) configuration
    - Hotkey configuration
    - Save/Cancel buttons

    Usage:
        dialog = ProfileEditorDialog(parent)
        dialog.set_profile(existing_profile)  # For editing
        if dialog.exec() == QDialog.Accepted:
            profile = dialog.get_profile()
    """

    # Signals
    profile_saved = Signal(object)  # Profile

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile: Optional[Profile] = None
        self._is_new = True

        self._setup_ui()
        self._apply_theme()
        self._connect_signals()

        logger.info("ProfileEditorDialog initialized")

    def _setup_ui(self):
        """UIを構築。"""
        self.setWindowTitle("Profile Editor")
        self.setMinimumSize(520, 600)
        self.resize(600, 800)
        self.setModal(True)

        # メインレイアウト（ダイアログ全体）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ヘッダー部分（タイトル - 固定）
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #0B1B2B;
                padding: 16px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)

        title_label = QLabel("Edit Profile")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)

        main_layout.addWidget(header_frame)

        # スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F6F1E6;
            }
            QScrollBar:vertical {
                background-color: #E8E3D8;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #C0B8A8;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #A8A090;
            }
        """)

        # スクロール内のコンテンツウィジェット
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(24, 24, 24, 24)
        scroll_layout.setSpacing(20)

        # === セクション 1: 基本情報 ===
        basic_group = QGroupBox("Basic Information")
        basic_group.setStyleSheet(self._get_groupbox_style())
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setContentsMargins(16, 20, 16, 16)
        basic_layout.setSpacing(12)

        # プロファイル名
        name_label = QLabel("Profile Name")
        name_label.setStyleSheet("font-weight: bold; color: #333;")
        basic_layout.addWidget(name_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter profile name...")
        self.name_edit.setStyleSheet(self._get_input_style())
        self.name_edit.setMinimumHeight(36)
        basic_layout.addWidget(self.name_edit)

        # 説明
        desc_label = QLabel("Description (Optional)")
        desc_label.setStyleSheet("font-weight: bold; color: #333; margin-top: 8px;")
        basic_layout.addWidget(desc_label)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter profile description...")
        self.description_edit.setStyleSheet(self._get_input_style())
        self.description_edit.setFixedHeight(70)
        basic_layout.addWidget(self.description_edit)

        scroll_layout.addWidget(basic_group)

        # === セクション 2: キャプチャ領域 ===
        capture_group = QGroupBox("Capture Regions")
        capture_group.setStyleSheet(self._get_groupbox_style())
        capture_layout = QVBoxLayout(capture_group)
        capture_layout.setContentsMargins(16, 20, 16, 16)
        capture_layout.setSpacing(16)

        capture_desc = QLabel("Define the screen regions to capture for OCR processing.")
        capture_desc.setWordWrap(True)
        capture_desc.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 8px;")
        capture_layout.addWidget(capture_desc)

        # ヘッダー領域
        self.header_rect_editor = RectEditorWidget("Header Region (名前)")
        capture_layout.addWidget(self.header_rect_editor)

        # ボディ領域
        self.body_rect_editor = RectEditorWidget("Body Region (本文)")
        capture_layout.addWidget(self.body_rect_editor)

        # 語り部領域
        self.narrator_rect_editor = RectEditorWidget("Narrator Region (語り部)")
        capture_layout.addWidget(self.narrator_rect_editor)

        # 語り部ラベル設定
        narrator_label_layout = QHBoxLayout()
        narrator_label_desc = QLabel("Narrator Label:")
        narrator_label_desc.setStyleSheet("color: #666; font-size: 12px; min-width: 90px;")
        narrator_label_layout.addWidget(narrator_label_desc)

        self.narrator_label_edit = QLineEdit()
        self.narrator_label_edit.setPlaceholderText("語り部")
        self.narrator_label_edit.setText("語り部")
        self.narrator_label_edit.setStyleSheet(self._get_input_style())
        self.narrator_label_edit.setMinimumHeight(32)
        narrator_label_layout.addWidget(self.narrator_label_edit, 1)

        capture_layout.addLayout(narrator_label_layout)

        scroll_layout.addWidget(capture_group)

        # === セクション 3: ホットキー ===
        hotkey_group = QGroupBox("Hotkey Settings")
        hotkey_group.setStyleSheet(self._get_groupbox_style())
        hotkey_layout = QVBoxLayout(hotkey_group)
        hotkey_layout.setContentsMargins(16, 20, 16, 16)
        hotkey_layout.setSpacing(12)

        self.hotkey_editor = HotkeyEditorWidget("Capture Hotkey (名前+本文)")
        hotkey_layout.addWidget(self.hotkey_editor)

        self.narrator_hotkey_editor = HotkeyEditorWidget("Narrator Hotkey (語り部)")
        hotkey_layout.addWidget(self.narrator_hotkey_editor)

        scroll_layout.addWidget(hotkey_group)

        # スペーサー
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)

        # === フッター部分（ボタン - 固定） ===
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #E0D8C8;
            }
        """)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.setSpacing(12)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8E3D8;
                color: #333;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #D8D3C8;
            }
        """)
        footer_layout.addWidget(self.cancel_btn)

        footer_layout.addStretch()

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.setMinimumWidth(100)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #63C6FF;
                color: #0B1B2B;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4AB8F5;
            }
        """)
        footer_layout.addWidget(self.save_btn)

        main_layout.addWidget(footer_frame)

    def _get_groupbox_style(self) -> str:
        """GroupBoxのスタイルを取得。"""
        return """
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E0D8C8;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                padding: 0 8px;
                background-color: #FFFFFF;
                color: #0B1B2B;
            }
        """

    def _get_input_style(self) -> str:
        """入力フィールドのスタイルを取得。"""
        return """
            QLineEdit, QTextEdit {
                background-color: #FAFAFA;
                border: 1px solid #D0C8B8;
                border-radius: 6px;
                padding: 8px 12px;
                color: #333;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #63C6FF;
            }
        """

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
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._on_save_clicked)

    @Slot()
    def _on_save_clicked(self):
        """保存ボタンクリック時の処理。"""
        # バリデーション
        if not self._validate():
            return

        # プロファイルを取得して保存シグナルを発行
        profile = self.get_profile()
        self.profile_saved.emit(profile)

        logger.info(f"Profile saved: {profile.name}")
        self.accept()

    def _validate(self) -> bool:
        """入力値のバリデーション。"""
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Profile name is required.",
                QMessageBox.Ok,
            )
            self.name_edit.setFocus()
            return False

        # 領域のバリデーション（幅・高さが0より大きいか）
        header_rect = self.header_rect_editor.get_rect()
        body_rect = self.body_rect_editor.get_rect()

        if header_rect and (header_rect.width <= 0 or header_rect.height <= 0):
            QMessageBox.warning(
                self,
                "Validation Error",
                "Header region width and height must be greater than 0.",
                QMessageBox.Ok,
            )
            return False

        if body_rect and (body_rect.width <= 0 or body_rect.height <= 0):
            QMessageBox.warning(
                self,
                "Validation Error",
                "Body region width and height must be greater than 0.",
                QMessageBox.Ok,
            )
            return False

        return True

    def set_profile(self, profile: Profile):
        """編集するプロファイルを設定。"""
        self._profile = profile
        self._is_new = False

        # UIに値を反映
        self.name_edit.setText(profile.name)
        self.description_edit.setPlainText(profile.description)
        self.header_rect_editor.set_rect(profile.header_rect)
        self.body_rect_editor.set_rect(profile.body_rect)
        self.narrator_rect_editor.set_rect(profile.narrator_rect)
        self.narrator_label_edit.setText(profile.narrator_label or "語り部")
        self.hotkey_editor.set_hotkey(profile.hotkey)
        self.narrator_hotkey_editor.set_hotkey(profile.narrator_hotkey)

        # タイトル更新
        self.setWindowTitle(f"Edit Profile - {profile.name}")
        self.findChild(QLabel, "titleLabel")
        for child in self.findChildren(QLabel):
            if child.objectName() == "titleLabel":
                child.setText(f"Edit Profile: {profile.name}")
                break

        logger.info(f"Profile loaded for editing: {profile.name}")

    def get_profile(self) -> Profile:
        """編集後のプロファイルを取得。"""
        from datetime import datetime

        if self._profile:
            # 既存プロファイルの更新
            profile = self._profile
            profile.updated_at = datetime.now().isoformat()
        else:
            # 新規プロファイルの作成
            profile = Profile()

        # UIから値を取得して設定
        profile.name = self.name_edit.text().strip()
        profile.description = self.description_edit.toPlainText().strip()
        profile.header_rect = self.header_rect_editor.get_rect()
        profile.body_rect = self.body_rect_editor.get_rect()
        profile.narrator_rect = self.narrator_rect_editor.get_rect()
        profile.narrator_label = self.narrator_label_edit.text().strip() or "語り部"
        profile.hotkey = self.hotkey_editor.get_hotkey()
        profile.narrator_hotkey = self.narrator_hotkey_editor.get_hotkey()

        return profile

    def clear(self):
        """すべての入力をクリア。"""
        self._profile = None
        self._is_new = True

        self.name_edit.clear()
        self.description_edit.clear()
        self.header_rect_editor.clear()
        self.body_rect_editor.clear()
        self.narrator_rect_editor.clear()
        self.narrator_label_edit.setText("語り部")
        self.hotkey_editor.clear()
        self.narrator_hotkey_editor.clear()

        self.setWindowTitle("Profile Editor")
        for child in self.findChildren(QLabel):
            if child.objectName() == "titleLabel":
                child.setText("New Profile")
                break

    def set_new_mode(self):
        """新規作成モードに設定。"""
        self.clear()
        for child in self.findChildren(QLabel):
            if child.objectName() == "titleLabel":
                child.setText("Create New Profile")
                break
        self.setWindowTitle("Create New Profile")


# Standalone test
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # テスト用プロファイル
    test_profile = Profile(
        name="Test Game",
        description="Profile for testing the editor",
        header_rect=Rect(x=100, y=200, width=300, height=50),
        body_rect=Rect(x=100, y=260, width=300, height=200),
        hotkey=Hotkey(keys=["cmd", "shift", "l"]),
    )

    dialog = ProfileEditorDialog()

    # 既存プロファイルを編集する場合
    # dialog.set_profile(test_profile)

    # 新規作成モード
    dialog.set_new_mode()

    if dialog.exec() == QDialog.Accepted:
        result = dialog.get_profile()
        print(f"Profile saved: {result.name}")
        print(f"  Description: {result.description}")
        print(f"  Header rect: {result.header_rect}")
        print(f"  Body rect: {result.body_rect}")
        print(f"  Hotkey: {result.hotkey}")
    else:
        print("Dialog cancelled")

    sys.exit(0)
