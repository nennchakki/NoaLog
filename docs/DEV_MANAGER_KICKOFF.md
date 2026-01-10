# dev-manager へのキックオフ指示書

## プロジェクト概要

**NoaLog** - クロスプラットフォームOCR会話ログツール

ゲーム/ノベル/配信等の画面からOCRでテキストを抽出し、「名前/組織 + 本文」形式で構造化・保存するデスクトップアプリ。

## 準備済みの成果物

### ディレクトリ構造
```
/Users/dansetsu/NoaLog/
├── src/
│   ├── __init__.py        # バージョン情報
│   ├── main.py            # エントリポイント（スケルトン）
│   ├── config.py          # 設定管理
│   ├── models.py          # データモデル定義
│   ├── core/
│   │   ├── capture/       # 画面キャプチャ（実装待ち）
│   │   ├── ocr/           # OCR処理（実装待ち）
│   │   ├── hotkey/        # ホットキー（実装待ち）
│   │   └── storage/       # データ永続化（実装待ち）
│   ├── ui/
│   │   ├── views/         # メインビュー（実装待ち）
│   │   ├── widgets/       # カスタムウィジェット（実装待ち）
│   │   └── styles/        # スタイル定義（実装待ち）
│   └── utils/             # ユーティリティ（実装待ち）
├── tests/                 # テストコード
├── docs/                  # ドキュメント
├── profiles/              # ユーザープロファイル保存先
├── logs/                  # 会話ログ保存先
└── reports/               # プロジェクトレポート
```

### 設定ファイル
- `pyproject.toml` - 依存関係、ビルド設定
- `.gitignore` - Git除外設定

### データモデル（src/models.py）
- `Rect` - キャプチャ領域
- `Hotkey` - ホットキー定義
- `Profile` - プロファイル（領域設定、ホットキー）
- `LogEntry` - ログエントリ（raw/edited分離済み）
- `CopyFormat` - コピー形式

### 設定管理（src/config.py）
- `Config` - アプリ設定、パス管理
- OCR前処理設定
- テキスト正規化設定
- ヘッダーパース設定

---

## MVP実装タスク

### 優先度1: 環境構築
```bash
cd /Users/dansetsu/NoaLog
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### 優先度2: Captureモジュール
**ファイル**: `src/core/capture/screen_capture.py`

**要件**:
- mssを使用した画面キャプチャ
- 指定Rect領域の切り出し
- macOS Screen Recording権限チェック
- 画像をnumpy array（OpenCV形式）で返却

**インターフェース案**:
```python
class ScreenCapture:
    def capture_region(self, rect: Rect) -> np.ndarray:
        """指定領域をキャプチャ"""
        pass

    def capture_full_screen(self, monitor: int = 0) -> np.ndarray:
        """全画面キャプチャ"""
        pass

    @staticmethod
    def check_permission() -> bool:
        """権限チェック（macOS）"""
        pass
```

### 優先度3: Hotkeyモジュール
**ファイル**: `src/core/hotkey/hotkey_manager.py`

**要件**:
- pynputを使用したグローバルホットキー
- 2キー以上の同時押し検出
- デバウンス処理（全キー離すまで次を許可しない）
- macOS Accessibility権限チェック

**インターフェース案**:
```python
class HotkeyManager:
    def register(self, hotkey: Hotkey, callback: Callable) -> None:
        """ホットキー登録"""
        pass

    def unregister(self, hotkey: Hotkey) -> None:
        """ホットキー解除"""
        pass

    def start(self) -> None:
        """監視開始"""
        pass

    def stop(self) -> None:
        """監視停止"""
        pass

    @staticmethod
    def check_permission() -> bool:
        """権限チェック（macOS）"""
        pass
```

### 優先度4: OCRモジュール
**ファイル**: `src/core/ocr/ocr_processor.py`

**要件**:
- PaddleOCR初期化（日本語モデル）
- 画像前処理（OpenCV）
  - グレースケール
  - ノイズ除去
  - コントラスト調整
- OCR実行
- テキスト正規化

**インターフェース案**:
```python
class OCRProcessor:
    def __init__(self, config: dict):
        """PaddleOCR初期化"""
        pass

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """前処理"""
        pass

    def recognize(self, image: np.ndarray) -> str:
        """OCR実行"""
        pass

    def process(self, image: np.ndarray) -> str:
        """前処理 + OCR + 正規化"""
        pass
```

### 優先度5: Storageモジュール
**ファイル**: `src/core/storage/log_storage.py`

**要件**:
- JSONL形式でのログ保存（追記）
- ログ読み込み
- プロファイル保存/読み込み（JSON）

**インターフェース案**:
```python
class LogStorage:
    def __init__(self, logs_dir: Path):
        pass

    def append(self, entry: LogEntry) -> None:
        """ログ追記"""
        pass

    def load_all(self, profile_id: str) -> List[LogEntry]:
        """全ログ読み込み"""
        pass

    def update(self, entry: LogEntry) -> None:
        """ログ更新（編集用）"""
        pass


class ProfileStorage:
    def __init__(self, profiles_dir: Path):
        pass

    def save(self, profile: Profile) -> None:
        """プロファイル保存"""
        pass

    def load(self, profile_id: str) -> Profile:
        """プロファイル読み込み"""
        pass

    def list_all(self) -> List[Profile]:
        """全プロファイル一覧"""
        pass
```

### 優先度6: テキスト処理
**ファイル**: `src/utils/text_processor.py`

**要件**:
- テキスト正規化（全角/半角統一）
- ヘッダーパース（name/org分割）
- 地の文判定

---

## 参考ドキュメント

- `/Users/dansetsu/NoaLog/docs/ROADMAP.md` - 詳細スケジュール
- `/Users/dansetsu/NoaLog/docs/TASK_ASSIGNMENT.md` - 作業分担
- `/Users/dansetsu/NoaLog/reports/collaborative/project-noalog-plan.md` - プロジェクト計画

---

## 連携ポイント

### OCR実装完了後
tech-advisor-chiefにOCR精度検証を依頼:
- テスト画像と期待結果を準備
- 前処理パラメータの最適化提案を受ける

### Beta完了後
tech-advisor-chiefにパフォーマンスレビューを依頼:
- 応答性計測結果を準備
- メモリプロファイリングを実施

---

## 報告

作業進捗は以下に記録:
`/Users/dansetsu/NoaLog/reports/dev-manager-report.md`

---

作成日: 2026-01-04
発行元: chief-producer
