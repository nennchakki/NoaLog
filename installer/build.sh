#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "=== NoaLog Windows Installer Build ==="
echo ""

# 1. Windows向けself-containedビルド
echo "[1/3] Building NoaLog for Windows (win-x64)..."
dotnet publish src/NoaLog.App -c Release -r win-x64 --self-contained true \
    -p:PublishSingleFile=true \
    -p:IncludeNativeLibrariesForSelfExtract=true

# 2. publishディレクトリをinstallerにコピー
echo "[2/3] Copying publish output..."
rm -rf installer/publish
cp -r src/NoaLog.App/bin/Release/net8.0/win-x64/publish/ installer/publish/

# 3. Ollamaバイナリの確認
echo "[3/3] Checking Ollama binary..."
if [ ! -f installer/ollama/ollama.exe ]; then
    echo ""
    echo "========================================="
    echo "  WARNING: installer/ollama/ollama.exe が見つかりません"
    echo ""
    echo "  以下からダウンロードしてください:"
    echo "  https://github.com/ollama/ollama/releases"
    echo ""
    echo "  ollama.exe を installer/ollama/ に配置してください"
    echo "========================================="
    echo ""
fi

echo ""
echo "=== Build complete ==="
echo ""
echo "次のステップ:"
echo "  1. installer/ollama/ に ollama.exe を配置"
echo "  2. installer/ フォルダをWindowsに転送"
echo "  3. Windows上で Inno Setup をインストール: https://jrsoftware.org/isinfo.php"
echo "  4. コマンドプロンプトで実行: iscc installer\\noalog.iss"
echo "  5. Output/ に NoaLogInstaller.exe が生成されます"
