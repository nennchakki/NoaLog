# NoaLog

ゲーム（ビジュアルノベル、ブルーアーカイブ等）のプレイ中に表示されるテキストを、
画面キャプチャ＋AI-OCRで自動的にログとして記録するデスクトップアプリ。

## 特徴
- 完全ローカル動作（外部サーバーへの通信なし）
- OCRエンジン: Ollama経由のVLM（デフォルト: glm-ocr 0.9B）
- Windows / macOS 対応

## インストール（Windows）
1. [Releases](https://github.com/nennchakki/NoaLog/releases) から `NoaLogInstaller.exe` をダウンロード
2. インストーラーを実行（NoaLog本体 + Ollama + OCRモデルが自動セットアップ）
3. デスクトップの NoaLog アイコンから起動

## 使い方

### 初回セットアップ（範囲指定）
1. NoaLog を起動する
2. ゲームをウィンドウモードで起動する（または範囲指定前にフルスクリーンを解除）
3. **Ctrl+R** でキャプチャ範囲の指定画面が開く
4. テキストが表示される領域をドラッグで囲む（余裕を持って大きめに）
5. 続けてナレーション（語り部）領域も指定する（不要ならEscでスキップ）
6. 範囲はプロファイルに保存される（次回起動時も有効）

### ゲームプレイ中
- **Ctrl+L**: テキストをキャプチャ＆OCR実行（メイン機能）
- **Ctrl+N**: ナレーションテキストのキャプチャ
- これらのショートカットは**ゲームがフルスクリーンでも、NoaLogが裏にあっても動作する**（グローバルホットキー）

### ログの操作
- **Ctrl+F**: 検索（置換も可能）
- **Ctrl+A**: 全選択
- **Backspace / Delete**: 選択したログを削除
- チェックボックスで複数選択 → エクスポート（txt / md / json）

### 注意事項
- **Ctrl+R（範囲指定）だけはNoaLogのオーバーレイが最前面に表示される**。ゲーム開始前にウィンドウモードで範囲指定を済ませ、その後フルスクリーンにするのがおすすめ
- 範囲指定は最初の1回だけでOK（プロファイルに保存される）
- ENGINE パネルに「Ready」と表示されるまではOCRが使えない（初回はモデルダウンロードに時間がかかる）
- 初回起動時はOCRモデルのGPUロードに30秒〜1分かかる。2回目以降はキャッシュされるため数秒で起動する
- GPU（NVIDIA/AMD）がある場合、Ollamaが自動でGPU推論を使う。CPUのみでも動作するが遅い

### ホットキーの変更
Settings画面からホットキーの割り当てを変更可能。他のアプリと競合する場合に使用。

## ビルド方法
```bash
# Windows
dotnet publish src/NoaLog.App -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true

# macOS (Apple Silicon)
dotnet publish src/NoaLog.App -c Release -r osx-arm64 --self-contained true -p:PublishSingleFile=true
```

## 二次創作ガイドラインについて

本ソフトウェアは、株式会社Yostarが定める[「ブルーアーカイブ」二次創作ガイドライン](https://bluearchive.jp/fankit/guidelines)に基づき、個人による非営利目的のツールとして作成されています。

ゲームのデータファイルへのアクセスや、ゲーム素材の抽出・再配布は行いません。

「ブルーアーカイブ」は株式会社Yostarの登録商標です。本ソフトウェアは株式会社Yostarとは一切関係ありません。

## ライセンス
See [LICENSE](LICENSE)
