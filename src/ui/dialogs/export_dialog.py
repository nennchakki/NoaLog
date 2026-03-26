"""
ExportDialog

選択したログエントリをファイルにエクスポートするダイアログ。
章名、章番号、話番号を指定してファイル名を生成。
番号範囲選択と個別選択に対応。
"""

import logging
from pathlib import Path
from typing import List, Optional, Set

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QComboBox,
    QFileDialog,
    QFrame,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QScrollArea,
    QWidget,
    QSplitter,
)

from src.models import LogEntry
from src.ui.styles.tokens import COLORS, TYPOGRAPHY, SHAPES, SPACING

logger = logging.getLogger(__name__)


class ExportDialog(QDialog):
    """
    ログエントリをファイルにエクスポートするダイアログ。
    番号範囲選択と個別選択に対応。

    Signals:
        exported(str): エクスポート完了時にファイルパスを送信
    """

    exported = Signal(str)  # ファイルパス

    def __init__(
        self,
        all_entries: List[LogEntry],
        selected_ids: List[str] = None,
        parent=None,
        initial_chapter_name: str = "",
        initial_chapter_number: int = 1,
        initial_episode_number: int = 1,
        initial_output_dir: str = "",
    ):
        """
        初期化。

        Args:
            all_entries: 全ログエントリのリスト
            selected_ids: 事前選択されたエントリID
            parent: 親ウィジェット
            initial_chapter_name: 初期章名
            initial_chapter_number: 初期章番号
            initial_episode_number: 初期話番号
            initial_output_dir: 初期出力ディレクトリ
        """
        super().__init__(parent)

        self._all_entries = all_entries
        self._selected_ids: Set[str] = set(selected_ids) if selected_ids else set()
        self._output_dir = initial_output_dir or str(Path.home() / "Desktop")
        self._entry_checkboxes: dict = {}  # entry_id -> QCheckBox

        self.setWindowTitle("Export to File")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        self.setModal(True)

        self._setup_ui(
            initial_chapter_name,
            initial_chapter_number,
            initial_episode_number,
        )
        self._connect_signals()
        self._update_preview()
        self._update_selection_count()

    def _setup_ui(
        self,
        initial_chapter_name: str,
        initial_chapter_number: int,
        initial_episode_number: int,
    ) -> None:
        """UIを構築。"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # タイトル
        title = QLabel("Export Selected Entries")
        title.setStyleSheet(f"""
            font-size: {TYPOGRAPHY['text_lg']};
            font-weight: {TYPOGRAPHY['weight_semibold']};
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(title)

        # メインコンテンツを左右に分割
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左側: エントリ選択 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        # 範囲選択セクション
        range_frame = QFrame()
        range_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_light']};
                border: 1px solid {COLORS['line_light']};
                border-radius: {SHAPES['radius_sm']};
            }}
        """)
        range_layout = QVBoxLayout(range_frame)
        range_layout.setContentsMargins(12, 8, 12, 8)
        range_layout.setSpacing(8)

        range_title = QLabel("Select by Range")
        range_title.setStyleSheet(f"""
            font-size: {TYPOGRAPHY['text_sm']};
            font-weight: {TYPOGRAPHY['weight_medium']};
            color: {COLORS['text_secondary']};
        """)
        range_layout.addWidget(range_title)

        # From / To 入力
        range_input_layout = QHBoxLayout()
        range_input_layout.setSpacing(8)

        range_input_layout.addWidget(QLabel("From #"))
        self._from_spin = QSpinBox()
        self._from_spin.setRange(1, max(1, len(self._all_entries)))
        self._from_spin.setValue(1)
        self._from_spin.setStyleSheet(self._spinbox_style())
        self._from_spin.setMinimumWidth(70)
        range_input_layout.addWidget(self._from_spin)

        range_input_layout.addWidget(QLabel("To #"))
        self._to_spin = QSpinBox()
        self._to_spin.setRange(1, max(1, len(self._all_entries)))
        self._to_spin.setValue(min(10, len(self._all_entries)))
        self._to_spin.setStyleSheet(self._spinbox_style())
        self._to_spin.setMinimumWidth(70)
        range_input_layout.addWidget(self._to_spin)

        self._apply_range_btn = QPushButton("Apply")
        self._apply_range_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_range_btn.setStyleSheet(self._secondary_button_style())
        range_input_layout.addWidget(self._apply_range_btn)

        range_input_layout.addStretch()
        range_layout.addLayout(range_input_layout)

        # Select All / Clear ボタン
        select_buttons_layout = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_all_btn.setStyleSheet(self._link_button_style())
        select_buttons_layout.addWidget(self._select_all_btn)

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet(self._link_button_style())
        select_buttons_layout.addWidget(self._clear_btn)

        select_buttons_layout.addStretch()
        range_layout.addLayout(select_buttons_layout)

        left_layout.addWidget(range_frame)

        # 選択数表示
        self._selection_count_label = QLabel("0 entries selected")
        self._selection_count_label.setStyleSheet(f"""
            font-size: {TYPOGRAPHY['text_sm']};
            color: {COLORS['text_secondary']};
        """)
        left_layout.addWidget(self._selection_count_label)

        # エントリリスト（チェックボックス付き）
        self._entry_list = QListWidget()
        self._entry_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['line_light']};
                border-radius: {SHAPES['radius_sm']};
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {COLORS['line_light']};
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
        """)
        self._populate_entry_list()
        left_layout.addWidget(self._entry_list, 1)

        splitter.addWidget(left_widget)

        # === 右側: エクスポート設定 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(12)

        # 章名入力
        chapter_name_layout = QVBoxLayout()
        chapter_name_label = QLabel("Chapter Name")
        chapter_name_label.setStyleSheet(self._label_style())
        chapter_name_layout.addWidget(chapter_name_label)

        self._chapter_name_input = QLineEdit()
        self._chapter_name_input.setPlaceholderText("e.g., 序章, 第一章")
        self._chapter_name_input.setText(initial_chapter_name)
        self._chapter_name_input.setStyleSheet(self._input_style())
        chapter_name_layout.addWidget(self._chapter_name_input)
        right_layout.addLayout(chapter_name_layout)

        # 章番号・話番号（横並び）
        numbers_layout = QHBoxLayout()
        numbers_layout.setSpacing(12)

        # 章番号
        chapter_num_layout = QVBoxLayout()
        chapter_num_label = QLabel("Chapter #")
        chapter_num_label.setStyleSheet(self._label_style())
        chapter_num_layout.addWidget(chapter_num_label)

        self._chapter_number_spin = QSpinBox()
        self._chapter_number_spin.setRange(1, 999)
        self._chapter_number_spin.setValue(initial_chapter_number)
        self._chapter_number_spin.setStyleSheet(self._spinbox_style())
        self._chapter_number_spin.setMinimumWidth(70)
        chapter_num_layout.addWidget(self._chapter_number_spin)
        numbers_layout.addLayout(chapter_num_layout)

        # 話番号
        episode_num_layout = QVBoxLayout()
        episode_num_label = QLabel("Episode #")
        episode_num_label.setStyleSheet(self._label_style())
        episode_num_layout.addWidget(episode_num_label)

        self._episode_number_spin = QSpinBox()
        self._episode_number_spin.setRange(1, 9999)
        self._episode_number_spin.setValue(initial_episode_number)
        self._episode_number_spin.setStyleSheet(self._spinbox_style())
        self._episode_number_spin.setMinimumWidth(70)
        episode_num_layout.addWidget(self._episode_number_spin)
        numbers_layout.addLayout(episode_num_layout)

        numbers_layout.addStretch()
        right_layout.addLayout(numbers_layout)

        # フォーマット選択
        format_layout = QVBoxLayout()
        format_label = QLabel("Format")
        format_label.setStyleSheet(self._label_style())
        format_layout.addWidget(format_label)

        self._format_combo = QComboBox()
        self._format_combo.addItem("Plain Text (.txt)", "plain")
        self._format_combo.addItem("Markdown (.md)", "markdown")
        self._format_combo.addItem("JSON (.json)", "json")
        self._format_combo.setStyleSheet(self._combo_style())
        format_layout.addWidget(self._format_combo)
        right_layout.addLayout(format_layout)

        # 出力先ディレクトリ
        dir_layout = QVBoxLayout()
        dir_label = QLabel("Output Directory")
        dir_label.setStyleSheet(self._label_style())
        dir_layout.addWidget(dir_label)

        dir_input_layout = QHBoxLayout()
        self._dir_input = QLineEdit()
        self._dir_input.setText(self._output_dir)
        self._dir_input.setStyleSheet(self._input_style())
        self._dir_input.setReadOnly(True)
        dir_input_layout.addWidget(self._dir_input)

        self._browse_btn = QPushButton("...")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.setStyleSheet(self._secondary_button_style())
        self._browse_btn.setMaximumWidth(40)
        dir_input_layout.addWidget(self._browse_btn)

        dir_layout.addLayout(dir_input_layout)
        right_layout.addLayout(dir_layout)

        # プレビュー
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_light']};
                border: 1px solid {COLORS['line_light']};
                border-radius: {SHAPES['radius_sm']};
            }}
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 8, 12, 8)

        preview_title = QLabel("File name preview:")
        preview_title.setStyleSheet(f"""
            font-size: {TYPOGRAPHY['text_xs']};
            color: {COLORS['text_tertiary']};
        """)
        preview_layout.addWidget(preview_title)

        self._preview_label = QLabel()
        self._preview_label.setStyleSheet(f"""
            font-size: {TYPOGRAPHY['text_base']};
            font-weight: {TYPOGRAPHY['weight_medium']};
            color: {COLORS['accent']};
        """)
        preview_layout.addWidget(self._preview_label)

        right_layout.addWidget(preview_frame)

        right_layout.addStretch()

        splitter.addWidget(right_widget)

        # スプリッターの比率設定
        splitter.setSizes([350, 350])

        layout.addWidget(splitter, 1)

        # ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet(self._secondary_button_style())
        button_layout.addWidget(self._cancel_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setStyleSheet(self._primary_button_style())
        self._export_btn.setMinimumWidth(100)
        button_layout.addWidget(self._export_btn)

        layout.addLayout(button_layout)

    def _populate_entry_list(self) -> None:
        """エントリリストを作成。"""
        self._entry_list.clear()
        self._entry_checkboxes.clear()

        total = len(self._all_entries)
        for i, entry in enumerate(self._all_entries):
            # 番号は最古が#1（total - i）
            index = total - i

            # チェックボックス付きウィジェット
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(4, 2, 4, 2)
            item_layout.setSpacing(8)

            checkbox = QCheckBox()
            checkbox.setChecked(entry.id in self._selected_ids)
            checkbox.stateChanged.connect(
                lambda state, eid=entry.id: self._on_checkbox_changed(eid, state)
            )
            self._entry_checkboxes[entry.id] = checkbox
            item_layout.addWidget(checkbox)

            # 番号
            index_label = QLabel(f"#{index}")
            index_label.setStyleSheet(f"""
                font-size: {TYPOGRAPHY['text_sm']};
                color: {COLORS['text_tertiary']};
                min-width: 40px;
            """)
            item_layout.addWidget(index_label)

            # 話者名とテキストプレビュー
            text = f"{entry.display_name}"
            if entry.display_org:
                text += f" / {entry.display_org}"
            body_preview = entry.display_body[:30] + "..." if len(entry.display_body) > 30 else entry.display_body
            body_preview = body_preview.replace("\n", " ")

            content_label = QLabel(f"{text}\n{body_preview}")
            content_label.setStyleSheet(f"""
                font-size: {TYPOGRAPHY['text_sm']};
                color: {COLORS['text_primary']};
            """)
            content_label.setWordWrap(True)
            item_layout.addWidget(content_label, 1)

            # リストアイテムに追加
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, entry.id)
            list_item.setSizeHint(item_widget.sizeHint())
            self._entry_list.addItem(list_item)
            self._entry_list.setItemWidget(list_item, item_widget)

    def _connect_signals(self) -> None:
        """シグナルを接続。"""
        self._chapter_name_input.textChanged.connect(self._update_preview)
        self._chapter_number_spin.valueChanged.connect(self._update_preview)
        self._episode_number_spin.valueChanged.connect(self._update_preview)
        self._format_combo.currentIndexChanged.connect(self._update_preview)
        self._dir_input.textChanged.connect(self._update_preview)

        self._apply_range_btn.clicked.connect(self._on_apply_range)
        self._select_all_btn.clicked.connect(self._on_select_all)
        self._clear_btn.clicked.connect(self._on_clear_all)
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        self._cancel_btn.clicked.connect(self.reject)
        self._export_btn.clicked.connect(self._on_export_clicked)

    def _on_checkbox_changed(self, entry_id: str, state: int) -> None:
        """チェックボックス変更時の処理。"""
        if state == Qt.CheckState.Checked.value:
            self._selected_ids.add(entry_id)
        else:
            self._selected_ids.discard(entry_id)
        self._update_selection_count()

    def _on_apply_range(self) -> None:
        """範囲を適用。"""
        from_num = self._from_spin.value()
        to_num = self._to_spin.value()

        if from_num > to_num:
            from_num, to_num = to_num, from_num

        total = len(self._all_entries)
        for i, entry in enumerate(self._all_entries):
            index = total - i  # 最古が#1
            should_select = from_num <= index <= to_num

            if entry.id in self._entry_checkboxes:
                self._entry_checkboxes[entry.id].setChecked(should_select)

        self._update_selection_count()

    def _on_select_all(self) -> None:
        """全選択。"""
        for checkbox in self._entry_checkboxes.values():
            checkbox.setChecked(True)
        self._update_selection_count()

    def _on_clear_all(self) -> None:
        """全解除。"""
        for checkbox in self._entry_checkboxes.values():
            checkbox.setChecked(False)
        self._update_selection_count()

    def _update_selection_count(self) -> None:
        """選択数表示を更新。"""
        count = len(self._selected_ids)
        self._selection_count_label.setText(f"{count} entries selected")

    def _update_preview(self) -> None:
        """ファイル名プレビューを更新。"""
        filename = self._generate_filename()
        self._preview_label.setText(filename)

    def _generate_filename(self) -> str:
        """ファイル名を生成。"""
        chapter_name = self._chapter_name_input.text().strip()
        chapter_num = self._chapter_number_spin.value()
        episode_num = self._episode_number_spin.value()
        format_type = self._format_combo.currentData()

        extensions = {
            "plain": ".txt",
            "markdown": ".md",
            "json": ".json",
        }
        ext = extensions.get(format_type, ".txt")

        if chapter_name:
            filename = f"{chapter_name}_{chapter_num:02d}_{episode_num:03d}{ext}"
        else:
            filename = f"chapter_{chapter_num:02d}_{episode_num:03d}{ext}"

        return filename

    def _on_browse_clicked(self) -> None:
        """出力先ディレクトリを選択。"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self._output_dir,
        )
        if dir_path:
            self._output_dir = dir_path
            self._dir_input.setText(dir_path)

    def _on_export_clicked(self) -> None:
        """エクスポートを実行。"""
        if not self._selected_ids:
            QMessageBox.warning(self, "Warning", "No entries selected for export.")
            return

        # 選択されたエントリを取得（番号順にソート）
        total = len(self._all_entries)
        selected_entries = []
        for i, entry in enumerate(self._all_entries):
            if entry.id in self._selected_ids:
                index = total - i
                selected_entries.append((index, entry))

        # 番号順にソート（昇順）
        selected_entries.sort(key=lambda x: x[0])
        entries_to_export = [e for _, e in selected_entries]

        filename = self._generate_filename()
        output_path = Path(self._output_dir) / filename

        # ファイルが既に存在する場合の確認
        if output_path.exists():
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"'{filename}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            format_type = self._format_combo.currentData()
            content = self._format_entries(entries_to_export, format_type)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Exported {len(entries_to_export)} entries to: {output_path}")

            # 話番号をインクリメント
            self._episode_number_spin.setValue(self._episode_number_spin.value() + 1)

            self.exported.emit(str(output_path))

            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {len(entries_to_export)} entries to:\n{output_path}",
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export: {e}",
            )

    def _format_entries(self, entries: List[LogEntry], format_type: str) -> str:
        """エントリをフォーマット。"""
        if format_type == "plain":
            return self._format_plain(entries)
        elif format_type == "markdown":
            return self._format_markdown(entries)
        elif format_type == "json":
            return self._format_json(entries)
        return ""

    def _format_plain(self, entries: List[LogEntry]) -> str:
        """プレーンテキスト形式でフォーマット。"""
        lines = []
        for entry in entries:
            header = self._build_header(entry)
            lines.append(header)
            lines.append(entry.display_body)
            lines.append("")
        return "\n".join(lines).rstrip()

    def _format_markdown(self, entries: List[LogEntry]) -> str:
        """Markdown形式でフォーマット。"""
        lines = []
        for entry in entries:
            name = entry.display_name
            org = entry.display_org
            header = f"**{name}**" + (f" / {org}" if org else "")
            lines.append(header)
            lines.append("")
            body_lines = entry.display_body.split("\n")
            for body_line in body_lines:
                lines.append(f"> {body_line}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _format_json(self, entries: List[LogEntry]) -> str:
        """JSON形式でフォーマット。"""
        import json
        data = []
        for entry in entries:
            data.append({
                "id": entry.id,
                "speaker": entry.display_name,
                "organization": entry.display_org,
                "body": entry.display_body,
                "timestamp": entry.timestamp,
                "log_type": entry.log_type.value,
            })
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _build_header(self, entry: LogEntry) -> str:
        """ヘッダー文字列を構築。"""
        name = entry.display_name
        org = entry.display_org
        if org:
            return f"{name} / {org}"
        return name

    # 設定値取得メソッド

    def get_chapter_name(self) -> str:
        return self._chapter_name_input.text()

    def get_chapter_number(self) -> int:
        return self._chapter_number_spin.value()

    def get_episode_number(self) -> int:
        return self._episode_number_spin.value()

    def get_output_dir(self) -> str:
        return self._output_dir

    # スタイル定義

    def _label_style(self) -> str:
        return f"""
            font-size: {TYPOGRAPHY['text_sm']};
            font-weight: {TYPOGRAPHY['weight_medium']};
            color: {COLORS['text_secondary']};
            margin-bottom: 4px;
        """

    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_sm']};
                padding: 8px 12px;
                font-size: {TYPOGRAPHY['text_base']};
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
            }}
        """

    def _spinbox_style(self) -> str:
        return f"""
            QSpinBox {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_sm']};
                padding: 6px 10px;
                font-size: {TYPOGRAPHY['text_base']};
                color: {COLORS['text_primary']};
            }}
            QSpinBox:focus {{
                border-color: {COLORS['accent']};
            }}
        """

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_sm']};
                padding: 8px 12px;
                font-size: {TYPOGRAPHY['text_base']};
                color: {COLORS['text_primary']};
            }}
            QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['line']};
                selection-background-color: {COLORS['bg_selected']};
            }}
        """

    def _primary_button_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: {COLORS['text_on_accent']};
                border: none;
                border-radius: {SHAPES['radius_sm']};
                padding: 10px 20px;
                font-size: {TYPOGRAPHY['text_base']};
                font-weight: {TYPOGRAPHY['weight_medium']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_dark']};
            }}
        """

    def _secondary_button_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_sm']};
                padding: 8px 16px;
                font-size: {TYPOGRAPHY['text_sm']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['accent_light']};
            }}
        """

    def _link_button_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['accent']};
                border: none;
                padding: 4px 8px;
                font-size: {TYPOGRAPHY['text_sm']};
            }}
            QPushButton:hover {{
                color: {COLORS['accent_dark']};
                text-decoration: underline;
            }}
        """
