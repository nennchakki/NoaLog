#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "=== NoaLog Windows Installer Build ==="
echo ""

# 1. Windows向けself-containedビルド
echo "[1/2] Building NoaLog for Windows (win-x64)..."
dotnet publish src/NoaLog.App -c Release -r win-x64 --self-contained true \
    -p:PublishSingleFile=true \
    -p:IncludeNativeLibrariesForSelfExtract=true

# 2. publishディレクトリをinstallerにコピー
echo "[2/2] Copying publish output..."
rm -rf installer/publish
cp -r src/NoaLog.App/bin/Release/net8.0/win-x64/publish/ installer/publish/

echo ""
echo "=== Build complete ==="
echo ""
echo "次のステップ:"
echo "  1. installer/ フォルダをWindowsに転送"
echo "  2. Windows上で Inno Setup をインストール: https://jrsoftware.org/isinfo.php"
echo "  3. コマンドプロンプトで実行: iscc installer\\noalog.iss"
echo "  4. Output/ に NoaLogInstaller.exe が生成されます (~40MB)"
echo ""
echo "※ Ollamaはインストール時にネットからダウンロードされます"
