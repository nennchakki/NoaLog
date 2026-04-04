#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "=== NoaLog Windows Installer Build ==="

# 1. Windows向けself-containedビルド
echo "[1/4] Building NoaLog for Windows (win-x64)..."
dotnet publish src/NoaLog.App -c Release -r win-x64 --self-contained true \
    -p:PublishSingleFile=true \
    -p:IncludeNativeLibrariesForSelfExtract=true

# 2. publishディレクトリをinstallerにコピー
echo "[2/4] Copying publish output..."
rm -rf installer/publish
cp -r src/NoaLog.App/bin/Release/net8.0/win-x64/publish/ installer/publish/

# 3. 辞書データ
echo "[3/4] Copying dictionary data..."
rm -rf installer/data
mkdir -p installer/data
cp -r data/dictionaries installer/data/dictionaries

# 4. Ollamaバイナリの確認
echo "[4/4] Checking Ollama binary..."
if [ ! -f installer/ollama/ollama.exe ]; then
    echo "WARNING: installer/ollama/ollama.exe not found!"
    echo "Download from: https://github.com/ollama/ollama/releases"
    echo "Place ollama.exe in installer/ollama/"
fi

echo ""
echo "=== Build complete ==="
echo "Transfer the installer/ directory to Windows and compile with Inno Setup."
echo "  iscc installer/noalog.iss"
