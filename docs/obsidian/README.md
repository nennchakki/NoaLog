# NoaLog 開発ドキュメント

## 概要
NoaLogはクロスプラットフォームOCR会話ログツールです。

## ディレクトリ構造
- `reports/` - 各エージェントの実装レポート
- `daily/` - 日次開発ログ
- `architecture/` - アーキテクチャドキュメント

## レポート一覧
- [[reports/window1-profile-editor]] - プロファイル編集ダイアログ
- [[reports/window2-capture-overlay]] - キャプチャ領域選択オーバーレイ
- [[reports/window3-log-storage]] - ログストレージ（JSONL永続化）
- [[reports/window4-export]] - エクスポート機能
- [[reports/window5-integration]] - 統合・キャプチャフロー

## 技術スタック
- Python 3.13
- PySide6 (Qt)
- PaddleOCR / EasyOCR
- mss (画面キャプチャ)
- pynput (ホットキー)
