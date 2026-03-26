"""
CopyPanel Widget

一括コピー機能を提供するパネルコンポーネント。
Plain / Markdown / JSON 形式でのエクスポートに対応。
ファイルへのエクスポート機能も提供。
"""

import json
import logging
from typing import List, Optional, Dict, Any
from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QButtonGroup,
    QApplication,
)

from src.models import LogEntry
from src.ui.styles.tokens import COLORS, TYPOGRAPHY, SPACING, SHAPES

logger = logging.getLogger(__name__)


class CopyFormat(Enum):
    """Copy format types."""
    PLAIN = "plain"
    MARKDOWN = "markdown"
    JSON = "json"


class FormatToggleButton(QPushButton):
    """Individual toggle button for format selection."""

    def __init__(self, text: str, format_type: CopyFormat, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.format_type = format_type
        self.setCheckable(True)
        self.setMinimumWidth(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self) -> None:
        """Update button style based on checked state."""
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: {COLORS['text_on_accent']};
                    border: none;
                    border-radius: {SHAPES['radius_sm']};
                    padding: 6px 12px;
                    font-size: {TYPOGRAPHY['text_sm']};
                    font-weight: {TYPOGRAPHY['weight_medium']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_input']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['line_light']};
                    border-radius: {SHAPES['radius_sm']};
                    padding: 6px 12px;
                    font-size: {TYPOGRAPHY['text_sm']};
                    font-weight: {TYPOGRAPHY['weight_normal']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['bg_hover']};
                    color: {COLORS['text_primary']};
                    border-color: {COLORS['accent_light']};
                }}
            """)

    def setChecked(self, checked: bool) -> None:
        """Override to update style when checked state changes."""
        super().setChecked(checked)
        self._update_style()


class CopyPanel(QFrame):
    """
    Copy panel widget providing bulk copy functionality.

    Signals:
        copy_requested(str, list): Emitted when copy is requested (format, entry_ids)
        format_changed(str): Emitted when format selection changes
        export_requested(list): Emitted when export is requested (entries)
    """

    copy_requested = Signal(str, list)  # (format, entry_ids)
    format_changed = Signal(str)  # format
    export_requested = Signal(list)  # entries to export

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._entries: List[LogEntry] = []
        self._selected_ids: List[str] = []
        self._selected_count: int = 0
        self._current_format: CopyFormat = CopyFormat.PLAIN

        # エクスポート設定の保持（ダイアログ間で引き継ぐ）
        self._export_settings: Dict[str, Any] = {
            "chapter_name": "",
            "chapter_number": 1,
            "episode_number": 1,
            "output_dir": "",
        }

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the UI."""
        self.setObjectName("copyPanel")
        self.setStyleSheet(f"""
            QFrame#copyPanel {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['line_light']};
                border-radius: {SHAPES['radius_md']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Title
        title_label = QLabel("Copy")
        title_label.setStyleSheet(f"""
            font-size: {TYPOGRAPHY['text_base']};
            font-weight: {TYPOGRAPHY['weight_semibold']};
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(title_label)

        # Format toggle buttons
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(0)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        # Create toggle buttons
        self._plain_btn = FormatToggleButton("Plain", CopyFormat.PLAIN)
        self._md_btn = FormatToggleButton("MD", CopyFormat.MARKDOWN)
        self._json_btn = FormatToggleButton("JSON", CopyFormat.JSON)

        # Style for connected buttons
        self._plain_btn.setStyleSheet(self._get_toggle_style("left", True))
        self._md_btn.setStyleSheet(self._get_toggle_style("center", False))
        self._json_btn.setStyleSheet(self._get_toggle_style("right", False))

        self._button_group.addButton(self._plain_btn, 0)
        self._button_group.addButton(self._md_btn, 1)
        self._button_group.addButton(self._json_btn, 2)

        # Set default selection
        self._plain_btn.setChecked(True)

        toggle_layout.addWidget(self._plain_btn)
        toggle_layout.addWidget(self._md_btn)
        toggle_layout.addWidget(self._json_btn)
        toggle_layout.addStretch()

        layout.addLayout(toggle_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Copy button
        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setObjectName("copyButton")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setMinimumHeight(36)
        self._update_copy_button_style()
        buttons_layout.addWidget(self._copy_btn)

        # Export button
        self._export_btn = QPushButton("Export")
        self._export_btn.setObjectName("exportButton")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setMinimumHeight(36)
        self._update_export_button_style()
        buttons_layout.addWidget(self._export_btn)

        layout.addLayout(buttons_layout)

    def _get_toggle_style(self, position: str, is_checked: bool) -> str:
        """Get style for toggle button based on position and state."""
        # Border radius based on position
        if position == "left":
            radius = f"{SHAPES['radius_sm']} 0 0 {SHAPES['radius_sm']}"
        elif position == "right":
            radius = f"0 {SHAPES['radius_sm']} {SHAPES['radius_sm']} 0"
        else:
            radius = "0"

        if is_checked:
            return f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: {COLORS['text_on_accent']};
                    border: 1px solid {COLORS['accent']};
                    border-radius: {radius};
                    padding: 6px 14px;
                    font-size: {TYPOGRAPHY['text_sm']};
                    font-weight: {TYPOGRAPHY['weight_medium']};
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {COLORS['bg_input']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['line']};
                    border-radius: {radius};
                    padding: 6px 14px;
                    font-size: {TYPOGRAPHY['text_sm']};
                    font-weight: {TYPOGRAPHY['weight_normal']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['bg_hover']};
                    color: {COLORS['text_primary']};
                }}
            """

    def _update_toggle_styles(self) -> None:
        """Update all toggle button styles based on current selection."""
        self._plain_btn.setStyleSheet(
            self._get_toggle_style("left", self._plain_btn.isChecked())
        )
        self._md_btn.setStyleSheet(
            self._get_toggle_style("center", self._md_btn.isChecked())
        )
        self._json_btn.setStyleSheet(
            self._get_toggle_style("right", self._json_btn.isChecked())
        )

    def _update_copy_button_style(self) -> None:
        """Update copy button text and style."""
        if self._selected_count > 0:
            self._copy_btn.setText(f"Copy {self._selected_count} selected")
        else:
            self._copy_btn.setText("Copy")

        self._copy_btn.setStyleSheet(f"""
            QPushButton#copyButton {{
                background-color: {COLORS['accent']};
                color: {COLORS['text_on_accent']};
                border: none;
                border-radius: {SHAPES['radius_sm']};
                padding: 8px 16px;
                font-size: {TYPOGRAPHY['text_base']};
                font-weight: {TYPOGRAPHY['weight_medium']};
            }}
            QPushButton#copyButton:hover {{
                background-color: {COLORS['accent_dark']};
            }}
            QPushButton#copyButton:pressed {{
                background-color: {COLORS['accent']};
            }}
        """)

    def _update_export_button_style(self) -> None:
        """Update export button style."""
        self._export_btn.setStyleSheet(f"""
            QPushButton#exportButton {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['line']};
                border-radius: {SHAPES['radius_sm']};
                padding: 8px 16px;
                font-size: {TYPOGRAPHY['text_base']};
                font-weight: {TYPOGRAPHY['weight_medium']};
            }}
            QPushButton#exportButton:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['accent_light']};
            }}
            QPushButton#exportButton:pressed {{
                background-color: {COLORS['bg_input']};
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._button_group.buttonClicked.connect(self._on_format_changed)
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        self._export_btn.clicked.connect(self._on_export_clicked)

    def _on_format_changed(self, button: QPushButton) -> None:
        """Handle format toggle button click."""
        if isinstance(button, FormatToggleButton):
            self._current_format = button.format_type
            self._update_toggle_styles()
            self.format_changed.emit(self._current_format.value)
            logger.debug(f"Format changed to: {self._current_format.value}")

    def _on_copy_clicked(self) -> None:
        """Handle copy button click."""
        entries_to_copy = self._get_entries_to_copy()

        if not entries_to_copy:
            logger.warning("No entries to copy")
            return

        # Format and copy to clipboard
        formatted_text = self._format_entries(entries_to_copy)
        clipboard = QApplication.clipboard()
        clipboard.setText(formatted_text)

        # Emit signal with entry IDs
        entry_ids = [e.id for e in entries_to_copy]
        self.copy_requested.emit(self._current_format.value, entry_ids)

        logger.info(
            f"Copied {len(entries_to_copy)} entries in {self._current_format.value} format"
        )

    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        if not self._entries:
            logger.warning("No entries to export")
            return

        # ExportDialogを開く（全エントリを渡し、ダイアログ内で範囲選択）
        from src.ui.dialogs.export_dialog import ExportDialog

        dialog = ExportDialog(
            all_entries=self._entries,
            selected_ids=self._selected_ids,
            parent=self.window(),
            initial_chapter_name=self._export_settings["chapter_name"],
            initial_chapter_number=self._export_settings["chapter_number"],
            initial_episode_number=self._export_settings["episode_number"],
            initial_output_dir=self._export_settings["output_dir"],
        )

        # エクスポート完了時に設定を保存
        dialog.exported.connect(self._on_export_completed)

        dialog.exec()

        # ダイアログを閉じた後、設定を保持
        self._export_settings["chapter_name"] = dialog.get_chapter_name()
        self._export_settings["chapter_number"] = dialog.get_chapter_number()
        self._export_settings["episode_number"] = dialog.get_episode_number()
        self._export_settings["output_dir"] = dialog.get_output_dir()

    def _on_export_completed(self, file_path: str) -> None:
        """Handle export completion."""
        logger.info(f"Export completed: {file_path}")
        self.export_requested.emit([file_path])

    def _get_entries_to_copy(self) -> List[LogEntry]:
        """Get entries to copy based on selection."""
        if self._selected_ids:
            # Copy selected entries
            selected_set = set(self._selected_ids)
            return [e for e in self._entries if e.id in selected_set and not e.is_deleted]
        elif self._entries:
            # Copy most recent entry (last in list)
            for entry in reversed(self._entries):
                if not entry.is_deleted:
                    return [entry]
        return []

    def _format_entries(self, entries: List[LogEntry]) -> str:
        """Format entries based on current format selection."""
        if self._current_format == CopyFormat.PLAIN:
            return self._format_plain(entries)
        elif self._current_format == CopyFormat.MARKDOWN:
            return self._format_markdown(entries)
        elif self._current_format == CopyFormat.JSON:
            return self._format_json(entries)
        return ""

    def _format_plain(self, entries: List[LogEntry]) -> str:
        """Format entries as plain text."""
        lines = []
        for entry in entries:
            header = self._build_header(entry)
            lines.append(header)
            lines.append(entry.display_body)
            lines.append("")  # Empty line between entries
        return "\n".join(lines).rstrip()

    def _format_markdown(self, entries: List[LogEntry]) -> str:
        """Format entries as Markdown."""
        lines = []
        for entry in entries:
            header = self._build_header(entry, bold_name=True)
            lines.append(header)
            # Quote the body
            body_lines = entry.display_body.split("\n")
            for body_line in body_lines:
                lines.append(f"> {body_line}")
            lines.append("")  # Empty line between entries
        return "\n".join(lines).rstrip()

    def _format_json(self, entries: List[LogEntry]) -> str:
        """Format entries as JSON."""
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

    def _build_header(self, entry: LogEntry, bold_name: bool = False) -> str:
        """Build header string from entry."""
        name = entry.display_name
        org = entry.display_org

        if bold_name:
            name = f"**{name}**"

        if org:
            return f"{name} / {org}"
        return name

    # Public API

    def set_selected_count(self, count: int) -> None:
        """
        Update the selected entry count.

        Args:
            count: Number of selected entries
        """
        self._selected_count = count
        self._update_copy_button_style()

    def set_selected_ids(self, ids: List[str]) -> None:
        """
        Set the list of selected entry IDs.

        Args:
            ids: List of selected entry IDs
        """
        self._selected_ids = ids.copy()
        self._selected_count = len(ids)
        self._update_copy_button_style()

    def set_entries(self, entries: List[LogEntry]) -> None:
        """
        Set the list of entries available for copying.

        Args:
            entries: List of LogEntry objects
        """
        self._entries = entries.copy()

    def get_selected_format(self) -> str:
        """
        Get the currently selected format.

        Returns:
            Format string ("plain", "markdown", or "json")
        """
        return self._current_format.value

    def set_format(self, format_str: str) -> None:
        """
        Set the current format.

        Args:
            format_str: Format string ("plain", "markdown", or "json")
        """
        try:
            format_type = CopyFormat(format_str)
            self._current_format = format_type

            # Update button states
            if format_type == CopyFormat.PLAIN:
                self._plain_btn.setChecked(True)
            elif format_type == CopyFormat.MARKDOWN:
                self._md_btn.setChecked(True)
            elif format_type == CopyFormat.JSON:
                self._json_btn.setChecked(True)

            self._update_toggle_styles()
        except ValueError:
            logger.warning(f"Invalid format: {format_str}")

    def clear_selection(self) -> None:
        """Clear the current selection."""
        self._selected_ids.clear()
        self._selected_count = 0
        self._update_copy_button_style()
