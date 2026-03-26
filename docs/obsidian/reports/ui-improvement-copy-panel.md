# CopyPanel 実装レポート

**Date**: 2026-01-11
**Author**: frontend-dev
**Status**: Completed

---

## 概要

CopyPanelは、選択したログエントリを複数のフォーマットでクリップボードにコピーするためのパネル。Plain/Markdown/JSON形式をサポート。

**実装ファイル**: `/src/ui/widgets/copy_panel.py`

---

## フォーマット

| フォーマット | Enum値 | 出力例 |
|-------------|--------|--------|
| PLAIN | `plain` | `Alice: Hello world` |
| MARKDOWN | `markdown` | `**Alice**\n> Hello world` |
| JSON | `json` | `{"speaker": "Alice", "body": "Hello world"}` |

---

## クラス構成

### CopyFormat (Enum)

```python
class CopyFormat(Enum):
    PLAIN = "plain"
    MARKDOWN = "markdown"
    JSON = "json"
```

### CopyPanel (QFrame)

```python
class CopyPanel(QFrame):
    copy_requested = Signal(str)  # フォーマット名
    format_changed = Signal(str)  # フォーマット名

    def __init__(self, parent=None)
    def set_entries(self, entries: List[LogEntry])
    def get_entries(self) -> List[LogEntry]
    def get_current_format(self) -> CopyFormat
    def set_format(self, format_type: CopyFormat)
    def get_formatted_text(self) -> str
    def copy_to_clipboard(self)
    def set_copy_enabled(self, enabled: bool)
```

---

## パネルレイアウト

```
┌─────────────────────────────────────────────┐
│ コピー形式                                   │
│ ┌──────────┬──────────┬──────────┐          │
│ │  Plain   │ Markdown │   JSON   │          │
│ └──────────┴──────────┴──────────┘          │
│                                              │
│ ┌─────────────────────────────────┐         │
│ │      📋 コピー (3件)            │         │
│ └─────────────────────────────────┘         │
│                                              │
│ 選択中: 3件                                  │
└─────────────────────────────────────────────┘
```

---

## フォーマット出力

### Plain

```python
def _format_plain(self, entries: List[LogEntry]) -> str:
    lines = []
    for entry in entries:
        header = entry.display_header
        body = entry.display_body
        lines.append(f"{header}: {body}")
    return "\n\n".join(lines)
```

出力例：
```
Alice / Engineering: Hello, this is a test message.

Bob / Marketing: Thank you for your message.
```

### Markdown

```python
def _format_markdown(self, entries: List[LogEntry]) -> str:
    lines = []
    for entry in entries:
        header = entry.display_header
        body = entry.display_body
        lines.append(f"**{header}**\n\n> {body}")
    return "\n\n---\n\n".join(lines)
```

出力例：
```markdown
**Alice / Engineering**

> Hello, this is a test message.

---

**Bob / Marketing**

> Thank you for your message.
```

### JSON

```python
def _format_json(self, entries: List[LogEntry]) -> str:
    data = []
    for entry in entries:
        data.append({
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "speaker_name": entry.display_speaker_name,
            "speaker_org": entry.display_speaker_org,
            "body": entry.display_body,
            "log_type": entry.log_type.value,
        })
    return json.dumps(data, ensure_ascii=False, indent=2)
```

出力例：
```json
[
  {
    "id": "abc123",
    "timestamp": "2026-01-11T12:34:56",
    "speaker_name": "Alice",
    "speaker_org": "Engineering",
    "body": "Hello, this is a test message.",
    "log_type": "dialogue"
  }
]
```

---

## クリップボード操作

```python
def copy_to_clipboard(self):
    """クリップボードにコピー"""
    text = self.get_formatted_text()
    clipboard = QApplication.clipboard()
    clipboard.setText(text)
    self.copy_requested.emit(self._current_format.value)
```

---

## 使用例

### 基本的な使用

```python
from ui.widgets import CopyPanel, CopyFormat
from models import LogEntry

panel = CopyPanel()
panel.set_entries([entry1, entry2, entry3])
panel.set_format(CopyFormat.MARKDOWN)
panel.copy_to_clipboard()
```

### シグナル接続

```python
def on_copy_requested(format_name: str):
    print(f"Copied as {format_name}")

panel.copy_requested.connect(on_copy_requested)
```

### フォーマット変更監視

```python
def on_format_changed(format_name: str):
    # プレビュー更新など
    preview.setText(panel.get_formatted_text())

panel.format_changed.connect(on_format_changed)
```

---

## ObjectName

| 要素 | ObjectName |
|------|-----------|
| パネル本体 | `copyPanel` |
| フォーマットトグル | `formatToggle` |
| コピーボタン | `copyButton` |

---

## QSSスタイル

```css
QFrame#copyPanel {
    background-color: #F6F1E6;
    border-radius: 14px;
    padding: 16px;
}

QPushButton#copyButton {
    background-color: #63C6FF;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-weight: 600;
    color: #FFFFFF;
}

QPushButton#copyButton:hover {
    background-color: #3BA8E8;
}

QPushButton#copyButton:disabled {
    background-color: #C8D2E0;
    color: #8A95A8;
}
```

---

## テスト項目

- [ ] 3フォーマットすべての出力確認
- [ ] フォーマット切り替えUI
- [ ] クリップボードへのコピー
- [ ] 0件時のボタン無効化
- [ ] 件数表示の更新
- [ ] 日本語テキストのJSON出力

---

## 関連ファイル

- [[ui-improvement-chief-producer]] - プロジェクト統括
- [[ui-improvement-main-window]] - パネル配置
- `/src/ui/widgets/copy_panel.py` - 実装

---

*Generated by frontend-dev*
