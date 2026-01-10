"""
Hotkey Input Widget

ゲームのキーバインド設定のようなホットキー入力ウィジェット。
ボタンをクリック → キー入力待ち → キーを押すと登録。
"""

import logging
from typing import List, Set, Optional, Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QFocusEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget
)

logger = logging.getLogger(__name__)

# Qt Key to string name mapping
KEY_NAMES: Dict[int, str] = {
    # Modifier keys
    Qt.Key.Key_Control: "ctrl",
    Qt.Key.Key_Meta: "cmd",  # macOS Command
    Qt.Key.Key_Alt: "alt",
    Qt.Key.Key_Shift: "shift",

    # Function keys
    Qt.Key.Key_F1: "f1",
    Qt.Key.Key_F2: "f2",
    Qt.Key.Key_F3: "f3",
    Qt.Key.Key_F4: "f4",
    Qt.Key.Key_F5: "f5",
    Qt.Key.Key_F6: "f6",
    Qt.Key.Key_F7: "f7",
    Qt.Key.Key_F8: "f8",
    Qt.Key.Key_F9: "f9",
    Qt.Key.Key_F10: "f10",
    Qt.Key.Key_F11: "f11",
    Qt.Key.Key_F12: "f12",

    # Special keys
    Qt.Key.Key_Space: "space",
    Qt.Key.Key_Return: "enter",
    Qt.Key.Key_Tab: "tab",
    Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Delete: "delete",
    Qt.Key.Key_Insert: "insert",
    Qt.Key.Key_Home: "home",
    Qt.Key.Key_End: "end",
    Qt.Key.Key_PageUp: "pageup",
    Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Up: "up",
    Qt.Key.Key_Down: "down",
    Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right",
}

# Add alphabet keys (A-Z)
for i in range(26):
    KEY_NAMES[Qt.Key.Key_A + i] = chr(ord('a') + i)

# Add number keys (0-9)
for i in range(10):
    KEY_NAMES[Qt.Key.Key_0 + i] = str(i)


class HotkeyInputWidget(QFrame):
    """
    単一のホットキー入力ウィジェット。

    ゲームのキーバインド設定のようなUI。
    「変更」ボタンをクリックするとキー入力待ち状態になり、
    指定された数のキーを同時に押すと登録される。
    """

    hotkey_changed = Signal(list)  # List[str]
    listening_started = Signal()
    listening_cancelled = Signal()

    def __init__(
        self,
        action_name: str,
        required_key_count: int,
        initial_keys: Optional[List[str]] = None,
        parent: Optional[QWidget] = None
    ):
        """
        初期化。

        Args:
            action_name: アクション名（例: "キャプチャ"）
            required_key_count: 必要なキー数（2 or 3）
            initial_keys: 初期ホットキー
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self._action_name = action_name
        self._required_key_count = required_key_count
        self._current_keys: List[str] = initial_keys or []
        self._is_listening = False
        self._pressed_keys: Set[str] = set()

        self._setup_ui()
        self._update_display()

        # キーボードフォーカスを受け取れるように
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _setup_ui(self) -> None:
        """UI構築。"""
        self.setObjectName("hotkeyInputFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # アクション名ラベル
        self._action_label = QLabel(self._action_name)
        self._action_label.setObjectName("hotkeyActionLabel")
        self._action_label.setMinimumWidth(100)
        layout.addWidget(self._action_label)

        # 必要キー数表示
        key_count_label = QLabel(f"({self._required_key_count}キー)")
        key_count_label.setObjectName("hotkeyRequiredLabel")
        key_count_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(key_count_label)

        layout.addStretch()

        # ホットキー表示ラベル
        self._display_label = QLabel()
        self._display_label.setObjectName("hotkeyDisplayLabel")
        self._display_label.setMinimumWidth(150)
        self._display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display_label.setStyleSheet("""
            background-color: #f0f0f0;
            border-radius: 4px;
            padding: 6px 12px;
            font-family: "SF Mono", "Menlo", "Monaco", monospace;
        """)
        layout.addWidget(self._display_label)

        # 変更/キャンセルボタン
        self._change_btn = QPushButton("変更")
        self._change_btn.setObjectName("hotkeyChangeButton")
        self._change_btn.setMinimumWidth(70)
        self._change_btn.clicked.connect(self._on_change_clicked)
        layout.addWidget(self._change_btn)

        # フレームスタイル
        self.setStyleSheet("""
            QFrame#hotkeyInputFrame {
                background-color: #ffffff;
                border: 2px solid #e5e5e0;
                border-radius: 8px;
            }
            QFrame#hotkeyInputFrame:hover {
                border-color: #5eb3f0;
            }
        """)

    def _update_display(self) -> None:
        """表示を更新。"""
        if self._is_listening:
            if self._pressed_keys:
                # 入力中のキーを表示
                keys_str = " + ".join(k.capitalize() for k in sorted(self._pressed_keys))
                self._display_label.setText(keys_str)
            else:
                self._display_label.setText("キー入力待ち...")

            self._display_label.setStyleSheet("""
                background-color: #fff8e6;
                border: 2px dashed #f0a030;
                border-radius: 4px;
                padding: 6px 12px;
                color: #f0a030;
                font-family: "SF Mono", "Menlo", "Monaco", monospace;
            """)
            self._change_btn.setText("キャンセル")
            self._change_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            self.setStyleSheet("""
                QFrame#hotkeyInputFrame {
                    background-color: #fff8e6;
                    border: 2px solid #f0a030;
                    border-radius: 8px;
                }
            """)
        else:
            # 通常表示
            if self._current_keys:
                keys_str = " + ".join(k.capitalize() for k in self._current_keys)
            else:
                keys_str = "未設定"
            self._display_label.setText(keys_str)

            self._display_label.setStyleSheet("""
                background-color: #f0f0f0;
                border-radius: 4px;
                padding: 6px 12px;
                font-family: "SF Mono", "Menlo", "Monaco", monospace;
            """)
            self._change_btn.setText("変更")
            self._change_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5eb3f0;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #4ea3e0;
                }
            """)
            self.setStyleSheet("""
                QFrame#hotkeyInputFrame {
                    background-color: #ffffff;
                    border: 2px solid #e5e5e0;
                    border-radius: 8px;
                }
                QFrame#hotkeyInputFrame:hover {
                    border-color: #5eb3f0;
                }
            """)

    def _on_change_clicked(self) -> None:
        """変更/キャンセルボタンクリック。"""
        if self._is_listening:
            self.cancel_listening()
        else:
            self.start_listening()

    def start_listening(self) -> None:
        """キー入力待ち状態を開始。"""
        self._is_listening = True
        self._pressed_keys.clear()
        self._update_display()
        self.setFocus()  # キーボードフォーカスを取得
        self.listening_started.emit()
        logger.debug(f"Started listening for hotkey: {self._action_name}")

    def cancel_listening(self) -> None:
        """キー入力待ちをキャンセル。"""
        self._is_listening = False
        self._pressed_keys.clear()
        self._update_display()
        self.listening_cancelled.emit()
        logger.debug(f"Cancelled listening for hotkey: {self._action_name}")

    def set_hotkey(self, keys: List[str]) -> None:
        """ホットキーを設定。"""
        self._current_keys = keys.copy()
        self._update_display()

    def get_hotkey(self) -> List[str]:
        """現在のホットキーを取得。"""
        return self._current_keys.copy()

    def reset_to_default(self, default_keys: List[str]) -> None:
        """デフォルト値にリセット。"""
        self.set_hotkey(default_keys)
        self.hotkey_changed.emit(self._current_keys)

    def _key_to_name(self, key: int) -> Optional[str]:
        """Qtキーコードを文字列名に変換。"""
        return KEY_NAMES.get(key)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """キー押下イベント処理。"""
        if not self._is_listening:
            super().keyPressEvent(event)
            return

        # Escapeでキャンセル
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_listening()
            return

        # 押されたキーを記録
        key_name = self._key_to_name(event.key())
        if key_name and key_name not in self._pressed_keys:
            self._pressed_keys.add(key_name)
            self._update_display()

            # 必要数に達したか確認
            if len(self._pressed_keys) >= self._required_key_count:
                self._confirm_hotkey()

        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """キー解放イベント処理。"""
        if not self._is_listening:
            super().keyReleaseEvent(event)
            return

        # キーが離されたらリセット（必要数に達していない場合）
        key_name = self._key_to_name(event.key())
        if key_name and key_name in self._pressed_keys:
            # 必要数に達していなければクリア
            if len(self._pressed_keys) < self._required_key_count:
                self._pressed_keys.clear()
                self._update_display()

        event.accept()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """フォーカス喪失時の処理。"""
        if self._is_listening:
            self.cancel_listening()
        super().focusOutEvent(event)

    def _confirm_hotkey(self) -> None:
        """ホットキーを確定。"""
        # キーを正規化された順序でソート（修飾キー → 通常キー）
        modifier_keys = {"cmd", "ctrl", "alt", "shift"}
        modifier_order = ["cmd", "ctrl", "alt", "shift"]
        keys_list = list(self._pressed_keys)

        # 修飾キーが含まれているか確認
        has_modifier = any(k in modifier_keys for k in keys_list)
        if not has_modifier:
            # 修飾キーなしの場合、警告を表示してキャンセル
            logger.warning(f"Hotkey must include at least one modifier key (Cmd, Ctrl, Alt, Shift)")
            self._show_modifier_warning()
            self._pressed_keys.clear()
            self._update_display()
            return

        def sort_key(k):
            if k in modifier_order:
                return (0, modifier_order.index(k))
            return (1, k)

        keys_list.sort(key=sort_key)

        self._current_keys = keys_list
        self._is_listening = False
        self._pressed_keys.clear()
        self._update_display()

        self.hotkey_changed.emit(self._current_keys)
        logger.info(f"Hotkey confirmed for {self._action_name}: {self._current_keys}")

    def _show_modifier_warning(self) -> None:
        """修飾キー必須の警告を表示。"""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(
            self,
            "ホットキー設定エラー",
            "ホットキーには修飾キー（Cmd, Ctrl, Alt, Shift）を\n"
            "少なくとも1つ含める必要があります。\n\n"
            "例: Cmd + Shift + L"
        )


class HotkeySettingsPanel(QFrame):
    """
    複数のホットキー設定をまとめたパネル。
    """

    settings_changed = Signal(dict)  # Dict[str, List[str]]
    settings_applied = Signal(dict)
    reset_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._hotkey_widgets: Dict[str, HotkeyInputWidget] = {}
        self._default_values: Dict[str, List[str]] = {}
        self._has_changes = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI構築。"""
        self.setObjectName("hotkeySettingsPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # タイトル
        title = QLabel("ホットキー設定")
        title.setObjectName("hotkeySettingsTitle")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a2744;")
        layout.addWidget(title)

        # 説明
        desc = QLabel("「変更」をクリックしてキーを同時に押してください")
        desc.setStyleSheet("color: #6b7280; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(desc)

        # ホットキー入力ウィジェットのコンテナ
        self._widgets_container = QVBoxLayout()
        self._widgets_container.setSpacing(8)
        layout.addLayout(self._widgets_container)

        layout.addStretch()

        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self._reset_btn = QPushButton("デフォルトに戻す")
        self._reset_btn.setObjectName("resetDefaultButton")
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        self._reset_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6b7280;
                border: 2px solid #e5e5e0;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e5e5e0;
                color: #1a2744;
            }
        """)
        button_layout.addWidget(self._reset_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    def add_hotkey_setting(
        self,
        action_id: str,
        action_name: str,
        required_keys: int,
        current_keys: List[str],
        default_keys: List[str]
    ) -> None:
        """
        ホットキー設定を追加。

        Args:
            action_id: アクションID（例: "capture"）
            action_name: 表示名（例: "キャプチャ"）
            required_keys: 必要キー数
            current_keys: 現在の設定
            default_keys: デフォルト値
        """
        widget = HotkeyInputWidget(
            action_name=action_name,
            required_key_count=required_keys,
            initial_keys=current_keys
        )
        widget.hotkey_changed.connect(
            lambda keys, aid=action_id: self._on_hotkey_changed(aid, keys)
        )

        self._hotkey_widgets[action_id] = widget
        self._default_values[action_id] = default_keys
        self._widgets_container.addWidget(widget)

    def _on_hotkey_changed(self, action_id: str, keys: List[str]) -> None:
        """個別ホットキー変更時。"""
        self._has_changes = True
        self.settings_changed.emit(self.get_all_settings())
        logger.debug(f"Hotkey changed: {action_id} -> {keys}")

    def _on_reset_clicked(self) -> None:
        """リセットボタンクリック。"""
        self.reset_all_to_default()
        self.reset_requested.emit()

    def get_all_settings(self) -> Dict[str, List[str]]:
        """全設定を取得。"""
        return {
            action_id: widget.get_hotkey()
            for action_id, widget in self._hotkey_widgets.items()
        }

    def reset_all_to_default(self) -> None:
        """全てをデフォルトにリセット。"""
        for action_id, widget in self._hotkey_widgets.items():
            default_keys = self._default_values.get(action_id, [])
            widget.reset_to_default(default_keys)

        self._has_changes = True
        self.settings_changed.emit(self.get_all_settings())
        logger.info("All hotkeys reset to default")

    def load_from_config(self, config: dict) -> None:
        """設定から読み込み。"""
        hotkey_config = config.get("hotkey", {})

        for action_id, widget in self._hotkey_widgets.items():
            if action_id in hotkey_config:
                widget.set_hotkey(hotkey_config[action_id])
