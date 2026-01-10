"""
LogCard Widget

A card-style widget for displaying log entries in the NoaLog application.
Supports hover, selection, multi-selection states with badges.
"""

from datetime import datetime
from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics,
    QMouseEvent, QPaintEvent, QEnterEvent
)
from PySide6.QtWidgets import QWidget, QCheckBox, QHBoxLayout, QSizePolicy

from models import LogEntry, LogType
from ui.styles.tokens import COLORS, TYPOGRAPHY, SPACING, SHAPES


class CardState(Enum):
    """Visual state of the LogCard."""
    NORMAL = auto()
    HOVERED = auto()
    SELECTED = auto()
    MULTI_SELECTED = auto()


class LogCard(QWidget):
    """
    Card widget for displaying a single log entry.

    Features:
    - Speaker name with optional organization
    - Timestamp display (HH:MM:SS)
    - Body text preview (max 3 lines, 100 chars)
    - Status badges (edited, narration, low_conf)
    - Checkbox for multi-selection mode
    - Hover, selected, multi-selected states

    Signals:
        clicked(str): Emitted when card is clicked (entry_id)
        double_clicked(str): Emitted when card is double-clicked (entry_id)
        selection_toggled(str, bool): Emitted when selection toggled (entry_id, selected)
    """

    # Signals
    clicked = Signal(str)
    double_clicked = Signal(str)
    selection_toggled = Signal(str, bool)

    # Constants
    MAX_BODY_LINES = 3
    MAX_BODY_CHARS = 100
    AVATAR_SIZE = 24
    BADGE_HEIGHT = 18
    BADGE_PADDING_H = 8
    BADGE_PADDING_V = 2
    BADGE_SPACING = 6

    def __init__(
        self,
        entry: Optional[LogEntry] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the LogCard.

        Args:
            entry: LogEntry to display (can be set later via set_entry)
            parent: Optional parent widget
        """
        super().__init__(parent)

        self._entry: Optional[LogEntry] = None
        self._state = CardState.NORMAL
        self._multi_select_mode = False
        self._is_selected = False
        self._checkbox: Optional[QCheckBox] = None
        self._low_confidence = False

        self._setup_ui()
        self._setup_fonts()
        self._setup_colors()

        if entry:
            self.set_entry(entry)

    def _setup_ui(self) -> None:
        """Configure widget properties."""
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(SHAPES.get("card_min_height", 72) if isinstance(SHAPES.get("card_min_height"), int) else 72)

        # Create checkbox for multi-select mode (hidden by default)
        self._checkbox = QCheckBox(self)
        self._checkbox.setFixedSize(20, 20)
        self._checkbox.hide()
        self._checkbox.stateChanged.connect(self._on_checkbox_changed)

    def _setup_fonts(self) -> None:
        """Set up font configurations."""
        font_family = "Hiragino Sans, Noto Sans JP, Yu Gothic UI, Segoe UI, sans-serif"

        # Header font (speaker name)
        self._header_font = QFont()
        self._header_font.setFamily(font_family)
        self._header_font.setPixelSize(14)
        self._header_font.setWeight(QFont.Weight.Medium)

        # Body font
        self._body_font = QFont()
        self._body_font.setFamily(font_family)
        self._body_font.setPixelSize(14)
        self._body_font.setWeight(QFont.Weight.Normal)

        # Timestamp font
        self._timestamp_font = QFont()
        self._timestamp_font.setFamily(font_family)
        self._timestamp_font.setPixelSize(11)
        self._timestamp_font.setWeight(QFont.Weight.Normal)

        # Badge font
        self._badge_font = QFont()
        self._badge_font.setFamily(font_family)
        self._badge_font.setPixelSize(11)
        self._badge_font.setWeight(QFont.Weight.Medium)

    def _setup_colors(self) -> None:
        """Set up color configurations from tokens."""
        # Background colors
        self._bg_normal = QColor(COLORS["bg_panel"])
        self._bg_hover = QColor(COLORS["bg_hover"])
        self._bg_selected = QColor(COLORS["bg_selected"])

        # Text colors
        self._text_primary = QColor(COLORS["text_primary"])
        self._text_secondary = QColor(COLORS["text_secondary"])
        self._text_tertiary = QColor(COLORS["text_tertiary"])

        # Line colors
        self._line_color = QColor(COLORS["line_light"])

        # Badge colors
        self._badge_edited_bg = QColor(COLORS["badge_edited"])
        self._badge_narration_bg = QColor(COLORS["badge_narration"])
        self._badge_low_conf_bg = QColor(COLORS["badge_low_conf"])
        self._badge_text = QColor(COLORS["text_on_accent"])

        # Accent color for avatar circle
        self._accent = QColor(COLORS["accent"])
        self._accent_light = QColor(COLORS["accent_light"])

        # Narration indicator
        self._narration_color = QColor(COLORS["narration"])

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def entry(self) -> Optional[LogEntry]:
        """Get the current log entry."""
        return self._entry

    @property
    def entry_id(self) -> str:
        """Get the entry ID."""
        return self._entry.id if self._entry else ""

    @property
    def state(self) -> CardState:
        """Get the current card state."""
        return self._state

    @property
    def is_selected(self) -> bool:
        """Check if card is selected."""
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool) -> None:
        """Set selection state."""
        if self._is_selected != value:
            self._is_selected = value
            self._update_state()
            if self._checkbox:
                self._checkbox.setChecked(value)
            self.update()

    @property
    def multi_select_mode(self) -> bool:
        """Check if multi-select mode is enabled."""
        return self._multi_select_mode

    @multi_select_mode.setter
    def multi_select_mode(self, value: bool) -> None:
        """Enable/disable multi-select mode."""
        if self._multi_select_mode != value:
            self._multi_select_mode = value
            if self._checkbox:
                self._checkbox.setVisible(value)
            self._update_state()
            self.update()

    @property
    def low_confidence(self) -> bool:
        """Check if entry has low confidence flag."""
        return self._low_confidence

    @low_confidence.setter
    def low_confidence(self, value: bool) -> None:
        """Set low confidence flag."""
        if self._low_confidence != value:
            self._low_confidence = value
            self.update()

    # =========================================================================
    # Public Methods
    # =========================================================================

    def set_entry(self, entry: LogEntry) -> None:
        """
        Set the log entry to display.

        Args:
            entry: LogEntry to display
        """
        self._entry = entry
        self._update_height()
        self.update()

    def clear(self) -> None:
        """Clear the displayed entry."""
        self._entry = None
        self.update()

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _update_state(self) -> None:
        """Update the visual state based on current conditions."""
        if self._is_selected:
            if self._multi_select_mode:
                self._state = CardState.MULTI_SELECTED
            else:
                self._state = CardState.SELECTED
        elif self._state == CardState.HOVERED:
            pass  # Keep hover state
        else:
            self._state = CardState.NORMAL

    def _update_height(self) -> None:
        """Update widget height based on content."""
        if not self._entry:
            return

        # Calculate body text height
        body_text = self._get_truncated_body()
        metrics = QFontMetrics(self._body_font)
        line_height = metrics.lineSpacing()

        # Count actual lines
        lines = body_text.split('\n')
        line_count = min(len(lines), self.MAX_BODY_LINES)

        # Calculate total height
        # Header row: avatar + name/org + timestamp
        header_height = max(self.AVATAR_SIZE, 20)
        # Separator line
        separator_height = 12
        # Body text
        body_height = line_count * line_height
        # Badges row
        badges_height = self.BADGE_HEIGHT + 4 if self._has_badges() else 0
        # Padding
        padding = 16 * 2  # top + bottom

        total_height = header_height + separator_height + body_height + badges_height + padding
        total_height = max(total_height, 72)  # Minimum height

        self.setFixedHeight(int(total_height))

    def _get_truncated_body(self) -> str:
        """Get body text truncated to max chars and lines."""
        if not self._entry:
            return ""

        body = self._entry.display_body
        if not body:
            return ""

        # Truncate to max chars
        if len(body) > self.MAX_BODY_CHARS:
            body = body[:self.MAX_BODY_CHARS] + "..."

        # Split into lines and limit
        lines = body.split('\n')
        if len(lines) > self.MAX_BODY_LINES:
            lines = lines[:self.MAX_BODY_LINES]
            if not lines[-1].endswith("..."):
                lines[-1] = lines[-1] + "..."

        return '\n'.join(lines)

    def _has_badges(self) -> bool:
        """Check if any badges should be displayed."""
        if not self._entry:
            return False
        return (
            self._is_edited() or
            self._entry.log_type == LogType.NARRATION or
            self._low_confidence
        )

    def _is_edited(self) -> bool:
        """Check if entry has been edited."""
        if not self._entry:
            return False
        return (
            self._entry.edited_speaker_name is not None or
            self._entry.edited_speaker_org is not None or
            self._entry.edited_body_text is not None
        )

    def _get_display_timestamp(self) -> str:
        """Get formatted timestamp (HH:MM:SS)."""
        if not self._entry:
            return ""

        try:
            dt = datetime.fromisoformat(self._entry.timestamp)
            return dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            return ""

    def _get_background_color(self) -> QColor:
        """Get background color based on current state."""
        if self._state in (CardState.SELECTED, CardState.MULTI_SELECTED):
            return self._bg_selected
        elif self._state == CardState.HOVERED:
            return self._bg_hover
        return self._bg_normal

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def enterEvent(self, event: QEnterEvent) -> None:
        """Handle mouse enter."""
        if self._state not in (CardState.SELECTED, CardState.MULTI_SELECTED):
            self._state = CardState.HOVERED
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leave."""
        if self._state == CardState.HOVERED:
            self._state = CardState.NORMAL
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton and self._entry:
            self.clicked.emit(self._entry.id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double click."""
        if event.button() == Qt.MouseButton.LeftButton and self._entry:
            self.double_clicked.emit(self._entry.id)
        super().mouseDoubleClickEvent(event)

    def _on_checkbox_changed(self, state: int) -> None:
        """Handle checkbox state change."""
        if self._entry:
            is_checked = state == Qt.CheckState.Checked.value
            self._is_selected = is_checked
            self._update_state()
            self.selection_toggled.emit(self._entry.id, is_checked)
            self.update()

    # =========================================================================
    # Painting
    # =========================================================================

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the card."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        self._draw_background(painter)

        if self._entry:
            # Draw content
            self._draw_header(painter)
            self._draw_separator(painter)
            self._draw_body(painter)
            self._draw_badges(painter)

        painter.end()

    def _draw_background(self, painter: QPainter) -> None:
        """Draw card background with rounded corners."""
        bg_color = self._get_background_color()
        radius = 10  # radius_md

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)

        # Draw subtle border
        border_color = QColor(COLORS["line_light"])
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)

    def _draw_header(self, painter: QPainter) -> None:
        """Draw header row (avatar, name/org, timestamp)."""
        left_margin = 16
        top_margin = 16
        right_margin = 16

        # Adjust for checkbox in multi-select mode
        content_left = left_margin
        if self._multi_select_mode:
            content_left = left_margin + 28
            # Position checkbox
            if self._checkbox:
                self._checkbox.move(left_margin, top_margin + 2)

        # Draw avatar circle
        avatar_x = content_left
        avatar_y = top_margin
        avatar_center_x = avatar_x + self.AVATAR_SIZE // 2
        avatar_center_y = avatar_y + self.AVATAR_SIZE // 2

        is_narration = self._entry.log_type == LogType.NARRATION

        if is_narration:
            # Square indicator for narration
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._narration_color))
            square_size = 10
            painter.drawRect(
                avatar_center_x - square_size // 2,
                avatar_center_y - square_size // 2,
                square_size,
                square_size
            )
        else:
            # Circle for dialogue
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._accent_light))
            painter.drawEllipse(
                avatar_x,
                avatar_y,
                self.AVATAR_SIZE,
                self.AVATAR_SIZE
            )
            # Inner circle
            inner_size = self.AVATAR_SIZE - 8
            painter.setBrush(QBrush(self._accent))
            painter.drawEllipse(
                avatar_x + 4,
                avatar_y + 4,
                inner_size,
                inner_size
            )

        # Draw speaker name and organization
        text_left = avatar_x + self.AVATAR_SIZE + 10
        text_y = top_margin + 4

        painter.setFont(self._header_font)
        painter.setPen(QPen(self._text_primary))

        if is_narration:
            speaker_text = "  \u25a0 \u5730\u306e\u6587"  # ■ 地の文
        else:
            speaker_text = self._entry.display_name
            if self._entry.display_org:
                speaker_text += f" / {self._entry.display_org}"

        # Calculate available width for speaker text
        timestamp_width = 60  # Reserve space for timestamp
        available_width = self.width() - text_left - right_margin - timestamp_width - 10

        # Elide text if too long
        metrics = QFontMetrics(self._header_font)
        elided_text = metrics.elidedText(speaker_text, Qt.TextElideMode.ElideRight, int(available_width))
        painter.drawText(text_left, text_y + metrics.ascent(), elided_text)

        # Draw timestamp (right aligned)
        painter.setFont(self._timestamp_font)
        painter.setPen(QPen(self._text_tertiary))

        timestamp = self._get_display_timestamp()
        timestamp_metrics = QFontMetrics(self._timestamp_font)
        timestamp_x = self.width() - right_margin - timestamp_metrics.horizontalAdvance(timestamp)
        painter.drawText(timestamp_x, text_y + timestamp_metrics.ascent(), timestamp)

    def _draw_separator(self, painter: QPainter) -> None:
        """Draw separator line under header."""
        left_margin = 16
        right_margin = 16

        # Adjust for checkbox in multi-select mode
        content_left = left_margin
        if self._multi_select_mode:
            content_left = left_margin + 28

        # Position: below avatar, aligned with text
        line_left = content_left + self.AVATAR_SIZE + 10
        line_y = 16 + self.AVATAR_SIZE + 6
        line_right = self.width() - right_margin

        painter.setPen(QPen(self._line_color, 1))
        painter.drawLine(line_left, line_y, line_right, line_y)

    def _draw_body(self, painter: QPainter) -> None:
        """Draw body text preview."""
        left_margin = 16
        right_margin = 16

        # Adjust for checkbox in multi-select mode
        content_left = left_margin
        if self._multi_select_mode:
            content_left = left_margin + 28

        # Position: below separator, aligned with text
        text_left = content_left + self.AVATAR_SIZE + 10
        text_top = 16 + self.AVATAR_SIZE + 18
        text_width = self.width() - text_left - right_margin

        painter.setFont(self._body_font)
        painter.setPen(QPen(self._text_secondary))

        body_text = self._get_truncated_body()
        metrics = QFontMetrics(self._body_font)
        line_height = metrics.lineSpacing()

        lines = body_text.split('\n')
        for i, line in enumerate(lines[:self.MAX_BODY_LINES]):
            # Elide each line if too long
            elided = metrics.elidedText(line, Qt.TextElideMode.ElideRight, int(text_width))
            y = text_top + (i * line_height) + metrics.ascent()
            painter.drawText(text_left, y, elided)

    def _draw_badges(self, painter: QPainter) -> None:
        """Draw status badges."""
        if not self._has_badges():
            return

        left_margin = 16
        right_margin = 16

        # Adjust for checkbox in multi-select mode
        content_left = left_margin
        if self._multi_select_mode:
            content_left = left_margin + 28

        # Position: at bottom, aligned with text
        badge_left = content_left + self.AVATAR_SIZE + 10
        badge_y = self.height() - self.BADGE_HEIGHT - 12

        badges = []
        if self._is_edited():
            badges.append(("edited", self._badge_edited_bg))
        if self._entry.log_type == LogType.NARRATION:
            badges.append(("\u5730\u306e\u6587", self._badge_narration_bg))  # 地の文
        if self._low_confidence:
            badges.append(("low_conf", self._badge_low_conf_bg))

        painter.setFont(self._badge_font)
        metrics = QFontMetrics(self._badge_font)

        current_x = badge_left
        for text, bg_color in badges:
            # Calculate badge width
            text_width = metrics.horizontalAdvance(text)
            badge_width = text_width + self.BADGE_PADDING_H * 2
            badge_height = self.BADGE_HEIGHT

            # Draw badge background
            radius = badge_height // 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(
                int(current_x),
                int(badge_y),
                int(badge_width),
                int(badge_height),
                radius,
                radius
            )

            # Draw badge text
            painter.setPen(QPen(self._badge_text))
            text_y = badge_y + (badge_height - metrics.height()) // 2 + metrics.ascent()
            painter.drawText(int(current_x + self.BADGE_PADDING_H), int(text_y), text)

            current_x += badge_width + self.BADGE_SPACING

    # =========================================================================
    # Size Hints
    # =========================================================================

    def sizeHint(self) -> QSize:
        """Return preferred size."""
        return QSize(300, self.height() if self.height() > 0 else 100)

    def minimumSizeHint(self) -> QSize:
        """Return minimum size."""
        return QSize(200, 72)
