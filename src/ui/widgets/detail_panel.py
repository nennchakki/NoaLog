"""
DetailPanel Widget

A tabbed detail panel for displaying and editing log entries.
Supports editing, viewing original OCR, and showing diff between versions.
"""

import difflib
from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal, Slot, QEvent
from PySide6.QtGui import (
    QFont, QColor, QTextCharFormat, QTextCursor,
    QKeySequence, QUndoStack, QUndoCommand
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTextEdit, QLineEdit, QSizePolicy,
    QSpacerItem
)

from models import LogEntry
from ui.styles.tokens import COLORS, TYPOGRAPHY, SPACING, SHAPES


# =============================================================================
# Undo Commands
# =============================================================================

class EditFieldCommand(QUndoCommand):
    """Undo command for field edits."""

    def __init__(
        self,
        panel: "DetailPanel",
        field_name: str,
        old_value: str,
        new_value: str,
        description: str = ""
    ):
        super().__init__(description or f"Edit {field_name}")
        self._panel = panel
        self._field_name = field_name
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        """Apply the edit."""
        self._panel._apply_field_change(self._field_name, self._new_value, emit_signal=True)

    def undo(self) -> None:
        """Revert the edit."""
        self._panel._apply_field_change(self._field_name, self._old_value, emit_signal=True)


# =============================================================================
# Editable Header Label
# =============================================================================

class EditableHeaderField(QWidget):
    """
    An inline-editable field for header values (speaker name, org, timestamp).
    Double-click to edit, Enter to save, Escape to cancel.
    """

    value_changed = Signal(str, str, str)  # field_name, old_value, new_value

    def __init__(
        self,
        field_name: str,
        label_text: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._field_name = field_name
        self._label_text = label_text
        self._current_value = ""
        self._editing = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        if self._label_text:
            label = QLabel(self._label_text)
            label.setStyleSheet(f"""
                color: {COLORS['text_tertiary']};
                font-size: {TYPOGRAPHY['text_sm']};
            """)
            label.setFixedWidth(60)
            layout.addWidget(label)

        # Value display / edit stack
        self._value_label = QLabel()
        self._value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {TYPOGRAPHY['text_base']};
            font-weight: {TYPOGRAPHY['weight_medium']};
        """)
        self._value_label.setCursor(Qt.CursorShape.IBeamCursor)
        self._value_label.installEventFilter(self)

        self._edit_input = QLineEdit()
        self._edit_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['accent']};
                border-radius: {SHAPES['radius_sm']};
                padding: 4px 8px;
                color: {COLORS['text_primary']};
                font-size: {TYPOGRAPHY['text_base']};
            }}
        """)
        self._edit_input.hide()
        self._edit_input.returnPressed.connect(self._finish_edit)
        self._edit_input.installEventFilter(self)

        layout.addWidget(self._value_label, 1)
        layout.addWidget(self._edit_input, 1)

    def set_value(self, value: str) -> None:
        """Set the displayed value."""
        self._current_value = value
        self._value_label.setText(value or "-")
        self._edit_input.setText(value)

    def get_value(self) -> str:
        """Get the current value."""
        return self._current_value

    def eventFilter(self, obj, event) -> bool:
        """Handle double-click to edit and Escape to cancel."""
        if obj == self._value_label:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self._start_edit()
                return True

        if obj == self._edit_input:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self._cancel_edit()
                    return True
            elif event.type() == QEvent.Type.FocusOut:
                # Auto-save on focus loss
                self._finish_edit()
                return False

        return super().eventFilter(obj, event)

    def _start_edit(self) -> None:
        """Enter edit mode."""
        if self._editing:
            return
        self._editing = True
        self._edit_input.setText(self._current_value)
        self._value_label.hide()
        self._edit_input.show()
        self._edit_input.setFocus()
        self._edit_input.selectAll()

    def _finish_edit(self) -> None:
        """Finish editing and save changes."""
        if not self._editing:
            return

        new_value = self._edit_input.text().strip()
        old_value = self._current_value

        self._editing = False
        self._edit_input.hide()
        self._value_label.show()

        if new_value != old_value:
            self._current_value = new_value
            self._value_label.setText(new_value or "-")
            self.value_changed.emit(self._field_name, old_value, new_value)

    def _cancel_edit(self) -> None:
        """Cancel editing without saving."""
        self._editing = False
        self._edit_input.setText(self._current_value)
        self._edit_input.hide()
        self._value_label.show()


# =============================================================================
# Tab Content Widgets
# =============================================================================

class EditableTextArea(QTextEdit):
    """
    Editable text area for the submission tab.
    Supports Enter to save and Escape to cancel.
    """

    edit_finished = Signal(str, str)  # old_value, new_value
    edit_cancelled = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._original_text = ""
        self._setup_style()

    def _setup_style(self) -> None:
        """Apply styling."""
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['line_light']};
                border-radius: {SHAPES['radius_md']};
                padding: {SPACING['space_3']};
                color: {COLORS['text_primary']};
                font-size: {TYPOGRAPHY['text_base']};
                line-height: {TYPOGRAPHY['leading_relaxed']};
            }}
            QTextEdit:focus {{
                border-color: {COLORS['accent']};
            }}
        """)

    def set_text_value(self, text: str) -> None:
        """Set text and store as original."""
        self._original_text = text
        self.setPlainText(text)

    def get_original_text(self) -> str:
        """Get the original text before editing."""
        return self._original_text

    def keyPressEvent(self, event) -> None:
        """Handle Enter (save) and Escape (cancel)."""
        if event.key() == Qt.Key.Key_Escape:
            self.setPlainText(self._original_text)
            self.edit_cancelled.emit()
            return

        # Ctrl+Enter or Cmd+Enter to save
        if event.key() == Qt.Key.Key_Return:
            modifiers = event.modifiers()
            if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
                new_text = self.toPlainText()
                if new_text != self._original_text:
                    old_text = self._original_text
                    self._original_text = new_text
                    self.edit_finished.emit(old_text, new_text)
                return

        super().keyPressEvent(event)


class ReadOnlyTextArea(QTextEdit):
    """Read-only text area for OCR raw tab."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setReadOnly(True)
        self._setup_style()

    def _setup_style(self) -> None:
        """Apply styling."""
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['line_light']};
                border-radius: {SHAPES['radius_md']};
                padding: {SPACING['space_3']};
                color: {COLORS['text_secondary']};
                font-size: {TYPOGRAPHY['text_base']};
                line-height: {TYPOGRAPHY['leading_relaxed']};
            }}
        """)


class DiffTextArea(QTextEdit):
    """
    Text area for displaying diff between raw and edited text.
    Uses color highlighting to show changes.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setReadOnly(True)
        self._setup_style()
        self._setup_formats()

    def _setup_style(self) -> None:
        """Apply base styling."""
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['line_light']};
                border-radius: {SHAPES['radius_md']};
                padding: {SPACING['space_3']};
                color: {COLORS['text_primary']};
                font-size: {TYPOGRAPHY['text_base']};
                font-family: {TYPOGRAPHY['font_family_mono']};
                line-height: {TYPOGRAPHY['leading_relaxed']};
            }}
        """)

    def _setup_formats(self) -> None:
        """Set up text formats for diff highlighting."""
        # Added text (green background)
        self._added_format = QTextCharFormat()
        self._added_format.setBackground(QColor("#dcfce7"))  # Light green
        self._added_format.setForeground(QColor("#166534"))  # Dark green

        # Removed text (red background with strikethrough)
        self._removed_format = QTextCharFormat()
        self._removed_format.setBackground(QColor("#fee2e2"))  # Light red
        self._removed_format.setForeground(QColor("#991b1b"))  # Dark red
        self._removed_format.setFontStrikeOut(True)

        # Equal text (normal)
        self._equal_format = QTextCharFormat()
        self._equal_format.setForeground(QColor(COLORS["text_primary"]))

    def show_diff(self, raw_text: str, edited_text: str) -> None:
        """
        Display the diff between raw and edited text.
        Uses difflib to generate a unified diff view.
        """
        self.clear()

        if not raw_text and not edited_text:
            self.setPlainText("(No content)")
            return

        if raw_text == edited_text:
            self.setPlainText("(No changes)")
            return

        # Generate word-level diff
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        # Use SequenceMatcher for inline diff
        matcher = difflib.SequenceMatcher(None, raw_text, edited_text)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                cursor.insertText(raw_text[i1:i2], self._equal_format)
            elif tag == 'replace':
                # Show removed text
                cursor.insertText(raw_text[i1:i2], self._removed_format)
                # Show added text
                cursor.insertText(edited_text[j1:j2], self._added_format)
            elif tag == 'delete':
                cursor.insertText(raw_text[i1:i2], self._removed_format)
            elif tag == 'insert':
                cursor.insertText(edited_text[j1:j2], self._added_format)

        self.setTextCursor(cursor)


# =============================================================================
# Detail Panel
# =============================================================================

class DetailPanel(QFrame):
    """
    Tabbed detail panel for log entries.

    Features:
    - Header with inline-editable fields (speaker name, org, timestamp)
    - Three tabs: Submission (editable), OCR Raw (read-only), Diff (comparison)
    - Undo/Redo support with QUndoStack
    - Edited badge display

    Signals:
        entry_updated(str, dict): Emitted when entry is updated (entry_id, changes)
        tab_changed(int): Emitted when tab is changed
        copy_requested(str): Emitted when copy is requested (format)
    """

    # Signals
    entry_updated = Signal(str, dict)  # entry_id, changes dict
    tab_changed = Signal(int)  # tab index
    copy_requested = Signal(str)  # format

    # Tab indices
    TAB_EDITED = 0
    TAB_RAW = 1
    TAB_DIFF = 2

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("detailPanel")

        self._entry: Optional[LogEntry] = None
        self._undo_stack = QUndoStack(self)
        self._is_edited = False

        self._setup_ui()
        self._setup_colors()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the UI structure."""
        self.setMinimumWidth(350)
        self.setMaximumWidth(450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header section
        self._create_header(layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['line_light']};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        # Tab widget
        self._create_tabs(layout)

        # Footer with Undo/Redo buttons
        self._create_footer(layout)

    def _setup_colors(self) -> None:
        """Apply color styling to the panel."""
        self.setStyleSheet(f"""
            QFrame#detailPanel {{
                background-color: {COLORS['bg_panel']};
                border-left: 1px solid {COLORS['line_light']};
            }}
        """)

    def _create_header(self, parent_layout: QVBoxLayout) -> None:
        """Create the header section with title and editable fields."""
        # Title row with edited badge
        title_row = QHBoxLayout()

        title_label = QLabel("DETAIL HEADER")
        title_label.setStyleSheet(f"""
            color: {COLORS['text_tertiary']};
            font-size: {TYPOGRAPHY['text_xs']};
            font-weight: {TYPOGRAPHY['weight_semibold']};
            letter-spacing: 1px;
        """)
        title_row.addWidget(title_label)

        title_row.addStretch()

        # Edited badge
        self._edited_badge = QLabel("edited")
        self._edited_badge.setStyleSheet(f"""
            background-color: {COLORS['badge_edited']};
            color: {COLORS['text_on_accent']};
            font-size: {TYPOGRAPHY['text_xs']};
            font-weight: {TYPOGRAPHY['weight_medium']};
            padding: 2px 8px;
            border-radius: 9px;
        """)
        self._edited_badge.hide()
        title_row.addWidget(self._edited_badge)

        parent_layout.addLayout(title_row)

        # Speaker name / Organization
        self._speaker_field = EditableHeaderField("speaker_name", "")
        self._speaker_field.value_changed.connect(self._on_header_field_changed)
        parent_layout.addWidget(self._speaker_field)

        self._org_field = EditableHeaderField("speaker_org", "")
        self._org_field.value_changed.connect(self._on_header_field_changed)
        parent_layout.addWidget(self._org_field)

        # Timestamp (read-only display)
        self._timestamp_label = QLabel()
        self._timestamp_label.setStyleSheet(f"""
            color: {COLORS['text_tertiary']};
            font-size: {TYPOGRAPHY['text_sm']};
        """)
        parent_layout.addWidget(self._timestamp_label)

    def _create_tabs(self, parent_layout: QVBoxLayout) -> None:
        """Create the tabbed content area."""
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_secondary']};
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: {SHAPES['radius_sm']};
                border-top-right-radius: {SHAPES['radius_sm']};
                font-size: {TYPOGRAPHY['text_sm']};
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['accent']};
                color: {COLORS['text_on_accent']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS['bg_hover']};
            }}
        """)

        # Tab 0: Submission (editable) - 提出用
        self._edited_text = EditableTextArea()
        self._edited_text.edit_finished.connect(self._on_body_edited)
        self._tab_widget.addTab(self._edited_text, "提出用")

        # Tab 1: OCR Raw (read-only) - OCR原文
        self._raw_text = ReadOnlyTextArea()
        self._tab_widget.addTab(self._raw_text, "OCR原文")

        # Tab 2: Diff - 差分
        self._diff_text = DiffTextArea()
        self._tab_widget.addTab(self._diff_text, "差分")

        parent_layout.addWidget(self._tab_widget, 1)

    def _create_footer(self, parent_layout: QVBoxLayout) -> None:
        """Create the footer with Undo/Redo buttons."""
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)

        # Undo button
        self._undo_btn = QPushButton("Undo")
        self._undo_btn.setObjectName("secondaryButton")
        self._undo_btn.setStyleSheet(self._get_button_style(secondary=True))
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(self.undo)
        footer_layout.addWidget(self._undo_btn)

        # Redo button
        self._redo_btn = QPushButton("Redo")
        self._redo_btn.setObjectName("secondaryButton")
        self._redo_btn.setStyleSheet(self._get_button_style(secondary=True))
        self._redo_btn.setEnabled(False)
        self._redo_btn.clicked.connect(self.redo)
        footer_layout.addWidget(self._redo_btn)

        footer_layout.addStretch()

        parent_layout.addLayout(footer_layout)

    def _get_button_style(self, secondary: bool = False) -> str:
        """Get button stylesheet."""
        if secondary:
            return f"""
                QPushButton {{
                    background-color: {COLORS['bg_input']};
                    color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['line']};
                    border-radius: {SHAPES['radius_sm']};
                    padding: 6px 12px;
                    font-size: {TYPOGRAPHY['text_sm']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['bg_hover']};
                }}
                QPushButton:disabled {{
                    background-color: {COLORS['bg_input']};
                    color: {COLORS['text_tertiary']};
                    border-color: {COLORS['line_light']};
                }}
            """
        return ""

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._undo_stack.canUndoChanged.connect(self._undo_btn.setEnabled)
        self._undo_stack.canRedoChanged.connect(self._redo_btn.setEnabled)

    # =========================================================================
    # Public Methods
    # =========================================================================

    def set_entry(self, entry: LogEntry) -> None:
        """
        Set the entry to display.

        Args:
            entry: LogEntry to display
        """
        self._entry = entry
        self._undo_stack.clear()
        self._update_display()

    def clear(self) -> None:
        """Clear all displayed content."""
        self._entry = None
        self._undo_stack.clear()

        self._speaker_field.set_value("")
        self._org_field.set_value("")
        self._timestamp_label.setText("")
        self._edited_text.set_text_value("")
        self._raw_text.setPlainText("")
        self._diff_text.clear()
        self._edited_badge.hide()
        self._is_edited = False

    def get_current_tab(self) -> int:
        """
        Get the current tab index.

        Returns:
            int: Current tab index (TAB_EDITED, TAB_RAW, or TAB_DIFF)
        """
        return self._tab_widget.currentIndex()

    def undo(self) -> None:
        """Undo the last edit."""
        if self._undo_stack.canUndo():
            self._undo_stack.undo()

    def redo(self) -> None:
        """Redo the last undone edit."""
        if self._undo_stack.canRedo():
            self._undo_stack.redo()

    def can_undo(self) -> bool:
        """
        Check if undo is available.

        Returns:
            bool: True if undo is available
        """
        return self._undo_stack.canUndo()

    def can_redo(self) -> bool:
        """
        Check if redo is available.

        Returns:
            bool: True if redo is available
        """
        return self._undo_stack.canRedo()

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _update_display(self) -> None:
        """Update the display with current entry data."""
        if not self._entry:
            self.clear()
            return

        # Update header fields
        self._speaker_field.set_value(self._entry.display_name or "")
        self._org_field.set_value(self._entry.display_org or "")

        # Format and display timestamp
        try:
            dt = datetime.fromisoformat(self._entry.timestamp)
            timestamp_str = dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            timestamp_str = str(self._entry.timestamp)[:8]
        self._timestamp_label.setText(timestamp_str)

        # Update text areas
        raw_body = self._entry.body_text or ""
        edited_body = self._entry.display_body or ""

        self._edited_text.set_text_value(edited_body)
        self._raw_text.setPlainText(raw_body)

        # Update diff view
        self._diff_text.show_diff(raw_body, edited_body)

        # Update edited badge
        self._update_edited_badge()

    def _update_edited_badge(self) -> None:
        """Update the visibility of the edited badge."""
        if not self._entry:
            self._edited_badge.hide()
            self._is_edited = False
            return

        has_edits = (
            self._entry.edited_speaker_name is not None or
            self._entry.edited_speaker_org is not None or
            self._entry.edited_body_text is not None
        )

        self._is_edited = has_edits
        self._edited_badge.setVisible(has_edits)

    def _apply_field_change(
        self,
        field_name: str,
        value: str,
        emit_signal: bool = False
    ) -> None:
        """
        Apply a field change to the entry.

        Args:
            field_name: Name of the field to change
            value: New value
            emit_signal: Whether to emit the entry_updated signal
        """
        if not self._entry:
            return

        # Apply the change to the entry
        if field_name == "speaker_name":
            self._entry.edited_speaker_name = value if value else None
            self._speaker_field.set_value(value)
        elif field_name == "speaker_org":
            self._entry.edited_speaker_org = value if value else None
            self._org_field.set_value(value)
        elif field_name == "body_text":
            self._entry.edited_body_text = value if value else None
            self._edited_text.set_text_value(value)
            # Update diff view
            raw_body = self._entry.body_text or ""
            self._diff_text.show_diff(raw_body, value)

        # Update edited badge
        self._update_edited_badge()

        # Emit signal if requested
        if emit_signal:
            self.entry_updated.emit(
                self._entry.id,
                {field_name: value}
            )

    # =========================================================================
    # Signal Handlers
    # =========================================================================

    @Slot(str, str, str)
    def _on_header_field_changed(
        self,
        field_name: str,
        old_value: str,
        new_value: str
    ) -> None:
        """Handle header field edits."""
        if not self._entry:
            return

        # Create undo command
        command = EditFieldCommand(
            self,
            field_name,
            old_value,
            new_value,
            f"Edit {field_name}"
        )
        self._undo_stack.push(command)

    @Slot(str, str)
    def _on_body_edited(self, old_value: str, new_value: str) -> None:
        """Handle body text edits."""
        if not self._entry:
            return

        # Create undo command
        command = EditFieldCommand(
            self,
            "body_text",
            old_value,
            new_value,
            "Edit body text"
        )
        self._undo_stack.push(command)

    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change."""
        # Update diff when switching to diff tab
        if index == self.TAB_DIFF and self._entry:
            raw_body = self._entry.body_text or ""
            edited_body = self._entry.display_body or ""
            self._diff_text.show_diff(raw_body, edited_body)

        self.tab_changed.emit(index)
