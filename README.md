# NoaLog

ゲーム（ビジュアルノベル、ブルーアーカイブ等）のプレイ中に表示されるテキストを、
画面キャプチャ＋AI-OCRで自動的にログとして記録するデスクトップアプリ。

## 特徴
- Gemini API によるクラウドOCR（高精度・軽量）
- 3つのモデルから選択可能（設定画面で切り替え）
- Windows / macOS 対応

## システム要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10 (64bit) / macOS 11+ |
| RAM | 4GB以上 |
| ネット | 必須（Gemini API通信用） |

## Gemini API キーの取得と設定

### 1. APIキーの取得
1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセス
2. Googleアカウントでログイン
3. 「APIキーを作成」をクリック
4. 表示されたAPIキーをコピー（`AIza...` で始まる文字列）

### 2. APIキーの設定

#### Windows (PowerShell)
```powershell
# 現在のセッションのみ有効
$env:GEMINI_API_KEY = 'ここにAPIキーを貼り付け'

# 永続化（PC再起動後も有効）
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'ここにAPIキーを貼り付け', 'User')
```

#### macOS / Linux (bash/zsh)
```bash
# ~/.zshrc または ~/.bashrc に追記
echo 'export GEMINI_API_KEY="ここにAPIキーを貼り付け"' >> ~/.zshrc
source ~/.zshrc
```

### 3. 確認
```powershell
# Windows
echo $env:GEMINI_API_KEY
```
```bash
# macOS / Linux
echo $GEMINI_API_KEY
```

設定画面のAPIキー欄に「設定済み」と表示されればOK。

### 選択可能なモデル

| モデル | 特徴 | 料金 (入力/100万トークン) |
|--------|------|--------------------------|
| gemini-3.1-flash-lite | **推奨** 高速・低コスト・高精度 | $0.25 |
| gemini-2.5-flash-lite | 軽量・最安 | $0.10 |
| gemini-2.5-pro | 最高精度（速度は劣る） | $1.25 |

## ダウンロード

**[>>> Windows版をダウンロード <<<](https://github.com/nennchakki/NoaLog/releases)**

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

### いらないエントリの削除
1. 削除したいエントリのチェックボックスをクリック（複数選択可）
2. **Ctrl+A** で全選択もできます
3. **Backspace** または **Delete** キーで選択したエントリを削除

### 注意事項
- **Ctrl+R（範囲指定）だけはNoaLogのオーバーレイが最前面に表示される**。ゲーム開始前にウィンドウモードで範囲指定を済ませ、その後フルスクリーンにするのがおすすめ
- 範囲指定は最初の1回だけでOK（プロファイルに保存される）
- 設定画面のAPIキー欄が「未設定」の場合はOCRが動作しない

### ホットキーの変更
Settings画面からホットキーの割り当てを変更可能。他のアプリと競合する場合に使用。

## ビルド方法
```bash
# Windows (.exe)
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
