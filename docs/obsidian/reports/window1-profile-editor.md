# ProfileEditorDialog Implementation Report

**Date**: 2026-01-04
**Author**: frontend-dev
**Status**: Completed

## Overview

ProfileEditorDialogは、NoaLogアプリケーションにおけるプロファイル編集機能を提供するダイアログコンポーネントです。PySide6を使用して実装され、既存のNoaLogテーマに準拠したスタイリングが適用されています。

## Implemented Features

### 1. Basic Profile Information
- **Profile Name**: 必須項目。バリデーション付きのテキスト入力
- **Description**: オプション項目。複数行テキスト入力対応

### 2. Capture Region Configuration
- **Header Region**: 話者名をキャプチャする矩形領域（x, y, width, height）
- **Body Region**: 会話本文をキャプチャする矩形領域

### 3. Hotkey Configuration
- QKeySequenceEditを使用したキーボードショートカット設定
- macOS/Windows互換のキーマッピング

### 4. Dialog Actions
- **Save**: バリデーション後にプロファイルを保存
- **Cancel**: 変更を破棄してダイアログを閉じる

## File Structure

```
src/ui/views/
├── __init__.py                 # Updated exports
├── main_window.py              # Existing main window
└── profile_editor.py           # NEW: Profile editor dialog
```

## Classes and Methods

### ProfileEditorDialog

メインダイアログクラス。

```python
class ProfileEditorDialog(QDialog):
    """プロファイル編集ダイアログ"""

    # Signals
    profile_saved = Signal(object)  # Emits Profile on save

    # Public Methods
    def set_profile(self, profile: Profile)  # Load existing profile
    def get_profile(self) -> Profile         # Get edited profile
    def clear(self)                          # Clear all inputs
    def set_new_mode(self)                   # Set to new profile mode
```

| Method | Description |
|--------|-------------|
| `set_profile(profile)` | 既存プロファイルを編集モードでロード |
| `get_profile()` | 現在の入力値からProfileオブジェクトを取得 |
| `clear()` | すべての入力フィールドをクリア |
| `set_new_mode()` | 新規プロファイル作成モードに設定 |

### RectEditorWidget

矩形領域を編集するための再利用可能なウィジェット。

```python
class RectEditorWidget(QGroupBox):
    """矩形領域編集ウィジェット"""

    # Signals
    value_changed = Signal()  # Emitted on any value change

    # Public Methods
    def get_rect(self) -> Optional[Rect]
    def set_rect(self, rect: Optional[Rect])
    def clear(self)
```

| Property | Type | Range |
|----------|------|-------|
| X | int | 0-9999 px |
| Y | int | 0-9999 px |
| Width | int | 1-9999 px |
| Height | int | 1-9999 px |

### HotkeyEditorWidget

ホットキー設定用ウィジェット。

```python
class HotkeyEditorWidget(QGroupBox):
    """ホットキー編集ウィジェット"""

    # Signals
    value_changed = Signal()

    # Public Methods
    def get_hotkey(self) -> Optional[Hotkey]
    def set_hotkey(self, hotkey: Optional[Hotkey])
    def clear()
```

## Usage Examples

### Creating a New Profile

```python
from ui.views import ProfileEditorDialog

dialog = ProfileEditorDialog(parent_window)
dialog.set_new_mode()

if dialog.exec() == QDialog.Accepted:
    new_profile = dialog.get_profile()
    # Save new_profile to database/file
```

### Editing an Existing Profile

```python
from ui.views import ProfileEditorDialog
from models import Profile

existing_profile = Profile(
    name="Game Profile",
    description="For capturing game dialogues",
    header_rect=Rect(x=100, y=200, width=300, height=50),
    body_rect=Rect(x=100, y=260, width=300, height=200),
    hotkey=Hotkey(keys=["cmd", "shift", "l"]),
)

dialog = ProfileEditorDialog(parent_window)
dialog.set_profile(existing_profile)

if dialog.exec() == QDialog.Accepted:
    updated_profile = dialog.get_profile()
    # Save updated_profile
```

### Using the profile_saved Signal

```python
def on_profile_saved(profile):
    print(f"Profile saved: {profile.name}")
    # Handle save logic

dialog = ProfileEditorDialog(parent_window)
dialog.profile_saved.connect(on_profile_saved)
dialog.exec()
```

## Theme Integration

ダイアログは `/src/ui/styles/theme.qss` のスタイルシートを自動的に読み込みます。以下のObjectNameが使用されています：

| ObjectName | Widget Type | Purpose |
|------------|-------------|---------|
| `titleLabel` | QLabel | Dialog title |
| `subtitleLabel` | QLabel | Section descriptions |
| `primaryButton` | QPushButton | Save button |
| `secondaryButton` | QPushButton | Cancel/Clear buttons |

## Dependencies

- **PySide6**: Qt for Python bindings
- **models.py**: Profile, Rect, Hotkey data classes

## Validation Rules

1. **Profile Name**: Required (cannot be empty)
2. **Header/Body Rect**: Width and height must be > 0
3. **Hotkey**: Optional (can be empty)

## Screenshots

*Note: Screenshots can be added after visual testing*

## Future Improvements

### High Priority
1. **Screen Region Picker**: マウスでキャプチャ領域を選択するオーバーレイ機能
2. **Profile Duplication**: 既存プロファイルのコピー機能
3. **Preview Panel**: キャプチャ領域のリアルタイムプレビュー

### Medium Priority
4. **Hotkey Conflict Detection**: 既存のホットキーとの競合チェック
5. **Import/Export**: 単一プロファイルのJSON形式エクスポート
6. **Undo/Redo**: 編集操作の取り消し機能

### Low Priority
7. **Profile Templates**: よく使われる設定のテンプレート
8. **Multi-Region Support**: 複数のキャプチャ領域サポート
9. **OCR Settings Per Profile**: プロファイルごとのOCR設定

## Test Plan

### Unit Tests
- [ ] Profile name validation
- [ ] Rect value boundary tests
- [ ] Hotkey parsing tests
- [ ] Signal emission tests

### Integration Tests
- [ ] Dialog open/close cycle
- [ ] Profile load and save roundtrip
- [ ] Theme application verification

### E2E Scenarios
1. Create new profile with all fields
2. Edit existing profile and verify changes
3. Cancel editing and verify no changes
4. Test hotkey capture functionality

## Related Files

- [[src/models.py]] - Data models
- [[src/ui/views/main_window.py]] - Main window integration
- [[src/ui/styles/theme.qss]] - Theme stylesheet
- [[docs/obsidian/architecture/overview.md]] - Architecture overview

## Changelog

| Date | Change |
|------|--------|
| 2026-01-04 | Initial implementation |

---

*Generated by frontend-dev agent*
