# CaptureOverlay 実装レポート

**作成日時**: 2026-01-04
**担当**: frontend-dev
**ステータス**: 完了

---

## 概要

CaptureOverlayは、画面上でキャプチャ領域を選択するためのフルスクリーンオーバーレイウィジェットです。マウスドラッグによる矩形領域の選択、ヘッダー/ボディ領域の切り替え、リアルタイムプレビューなどの機能を提供します。

## 実装した機能

### 主要機能

| 機能 | 説明 |
|------|------|
| フルスクリーンオーバーレイ | 全画面を覆う半透明オーバーレイ |
| マウスドラッグ選択 | クリック&ドラッグで矩形領域を選択 |
| リアルタイムプレビュー | 破線枠で選択領域をリアルタイム表示 |
| 領域タイプ切り替え | Tab キーでヘッダー/ボディを切り替え |
| ESC キャンセル | ESC キーで選択をキャンセル |
| シグナル通知 | 選択完了/キャンセル時にシグナル発行 |
| マルチモニター対応 | 複数モニター環境での動作 |

### キーバインド

| キー | 動作 |
|------|------|
| ESC | 選択をキャンセルしてオーバーレイを閉じる |
| Tab | ヘッダー/ボディの領域タイプを切り替え |
| マウス左ドラッグ | 領域を選択 |

---

## ファイル構成

```
/Users/dansetsu/NoaLog/src/ui/widgets/
├── __init__.py           # エクスポート定義を追加
└── capture_overlay.py    # メイン実装ファイル
```

---

## クラス構成

### RegionType (Enum)

領域タイプを定義する列挙型。

```python
class RegionType(Enum):
    HEADER = "header"
    BODY = "body"
```

### CaptureOverlay (QWidget)

メインのオーバーレイウィジェットクラス。

#### コンストラクタ

```python
def __init__(
    self,
    region_type: RegionType = RegionType.BODY,
    parent: Optional[QWidget] = None
)
```

#### シグナル

| シグナル | パラメータ | 説明 |
|----------|------------|------|
| `region_selected` | `(int, int, int, int, str)` | 選択完了時に発行 (x, y, width, height, region_type) |
| `selection_cancelled` | なし | キャンセル時に発行 |

#### プロパティ

| プロパティ | 型 | 説明 |
|------------|-----|------|
| `region_type` | `RegionType` | 現在の領域タイプ（get/set可） |

#### 主要メソッド

| メソッド | 説明 |
|----------|------|
| `show()` | オーバーレイを表示（全画面ジオメトリを自動設定） |
| `start_selection(region_type)` | 選択プロセスを開始 |
| `get_selection_rect()` | 現在の選択矩形を取得 |

### CaptureOverlayManager

オーバーレイのライフサイクルを管理するヘルパークラス。

```python
manager = CaptureOverlayManager()
manager.start_capture(
    RegionType.HEADER,
    on_selected=lambda x, y, w, h, t: print(f"Selected: {x}, {y}"),
    on_cancelled=lambda: print("Cancelled")
)
```

#### メソッド

| メソッド | 説明 |
|----------|------|
| `start_capture(region_type, on_selected, on_cancelled)` | キャプチャ開始 |
| `cancel()` | 現在のキャプチャをキャンセル |

### select_capture_region 関数

ブロッキング形式でリージョン選択を行う便利関数。

```python
result = select_capture_region(RegionType.BODY)
if result:
    x, y, width, height, region_type = result
```

---

## 使用例

### 基本的な使用

```python
from PySide6.QtWidgets import QApplication
from src.ui.widgets import CaptureOverlay, RegionType

app = QApplication([])

def on_region_selected(x, y, width, height, region_type):
    print(f"Selected {region_type}: ({x}, {y}) {width}x{height}")
    # Rect オブジェクトに変換
    from src.models import Rect
    rect = Rect(x=x, y=y, width=width, height=height)
    app.quit()

def on_cancelled():
    print("Selection cancelled")
    app.quit()

overlay = CaptureOverlay(RegionType.HEADER)
overlay.region_selected.connect(on_region_selected)
overlay.selection_cancelled.connect(on_cancelled)
overlay.show()

app.exec()
```

### マネージャーを使用した方法

```python
from src.ui.widgets import CaptureOverlayManager, RegionType

manager = CaptureOverlayManager()

def handle_selection(x, y, width, height, region_type):
    print(f"Captured: {x}, {y}, {width}x{height} ({region_type})")

manager.start_capture(
    RegionType.BODY,
    on_selected=handle_selection,
    on_cancelled=lambda: print("Cancelled")
)
```

### Rectモデルとの連携

```python
from src.models import Rect
from src.ui.widgets import CaptureOverlay, RegionType

overlay = CaptureOverlay(RegionType.HEADER)

def on_selected(x, y, width, height, region_type):
    rect = Rect(x=x, y=y, width=width, height=height)
    # プロファイルに保存
    if region_type == "header":
        profile.header_rect = rect
    else:
        profile.body_rect = rect

overlay.region_selected.connect(on_selected)
overlay.show()
```

---

## テーマとの統合

実装はNoaLogテーマ（theme.qss）のカラーパレットに準拠しています。

| 要素 | 色 | カラーコード |
|------|-----|-------------|
| オーバーレイ背景 | Navy 30% | `rgba(26, 39, 68, 0.3)` |
| 選択枠（破線） | Accent Blue | `#5eb3f0` |
| 選択領域塗りつぶし | Accent Blue 20% | `rgba(94, 179, 240, 0.2)` |
| テキスト | White | `#ffffff` |
| テキスト背景 | Navy 80% | `rgba(26, 39, 68, 0.8)` |

---

## クロスプラットフォーム考慮事項

### macOS

```python
if sys.platform == "darwin":
    flags |= Qt.WindowType.NoDropShadowWindowHint
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
```

- `NoDropShadowWindowHint`: ウィンドウ影を無効化
- `WA_TranslucentBackground`: 透過背景を有効化
- Retina ディスプレイでの高DPI対応

### Windows

```python
elif sys.platform == "win32":
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
```

- レイヤードウィンドウとして正しく描画
- DPI スケーリングはQtが自動処理

### Linux

```python
else:
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
```

- コンポジターに依存した透過処理
- X11/Wayland両対応

### マルチモニター対応

```python
def _set_fullscreen_geometry(self) -> None:
    screens = app.screens()
    combined_rect = QRect()
    for screen in screens:
        screen_geo = screen.geometry()
        combined_rect = combined_rect.united(screen_geo)
    self.setGeometry(combined_rect)
```

全モニターの合計領域を計算し、オーバーレイをその範囲に展開。

---

## 技術的な詳細

### ウィンドウフラグ

```python
flags = (
    Qt.WindowType.FramelessWindowHint |     # フレームなし
    Qt.WindowType.WindowStaysOnTopHint |    # 最前面表示
    Qt.WindowType.Tool                       # ツールウィンドウ
)
```

### 描画パイプライン

1. `paintEvent` で QPainter を使用
2. 半透明オーバーレイを全面に描画
3. 選択領域がある場合、その部分をクリア＆再描画
4. 破線枠とコーナーハンドルを描画
5. 寸法ラベルと操作説明を描画

### 最小選択サイズ

```python
MIN_SELECTION_SIZE = 10  # ピクセル
```

10px未満の選択は無効として破棄。

---

## test-engineer への引き継ぎ情報

### テスト対象

| 項目 | テスト内容 |
|------|------------|
| 選択機能 | マウスドラッグで矩形選択できること |
| シグナル発行 | 選択完了時にregion_selectedが発行されること |
| キャンセル | ESCキーでselection_cancelledが発行されること |
| 領域切り替え | Tabキーでヘッダー/ボディが切り替わること |
| 最小サイズ | 10px未満の選択が無効になること |
| 座標正規化 | 逆方向ドラッグでも正しい座標が返ること |

### E2Eシナリオ

1. オーバーレイを表示 -> ドラッグで選択 -> シグナル確認
2. オーバーレイを表示 -> ESCで閉じる -> キャンセルシグナル確認
3. Tab連打で領域タイプが交互に切り替わること
4. マルチモニター環境で全画面をカバーすること

---

## 関連ファイル

- `/Users/dansetsu/NoaLog/src/models.py` - Rect クラス定義
- `/Users/dansetsu/NoaLog/src/ui/styles/theme.qss` - テーマ定義
- `/Users/dansetsu/NoaLog/src/ui/widgets/__init__.py` - エクスポート定義

---

## 更新履歴

| 日付 | 内容 |
|------|------|
| 2026-01-04 | 初回実装完了 |
