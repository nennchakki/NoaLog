@echo off
setlocal

set OLLAMA_DIR=%~1\ollama
set OLLAMA_URL=https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip
set ZIP_FILE=%TEMP%\ollama-windows-amd64.zip

echo Ollamaをダウンロード中...
mkdir "%OLLAMA_DIR%" 2>nul

:: curlでDL（Windows 10以降は標準搭載）
curl -L -o "%ZIP_FILE%" "%OLLAMA_URL%"
if errorlevel 1 (
    echo ダウンロードに失敗しました。インターネット接続を確認してください。
    exit /b 1
)

echo 展開中...
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%OLLAMA_DIR%' -Force"
del "%ZIP_FILE%"

echo Ollamaサーバーを起動中...
start /b "" "%OLLAMA_DIR%\ollama.exe" serve

echo OCRモデルをダウンロード中 (glm-ocr, 約2.2GB)...
timeout /t 5 /nobreak >nul
"%OLLAMA_DIR%\ollama.exe" pull glm-ocr

echo セットアップ完了
