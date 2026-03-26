# ProfileEditor再設計レポート

**Date**: 2026-01-13
**Author**: frontend-dev
**Status**: Completed

---

## 概要

ProfileEditorDialogをスクロール対応レイアウトに再設計。生塩ノアテーマを適用し、各セクションを整理。

**実装ファイル**: `/src/ui/views/profile_editor.py`

---

## 課題

元の実装では以下の問題があった：
1. 全コンテンツを1ページに詰め込み、文字が重なる
2. ウィンドウサイズが小さいと項目が見切れる
3. PySide6非対応のメソッド使用

---

## 新レイアウト構成

```
┌─────────────────────────────────────────────────────┐
│ HEADER (固定・濃紺 #0B1B2B)                          │
│ Edit Profile                                         │
├─────────────────────────────────────────────────────┤
│ SCROLL AREA (スクロール可能・アイボリー #F6F1E6)      │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Basic Information                               │ │
│ │ ┌─────────────────────────────────────────────┐ │ │
│ │ │ Profile Name                                │ │ │
│ │ │ [________________________]                  │ │ │
│ │ │ Description (Optional)                      │ │ │
│ │ │ [________________________]                  │ │ │
│ │ └─────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Capture Regions                                │ │
│ │ Define the screen regions for OCR processing.  │ │
│ │ ┌───────────────────────────────────────────┐  │ │
│ │ │ Header Region (Speaker Name)              │  │ │
│ │ │ X: [___] Y: [___] W: [___] H: [___]       │  │ │
│ │ └───────────────────────────────────────────┘  │ │
│ │ ┌───────────────────────────────────────────┐  │ │
│ │ │ Body Region (Dialogue Text)               │  │ │
│ │ │ X: [___] Y: [___] W: [___] H: [___]       │  │ │
│ │ └───────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Hotkey Settings                                │ │
│ │ ┌───────────────────────────────────────────┐  │ │
│ │ │ Capture Hotkey                            │  │ │
│ │ │ [____________________] [Clear]            │  │ │
│ │ │ Current: Cmd+Shift+L                      │  │ │
│ │ └───────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
├─────────────────────────────────────────────────────┤
│ FOOTER (固定・白)                                    │
│ [Cancel]                              [Save]        │
└─────────────────────────────────────────────────────┘
```

---

## 実装詳細

### 1. メインレイアウト

```python
# メインレイアウト（ダイアログ全体）
main_layout = QVBoxLayout(self)
main_layout.setContentsMargins(0, 0, 0, 0)
main_layout.setSpacing(0)
```

### 2. 固定ヘッダー

```python
header_frame = QFrame()
header_frame.setStyleSheet("""
    QFrame {
        background-color: #0B1B2B;
        padding: 16px;
    }
""")
```

### 3. スクロールエリア

```python
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
""")
```

### 4. セクション分割

```python
# セクション1: 基本情報
basic_group = QGroupBox("Basic Information")

# セクション2: キャプチャ領域
capture_group = QGroupBox("Capture Regions")

# セクション3: ホットキー
hotkey_group = QGroupBox("Hotkey Settings")
```

### 5. 固定フッター

```python
footer_frame = QFrame()
footer_frame.setStyleSheet("""
    QFrame {
        background-color: #FFFFFF;
        border-top: 1px solid #E0D8C8;
    }
""")
```

---

## PySide6互換性修正

### QKeySequenceEdit.setPlaceholderText削除

```python
# Before (エラー)
self.key_sequence_edit.setPlaceholderText("Click to set hotkey...")

# After (修正)
self.key_sequence_edit = QKeySequenceEdit()
# Note: QKeySequenceEdit doesn't support setPlaceholderText
```

### QSpinBox.valueChangedシグナル修正

```python
# Before (TypeError)
self.x_spin.valueChanged.connect(self.value_changed.emit)

# After (修正)
self.x_spin.valueChanged.connect(lambda _: self.value_changed.emit())
```

---

## スタイルヘルパーメソッド

### GroupBoxスタイル

```python
def _get_groupbox_style(self) -> str:
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
```

### 入力フィールドスタイル

```python
def _get_input_style(self) -> str:
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
```

---

## カラーパレット

| 要素 | 色 | 用途 |
|------|-----|------|
| ヘッダー背景 | #0B1B2B | 濃紺 |
| スクロール背景 | #F6F1E6 | アイボリー |
| フッター背景 | #FFFFFF | 白 |
| ボーダー | #E0D8C8 | ベージュ |
| アクセント | #63C6FF | Noa Cyan |
| テキスト | #333 | ダークグレー |

---

## ウィンドウサイズ

```python
self.setMinimumSize(520, 500)
self.resize(580, 650)
```

---

## 関連ファイル

- [[settings-integration]] - Settings機能統合
- [[ui-improvement-main-window]] - NoaMainWindow
- [[window1-profile-editor]] - 元ProfileEditorDialog
- `/src/ui/views/profile_editor.py` - 実装

---

*Generated by frontend-dev*
