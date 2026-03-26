# NoaMainWindow 実装レポート

**Date**: 2026-01-11
**Author**: frontend-dev
**Status**: Completed

---

## 概要

NoaMainWindowは、生塩ノアテーマを適用した新しいメインウィンドウ。3ペインレイアウト + ヘッダー + ステータスバーの構成。

**実装ファイル**: `/src/ui/views/noa_main_window.py`

---

## レイアウト構成

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER (濃紺 #0B1B2B)                                           │
│ [Halo] NoaLog                              Hotkey: ⌘+Shift+L    │
├────────────────┬─────────────────────────┬──────────────────────┤
│ LEFT PANE      │ CENTER PANE             │ RIGHT PANE           │
│ (管理パネル)    │ (ログタイムライン)        │ (書記席 - 詳細/編集)  │
│                │                         │                      │
│ Profile:       │ 🔍 検索...               │ 詳細ヘッダー          │
│ [▼ Default   ] │                         │ ┌─────────────────┐  │
│                │ ┌─────────────────────┐ │ │ Alice           │  │
│ 統計:          │ │ LogCard 1           │ │ │ Engineering     │  │
│ ・総ログ: 42    │ └─────────────────────┘ │ │ 12:34:56        │  │
│ ・今日: 5      │ ┌─────────────────────┐ │ └─────────────────┘  │
│                │ │ LogCard 2           │ │                      │
│ [新規] [編集]   │ └─────────────────────┘ │ [編集|元|差分]        │
│ [領域選択]     │ ┌─────────────────────┐ │ ┌─────────────────┐  │
│                │ │ LogCard 3           │ │ │ テキストエリア   │  │
│                │ └─────────────────────┘ │ └─────────────────┘  │
│                │                         │                      │
│                │                         │ [↩ Undo] [↪ Redo]    │
│                │                         │                      │
│                │                         │ コピーパネル          │
│                │                         │ [Plain|MD|JSON]      │
│                │                         │ [📋 コピー (3件)]    │
├────────────────┴─────────────────────────┴──────────────────────┤
│ STATUS BAR                                                       │
│ Ready                                    OCR: PaddleOCR          │
└─────────────────────────────────────────────────────────────────┘
```

---

## ペイン幅

| ペイン | 幅 | 最小 | 最大 |
|--------|-----|------|------|
| LEFT | 240px | 200px | 300px |
| CENTER | 可変 | 400px | - |
| RIGHT | 360px | 320px | 450px |

---

## クラス構成

### NoaMainWindow (QMainWindow)

```python
class NoaMainWindow(QMainWindow):
    capture_requested = Signal()
    profile_changed = Signal(object)

    def __init__(self, config: Config, parent=None)

    # エントリ管理
    def add_log_entry(self, entry: LogEntry)
    def set_log_entries(self, entries: List[LogEntry])
    def clear_log_entries(self)

    # プロファイル管理
    def set_profiles(self, profiles: List[Profile])
    def get_current_profile(self) -> Optional[Profile]
    def set_current_profile(self, profile: Profile)

    # 状態表示
    def set_status(self, message: str)
    def set_ocr_status(self, engine_name: str)

    # マルチセレクト
    def set_multi_select_mode(self, enabled: bool)
    def get_selected_entries(self) -> List[LogEntry]
    def select_all_entries()
    def deselect_all_entries()
```

---

## コンポーネント統合

### ヘッダー

```python
def _create_header(self) -> QFrame:
    header = QFrame()
    header.setObjectName("headerFrame")

    # Halo Indicator
    self._halo = HaloIndicator(size=32)

    # タイトル
    title = QLabel("NoaLog")
    title.setObjectName("appTitle")

    # ホットキー表示
    self._hotkey_label = QLabel("Hotkey: ⌘+Shift+L")
    self._hotkey_label.setObjectName("hotkeyLabel")
```

### 左ペイン

```python
def _create_left_pane(self) -> QFrame:
    # プロファイルセレクター
    self._profile_selector = QComboBox()
    self._profile_selector.setObjectName("profileSelector")

    # 統計パネル
    stats = QFrame()
    stats.setObjectName("statsPanel")

    # ボタン
    # - 新規プロファイル
    # - 編集
    # - 領域選択
```

### 中央ペイン

```python
def _create_center_pane(self) -> QFrame:
    # 検索バー
    self._search_input = QLineEdit()
    self._search_input.setObjectName("searchInput")
    self._search_input.setPlaceholderText("🔍 検索...")

    # ログカードリスト
    self._log_list = QListWidget()
    self._log_list.setObjectName("logCardList")
```

### 右ペイン

```python
def _create_right_pane(self) -> QFrame:
    # DetailPanel（タブ付き詳細表示）
    self._detail_panel = DetailPanel()

    # CopyPanel（コピー機能）
    self._copy_panel = CopyPanel()
```

---

## キーボードショートカット

| キー | 動作 |
|------|------|
| ↑/↓ | ログカード選択移動 |
| Enter | 選択カードの編集開始 |
| E | 選択カードの編集開始 |
| ⌘+C | 選択エントリをコピー |
| ⌘+A | 全エントリ選択 |
| Escape | 選択解除 / マルチセレクト終了 |
| ⌘+Z | Undo |
| ⌘+Shift+Z | Redo |

```python
def keyPressEvent(self, event):
    if event.key() == Qt.Key.Key_Up:
        self._select_previous_card()
    elif event.key() == Qt.Key.Key_Down:
        self._select_next_card()
    elif event.key() == Qt.Key.Key_Return:
        self._edit_selected_card()
    # ...
```

---

## テーマ適用

```python
def _apply_theme(self):
    """Noaテーマを適用"""
    theme_path = Path(__file__).parent.parent / "styles" / "noa_theme.qss"
    if theme_path.exists():
        with open(theme_path, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())
```

---

## 使用例（main.pyでの使用）

```python
from ui.views.noa_main_window import NoaMainWindow

# 新UIを使用（デフォルト）
use_classic_ui = os.environ.get("NOALOG_CLASSIC", "0") == "1"
if use_classic_ui:
    from ui.views.main_window import MainWindow
else:
    from ui.views.noa_main_window import NoaMainWindow as MainWindow

window = MainWindow(config)
window.show()
```

---

## シグナル・スロット接続

```python
# プロファイル変更
self._profile_selector.currentIndexChanged.connect(
    self._on_profile_changed
)

# ログカード選択
self._log_list.itemSelectionChanged.connect(
    self._on_card_selection_changed
)

# 検索
self._search_input.textChanged.connect(
    self._filter_log_cards
)

# DetailPanelからの更新
self._detail_panel.entry_updated.connect(
    self._on_entry_updated
)

# CopyPanelからのコピー完了
self._copy_panel.copy_requested.connect(
    lambda fmt: self.set_status(f"Copied as {fmt}")
)
```

---

## ObjectName一覧

| 要素 | ObjectName |
|------|-----------|
| ヘッダー | `headerFrame` |
| タイトル | `appTitle` |
| ホットキーラベル | `hotkeyLabel` |
| 左ペイン | `leftPane` |
| プロファイルセレクター | `profileSelector` |
| 統計パネル | `statsPanel` |
| 中央ペイン | `centerPane` |
| 検索入力 | `searchInput` |
| ログリスト | `logCardList` |
| 右ペイン | `rightPane` |

---

## テスト項目

- [ ] ウィンドウ起動・表示
- [ ] 3ペインのリサイズ
- [ ] プロファイル切り替え
- [ ] ログカード追加・選択
- [ ] 検索フィルタリング
- [ ] マルチセレクト
- [ ] キーボードショートカット
- [ ] テーマ適用確認
- [ ] ステータスバー更新

---

## 関連ファイル

- [[ui-improvement-chief-producer]] - プロジェクト統括
- [[ui-improvement-halo-indicator]] - HaloIndicator
- [[ui-improvement-log-card]] - LogCard
- [[ui-improvement-copy-panel]] - CopyPanel
- [[ui-improvement-detail-panel]] - DetailPanel
- `/src/ui/views/noa_main_window.py` - 実装

---

*Generated by frontend-dev*
