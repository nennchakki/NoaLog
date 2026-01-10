# NoaLog 機能改修 - 開発部作業指示書

## 宛先
**dev-manager** (開発部マネージャー)

## 概要
NoaLogアプリケーションの機能改修を実施してください。
本プロジェクトは4つのタスクで構成され、優先度順に実装をお願いします。

---

## Task 1: ハードコードプロファイル削除

### 目的
`src/main.py` に直接記述されているテスト用プロファイルを削除し、動的なプロファイル管理に完全移行する。

### 対象ファイル
- `/Users/dansetsu/NoaLog/src/main.py`

### 作業内容

#### 1.1 削除対象コード（99-118行目）
以下のコードブロックを削除:

```python
# Create a default profile for testing
default_profile = Profile(
    name="Default",
    description="Default profile",
    hotkey=Hotkey(keys=["cmd", "shift", "l"]),
    header_rect=Rect(x=100, y=100, width=400, height=50),
    body_rect=Rect(x=100, y=160, width=600, height=200),
)

# Create a second profile for demonstration
zoom_profile = Profile(
    name="Zoom",
    description="Zoom meeting capture profile",
    hotkey=Hotkey(keys=["cmd", "shift", "z"]),
    header_rect=Rect(x=50, y=80, width=300, height=40),
    body_rect=Rect(x=50, y=130, width=500, height=150),
)

# Set profiles through controller
controller.set_profiles([default_profile, zoom_profile])
```

#### 1.2 代替処理の実装
プロファイルが存在しない場合のハンドリング:

```python
# Load saved profiles (or empty list if none exist)
saved_profiles = controller.load_profiles()  # 実装が必要な場合は空リストを返す

if saved_profiles:
    controller.set_profiles(saved_profiles)
else:
    # No profiles - show guidance to user
    window.set_status("プロファイルがありません。「新規」ボタンからプロファイルを作成してください。")
    logger.info("No profiles found. User should create a new profile.")
```

#### 1.3 AppController への load_profiles メソッド追加（必要に応じて）
`app_controller.py` に以下を追加:

```python
def load_profiles(self) -> List[Profile]:
    """
    保存されたプロファイルを読み込む。

    Returns:
        List[Profile]: 保存されたプロファイルのリスト（なければ空リスト）
    """
    profiles_dir = self.config.get_profiles_dir()
    profiles = []

    for profile_file in profiles_dir.glob("*.json"):
        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                profile = Profile.from_dict(data)
                profiles.append(profile)
        except Exception as e:
            logger.warning(f"Failed to load profile {profile_file}: {e}")

    return profiles
```

### 完了基準
- [ ] ハードコードプロファイルが削除されている
- [ ] プロファイル0件でアプリが正常に起動する
- [ ] 適切なガイダンスメッセージが表示される

---

## Task 2: CaptureOverlay の2段階選択モード実装

### 目的
既存の `CaptureOverlay` を拡張し、ヘッダー領域とボディ領域を連続して選択できるようにする。

### 対象ファイル
- `/Users/dansetsu/NoaLog/src/ui/widgets/capture_overlay.py`

### 作業内容

#### 2.1 選択ステージの追加

```python
from enum import Enum, auto

class SelectionStage(Enum):
    """Selection stage in the capture overlay."""
    HEADER = auto()  # Selecting header region
    BODY = auto()    # Selecting body region
    COMPLETE = auto()  # Both regions selected
```

#### 2.2 CaptureOverlay クラスの拡張

**新しいシグナル**:
```python
# 両領域選択完了時のシグナル
regions_selected = Signal(object, object)  # header_rect, body_rect (as Rect objects)
```

**新しいインスタンス変数**:
```python
def __init__(self, ...):
    # ... existing code ...

    # Two-stage selection mode
    self._two_stage_mode = False
    self._selection_stage = SelectionStage.HEADER
    self._header_rect: Optional[QRect] = None  # Stored header selection
    self._body_rect: Optional[QRect] = None    # Stored body selection
```

**新しいメソッド**:
```python
def start_two_stage_selection(self) -> None:
    """
    Start the two-stage selection process.
    Stage 1: Select header region
    Stage 2: Select body region
    """
    self._two_stage_mode = True
    self._selection_stage = SelectionStage.HEADER
    self._header_rect = None
    self._body_rect = None
    self._reset_selection()
    self.show()
```

#### 2.3 キーイベント処理の拡張

`keyPressEvent` を修正して、エンターキーでステージを進める:

```python
def keyPressEvent(self, event: QKeyEvent) -> None:
    """Handle key press events."""
    if event.key() == Qt.Key.Key_Escape:
        # Cancel entire selection
        self._reset_selection()
        self.selection_cancelled.emit()
        self.close()

    elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
        if self._two_stage_mode:
            self._confirm_current_stage()
        else:
            # Single-stage mode: Enter confirms current selection
            if self._selection_rect:
                self._emit_selection()

    elif event.key() == Qt.Key.Key_Tab:
        # Toggle is disabled in two-stage mode
        if not self._two_stage_mode:
            self._toggle_region_type()
    else:
        super().keyPressEvent(event)

def _confirm_current_stage(self) -> None:
    """Confirm the current selection and advance to next stage."""
    if not self._selection_rect:
        return  # No selection to confirm

    rect = self._selection_rect.normalized()
    if rect.width() < self.MIN_SELECTION_SIZE or rect.height() < self.MIN_SELECTION_SIZE:
        return  # Selection too small

    if self._selection_stage == SelectionStage.HEADER:
        # Store header rect and move to body stage
        self._header_rect = rect
        self._selection_stage = SelectionStage.BODY
        self._reset_selection()
        self.update()

    elif self._selection_stage == SelectionStage.BODY:
        # Store body rect and complete
        self._body_rect = rect
        self._selection_stage = SelectionStage.COMPLETE
        self._emit_two_stage_result()
```

#### 2.4 結果の発行

```python
def _emit_two_stage_result(self) -> None:
    """Emit the result of two-stage selection."""
    from models import Rect

    header = Rect(
        x=self._header_rect.x(),
        y=self._header_rect.y(),
        width=self._header_rect.width(),
        height=self._header_rect.height()
    )
    body = Rect(
        x=self._body_rect.x(),
        y=self._body_rect.y(),
        width=self._body_rect.width(),
        height=self._body_rect.height()
    )

    self.regions_selected.emit(header, body)
    self.close()
```

#### 2.5 描画の更新

`_draw_instructions` を修正してステージを表示:

```python
def _draw_instructions(self, painter: QPainter) -> None:
    """Draw instruction text at the top of the overlay."""
    if self._two_stage_mode:
        if self._selection_stage == SelectionStage.HEADER:
            instruction = "Step 1/2: Select HEADER Region (Name/Organization) - Drag to select, Enter to confirm, ESC to cancel"
        elif self._selection_stage == SelectionStage.BODY:
            instruction = "Step 2/2: Select BODY Region (Text Content) - Drag to select, Enter to confirm, ESC to cancel"
        else:
            instruction = "Selection Complete"
    else:
        # Original single-stage instructions
        region_name = "Header" if self._region_type == RegionType.HEADER else "Body"
        instruction = f"Select {region_name} Region - Drag to select, ESC to cancel, Tab to switch region"

    # ... rest of drawing code ...
```

#### 2.6 確定済み領域の表示

ボディ選択中に、確定済みのヘッダー領域を薄く表示:

```python
def paintEvent(self, event: QPaintEvent) -> None:
    """Paint the overlay and selection rectangle."""
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw the semi-transparent overlay
    painter.fillRect(self.rect(), self.OVERLAY_COLOR)

    # Draw confirmed header rect (if in body selection stage)
    if self._two_stage_mode and self._selection_stage == SelectionStage.BODY and self._header_rect:
        self._draw_confirmed_region(painter, self._header_rect, "Header")

    # Draw current selection if active
    if self._selection_rect and not self._selection_rect.isNull():
        self._draw_selection(painter)

    # Draw instructions
    self._draw_instructions(painter)

    painter.end()

def _draw_confirmed_region(self, painter: QPainter, rect: QRect, label: str) -> None:
    """Draw a confirmed region with a label."""
    # Green color for confirmed regions
    confirmed_border = QColor(100, 200, 100)
    confirmed_fill = QColor(100, 200, 100, 40)

    painter.fillRect(rect, confirmed_fill)

    pen = QPen(confirmed_border)
    pen.setWidth(2)
    pen.setStyle(Qt.PenStyle.SolidLine)
    painter.setPen(pen)
    painter.drawRect(rect)

    # Draw label
    font = QFont("Hiragino Sans", 10)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QPen(confirmed_border))
    painter.drawText(rect.topLeft() + QPoint(5, -5), f"{label} (confirmed)")
```

### 完了基準
- [ ] ヘッダー選択 -> Enter -> ボディ選択 -> Enter のフローが動作
- [ ] 確定済み領域が視覚的に区別される（緑色）
- [ ] 各ステージで適切な指示が表示される
- [ ] ESCで全体キャンセル可能
- [ ] 完了時に `regions_selected` シグナルが正しい座標で発火

---

## Task 3: 範囲指定モード起動用ホットキー実装

### 目的
新しいホットキー（Cmd+Shift+R）で範囲指定モードを起動し、選択結果を現在のプロファイルに反映する。

### 対象ファイル
- `/Users/dansetsu/NoaLog/src/app_controller.py`
- `/Users/dansetsu/NoaLog/src/main.py`

### 作業内容

#### 3.1 AppController への範囲指定機能追加

```python
from ui.widgets.capture_overlay import CaptureOverlay, SelectionStage

class AppController(QObject):
    # ... existing signals ...
    region_selection_started = Signal()
    region_selection_completed = Signal(object, object)  # header_rect, body_rect

    def __init__(self, ...):
        # ... existing code ...
        self._capture_overlay: Optional[CaptureOverlay] = None
        self._region_selection_hotkey_id: Optional[str] = None

    def register_region_selection_hotkey(self, hotkey: Hotkey) -> None:
        """Register hotkey for starting region selection mode."""
        if self._hotkey_manager:
            self._region_selection_hotkey_id = self._hotkey_manager.register_hotkey(
                hotkey, self._on_region_selection_hotkey
            )
            logger.info(f"Region selection hotkey registered: {hotkey}")

    def _on_region_selection_hotkey(self) -> None:
        """Handle region selection hotkey trigger."""
        logger.debug("Region selection hotkey triggered")
        # Qt のメインスレッドで実行
        QTimer.singleShot(0, self.start_region_selection)

    @Slot()
    def start_region_selection(self) -> None:
        """Start the two-stage region selection process."""
        if self._capture_overlay and self._capture_overlay.isVisible():
            logger.warning("Region selection already in progress")
            return

        self.region_selection_started.emit()

        # Create overlay
        self._capture_overlay = CaptureOverlay()
        self._capture_overlay.regions_selected.connect(self._on_regions_selected)
        self._capture_overlay.selection_cancelled.connect(self._on_region_selection_cancelled)

        # Start two-stage selection
        self._capture_overlay.start_two_stage_selection()

        if self._main_window:
            self._main_window.set_status("範囲指定モード: ヘッダー領域を選択してください")

    @Slot(object, object)
    def _on_regions_selected(self, header_rect, body_rect) -> None:
        """Handle completion of region selection."""
        logger.info(f"Regions selected - Header: {header_rect}, Body: {body_rect}")

        # Update current profile
        if self._current_profile:
            self._current_profile.header_rect = header_rect
            self._current_profile.body_rect = body_rect
            self._current_profile.updated_at = datetime.now().isoformat()

            # Save profile
            self._save_profile(self._current_profile)

            self.region_selection_completed.emit(header_rect, body_rect)

            if self._main_window:
                self._main_window.set_status(
                    f"範囲指定完了 - Header: ({header_rect.x}, {header_rect.y}, {header_rect.width}x{header_rect.height}), "
                    f"Body: ({body_rect.x}, {body_rect.y}, {body_rect.width}x{body_rect.height})"
                )
        else:
            if self._main_window:
                self._main_window.set_status("エラー: プロファイルが選択されていません")

        self._cleanup_overlay()

    @Slot()
    def _on_region_selection_cancelled(self) -> None:
        """Handle cancellation of region selection."""
        logger.info("Region selection cancelled")
        if self._main_window:
            self._main_window.set_status("範囲指定がキャンセルされました")
        self._cleanup_overlay()

    def _cleanup_overlay(self) -> None:
        """Clean up the capture overlay."""
        if self._capture_overlay:
            self._capture_overlay.deleteLater()
            self._capture_overlay = None

    def _save_profile(self, profile: Profile) -> None:
        """Save a profile to disk."""
        profiles_dir = self.config.get_profiles_dir()
        profile_file = profiles_dir / f"{profile.id}.json"

        try:
            with open(profile_file, "w", encoding="utf-8") as f:
                f.write(profile.to_json())
            logger.info(f"Profile saved: {profile_file}")
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
```

#### 3.2 main.py でのホットキー登録

```python
def main():
    # ... existing code ...

    # Register hotkeys
    # OCR capture hotkey is set per-profile (handled by set_current_profile)

    # Region selection hotkey (global)
    region_selection_hotkey = Hotkey(keys=["cmd", "shift", "r"])
    controller.register_region_selection_hotkey(region_selection_hotkey)

    # Start hotkey listener
    controller.start_hotkey_listener()

    # ... rest of code ...
```

### 完了基準
- [ ] Cmd+Shift+R で範囲指定モードが起動
- [ ] 選択完了後、プロファイルの `header_rect` と `body_rect` が更新される
- [ ] プロファイルがJSONファイルとして保存される
- [ ] ステータスバーに適切なメッセージが表示される

---

## Task 4: 編集機能（ダブルクリック編集）

### 目的
ログ一覧と詳細パネルでダブルクリックによるインライン編集を可能にする。

### 対象ファイル
- `/Users/dansetsu/NoaLog/src/ui/views/main_window.py`

### 作業内容

#### 4.1 LogEntryWidget のダブルクリック編集

```python
class LogEntryWidget(QFrame):
    """ログエントリ表示ウィジェット。"""

    clicked = Signal(str)  # entry_id
    double_clicked = Signal(str)  # entry_id for editing
    entry_edited = Signal(str, str, str)  # entry_id, field_name, new_value

    def __init__(self, entry: LogEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self._editing = False
        self._edit_widget: Optional[QLineEdit] = None
        # ... existing code ...

    def mouseDoubleClickEvent(self, event):
        """ダブルクリックで編集モード."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.entry.id)
            self._start_edit_mode()
        super().mouseDoubleClickEvent(event)

    def _start_edit_mode(self) -> None:
        """Start inline editing of the body text."""
        if self._editing:
            return

        self._editing = True

        # Find the body label and replace with QLineEdit
        body_label = self.findChild(QLabel)  # Get the body text label
        if body_label and hasattr(self, '_body_label'):
            self._body_label = body_label

            # Create edit widget
            self._edit_widget = QLineEdit(self.entry.display_body, self)
            self._edit_widget.setGeometry(body_label.geometry())
            self._edit_widget.setFocus()
            self._edit_widget.selectAll()

            # Connect signals
            self._edit_widget.returnPressed.connect(self._finish_edit)
            self._edit_widget.editingFinished.connect(self._finish_edit)

            # Install event filter for Escape
            self._edit_widget.installEventFilter(self)

            body_label.hide()
            self._edit_widget.show()

    def _finish_edit(self) -> None:
        """Finish editing and save changes."""
        if not self._editing or not self._edit_widget:
            return

        new_value = self._edit_widget.text().strip()
        if new_value != self.entry.display_body:
            self.entry.edited_body_text = new_value
            self.entry_edited.emit(self.entry.id, "body_text", new_value)

        self._cancel_edit()

    def _cancel_edit(self) -> None:
        """Cancel editing without saving."""
        if self._edit_widget:
            self._edit_widget.deleteLater()
            self._edit_widget = None

        if hasattr(self, '_body_label') and self._body_label:
            self._body_label.show()

        self._editing = False

    def eventFilter(self, obj, event) -> bool:
        """Handle Escape key to cancel edit."""
        if obj == self._edit_widget and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._cancel_edit()
                return True
        return super().eventFilter(obj, event)
```

#### 4.2 DetailPanel のダブルクリック編集

```python
class EditableLabel(QLabel):
    """Label that becomes editable on double-click."""

    value_changed = Signal(str, str)  # field_name, new_value

    def __init__(self, field_name: str, text: str = "", parent=None):
        super().__init__(text, parent)
        self.field_name = field_name
        self._edit_widget: Optional[QLineEdit] = None
        self._editing = False

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
        self._original_text = self.text()

        # Create edit widget at same position
        self._edit_widget = QLineEdit(self.text(), self.parent())
        self._edit_widget.setGeometry(self.geometry())
        self._edit_widget.setFont(self.font())
        self._edit_widget.setFocus()
        self._edit_widget.selectAll()

        self._edit_widget.returnPressed.connect(self._finish_edit)
        self._edit_widget.editingFinished.connect(self._finish_edit)

        self.hide()
        self._edit_widget.show()

    def _finish_edit(self) -> None:
        """Finish editing."""
        if not self._editing or not self._edit_widget:
            return

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


class DetailPanel(QFrame):
    """詳細パネル - 選択したログエントリの詳細を表示。"""

    # ... existing signals ...
    entry_field_changed = Signal(str, str, str)  # entry_id, field_name, new_value

    def _setup_ui(self):
        # Replace QLabel with EditableLabel for editable fields

        # 話者名
        self.name_label = EditableLabel("speaker_name", "")
        self.name_label.setObjectName("speakerLabel")
        self.name_label.setWordWrap(True)
        self.name_label.value_changed.connect(self._on_field_changed)
        content_layout.addWidget(self.name_label)

        # 所属
        self.org_label = EditableLabel("speaker_org", "")
        self.org_label.setObjectName("organizationLabel")
        self.org_label.setWordWrap(True)
        self.org_label.value_changed.connect(self._on_field_changed)
        content_layout.addWidget(self.org_label)

        # 本文
        self.body_label = EditableLabel("body_text", "")
        self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body_label.value_changed.connect(self._on_field_changed)
        content_layout.addWidget(self.body_label)

        # ... rest of UI ...

    def _on_field_changed(self, field_name: str, new_value: str) -> None:
        """Handle field value change."""
        if self._current_entry:
            self.entry_field_changed.emit(
                self._current_entry.id, field_name, new_value
            )
```

#### 4.3 MainWindow での編集イベント処理

```python
class MainWindow(QMainWindow):
    # ... existing code ...

    def _connect_signals(self):
        # ... existing connections ...

        # Detail panel edit events
        self.detail_panel.entry_field_changed.connect(self._on_entry_field_changed)

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
                # Replace with updated widget
                new_widget = LogEntryWidget(entry)
                new_widget.clicked.connect(lambda eid=entry.id: self._on_entry_clicked(eid))
                item.setSizeHint(new_widget.sizeHint())
                self.log_list.setItemWidget(item, new_widget)
                break
```

### 完了基準
- [ ] ログ一覧でダブルクリックすると編集モードになる
- [ ] 詳細パネルの話者名/所属/本文がダブルクリックで編集可能
- [ ] Enterで確定、Escapeでキャンセル
- [ ] 編集内容が `edited_*` フィールドに保存される
- [ ] 表示が即座に更新される

---

## 実装順序

1. **Task 1**: ハードコードプロファイル削除（最初に実施）
2. **Task 2**: CaptureOverlay 2段階選択モード
3. **Task 3**: 範囲指定モード起動用ホットキー
4. **Task 4**: 編集機能

## 注意事項

- 既存のテストがあれば、変更後も通ることを確認
- 各タスク完了後、動作確認を実施
- エラーハンドリングを適切に実装
- ログ出力を追加して、デバッグしやすくする
- 完了後、`reports/collaborative/dev-manager-report.md` に作業レポートを作成

---

作成日: 2026-01-05
Chief Producer: chief-producer
