# DetailPanel 実装レポート

**Date**: 2026-01-11
**Author**: frontend-dev
**Status**: Completed

---

## 概要

DetailPanelは、選択したログエントリの詳細表示・編集を行う右ペインウィジェット。3つのタブ（編集/元テキスト/差分）と Undo/Redo 機能を提供。

**実装ファイル**: `/src/ui/widgets/detail_panel.py`

---

## 3つのタブ

| タブ | インデックス | 説明 |
|------|-------------|------|
| 編集 | 0 | 編集可能なテキストエリア |
| 元テキスト | 1 | OCR結果（読み取り専用） |
| 差分 | 2 | 編集前後の差分表示 |

---

## クラス構成

### DetailPanel (QFrame)

```python
class DetailPanel(QFrame):
    entry_updated = Signal(object)  # LogEntry

    def __init__(self, parent=None)
    def set_entry(self, entry: LogEntry)
    def get_entry(self) -> Optional[LogEntry]
    def clear(self)
    def undo(self)
    def redo(self)
    def can_undo(self) -> bool
    def can_redo(self) -> bool
```

### EditableHeaderField (QFrame)

```python
class EditableHeaderField(QFrame):
    value_changed = Signal()

    def get_speaker_name(self) -> str
    def get_speaker_org(self) -> str
    def set_values(self, name: str, org: str)
```

### EditableTextArea (QTextEdit)

```python
class EditableTextArea(QTextEdit):
    # 編集可能なテキストエリア
    # フォーカス時にボーダー色変更
```

### DiffTextArea (QTextEdit)

```python
class DiffTextArea(QTextEdit):
    def set_diff(self, original: str, edited: str)
```

---

## パネルレイアウト

```
┌─────────────────────────────────────────────┐
│ 詳細ヘッダー                                 │
│ ┌─────────────────────────────────────────┐ │
│ │ 話者名           組織名                 │ │
│ │ ┌─────────────┐ ┌─────────────────────┐ │ │
│ │ │ Alice       │ │ Engineering         │ │ │
│ │ └─────────────┘ └─────────────────────┘ │ │
│ │ 2026-01-11 12:34:56                     │ │
│ └─────────────────────────────────────────┘ │
│                                              │
│ ┌────────┬────────────┬────────┐            │
│ │  編集  │ 元テキスト │  差分  │            │
│ └────────┴────────────┴────────┘            │
│ ┌─────────────────────────────────────────┐ │
│ │                                         │ │
│ │ テキストエリア                          │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
│                                              │
│ [↩ 元に戻す] [↪ やり直し]                   │
└─────────────────────────────────────────────┘
```

---

## Undo/Redo システム

```python
from PySide6.QtWidgets import QUndoStack, QUndoCommand

class EditCommand(QUndoCommand):
    """編集操作のUndoコマンド"""

    def __init__(self, panel, old_text, new_text, description="Edit"):
        super().__init__(description)
        self._panel = panel
        self._old_text = old_text
        self._new_text = new_text

    def undo(self):
        self._panel._set_text_without_undo(self._old_text)

    def redo(self):
        self._panel._set_text_without_undo(self._new_text)

# 使用
self._undo_stack = QUndoStack(self)
self._undo_stack.push(EditCommand(self, old, new))
```

---

## 差分表示

difflib.SequenceMatcherを使用した差分ハイライト：

```python
def set_diff(self, original: str, edited: str):
    """差分をハイライト表示"""
    matcher = difflib.SequenceMatcher(None, original, edited)

    html_parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            html_parts.append(html.escape(original[i1:i2]))
        elif tag == "delete":
            html_parts.append(f'<span style="background:#FFCDD2;text-decoration:line-through;">{html.escape(original[i1:i2])}</span>')
        elif tag == "insert":
            html_parts.append(f'<span style="background:#C8E6C9;">{html.escape(edited[j1:j2])}</span>')
        elif tag == "replace":
            html_parts.append(f'<span style="background:#FFCDD2;text-decoration:line-through;">{html.escape(original[i1:i2])}</span>')
            html_parts.append(f'<span style="background:#C8E6C9;">{html.escape(edited[j1:j2])}</span>')

    self.setHtml("".join(html_parts))
```

差分表示例：
- 削除: <span style="background:#FFCDD2">~~削除されたテキスト~~</span>
- 追加: <span style="background:#C8E6C9">追加されたテキスト</span>

---

## 使用例

### 基本的な使用

```python
from ui.widgets import DetailPanel
from models import LogEntry

panel = DetailPanel()
panel.set_entry(entry)

# 更新を監視
panel.entry_updated.connect(lambda e: storage.update(e))
```

### Undo/Redo

```python
# Undo/Redoボタン状態
undo_btn.setEnabled(panel.can_undo())
redo_btn.setEnabled(panel.can_redo())

# 操作
panel.undo()
panel.redo()
```

### タブ切り替え

```python
# 差分タブに切り替え
panel._tab_widget.setCurrentIndex(2)
```

---

## ObjectName

| 要素 | ObjectName |
|------|-----------|
| パネル本体 | `rightPane` |
| 詳細ヘッダー | `detailHeader` |
| 話者ラベル | `detailSpeaker` |
| 組織ラベル | `detailOrg` |
| タイムスタンプ | `detailTimestamp` |
| タブウィジェット | `viewTabs` |
| タブバー | `viewTabBar` |
| 編集エリア | `editableBody` |
| 元テキストエリア | `rawBody` |
| 差分エリア | `diffView` |
| Undoボタン | `undoButton` |
| Redoボタン | `redoButton` |

---

## QSSスタイル

```css
QTextEdit#editableBody {
    background-color: #FAFAFA;
    border: 1px solid #E5EAF2;
    border-radius: 10px;
}

QTextEdit#editableBody:focus {
    border-color: #63C6FF;
    background-color: #FFFFFF;
}

QTextEdit#rawBody {
    background-color: #F6F1E6;
    color: #5A6578;
}

QTextEdit#diffView {
    font-family: "SF Mono", "Consolas", monospace;
}
```

---

## テスト項目

- [ ] エントリ表示・更新
- [ ] タブ切り替え
- [ ] 編集 → 差分タブ反映
- [ ] Undo/Redo動作
- [ ] Undo/Redoボタン状態
- [ ] 話者名/組織の編集
- [ ] 空エントリ時の表示

---

## 関連ファイル

- [[ui-improvement-chief-producer]] - プロジェクト統括
- [[ui-improvement-main-window]] - パネル配置
- `/src/ui/widgets/detail_panel.py` - 実装

---

*Generated by frontend-dev*
