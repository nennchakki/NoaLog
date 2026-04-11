; NoaLog Installer - Inno Setup Script
; Windows上で Inno Setup Compiler (iscc) を使ってコンパイルする

[Setup]
AppName=NoaLog
AppVersion=0.1.0
AppPublisher=nennchakki
AppPublisherURL=https://github.com/nennchakki/NoaLog
DefaultDirName={autopf}\NoaLog
DefaultGroupName=NoaLog
OutputBaseFilename=NoaLogInstaller
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitModeOnly=x64compatible
WizardStyle=modern
LicenseFile=LICENSE.txt
PrivilegesRequired=admin

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Files]
; NoaLog本体（self-contained publish）
Source: "publish\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

; Ollama
Source: "ollama\*"; DestDir: "{app}\ollama"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\NoaLog"; Filename: "{app}\NoaLog.exe"
Name: "{commondesktop}\NoaLog"; Filename: "{app}\NoaLog.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加オプション:"

[Run]
; インストール後にOllamaサーバーを起動してモデルをダウンロード
Filename: "{app}\ollama\ollama.exe"; Parameters: "serve"; \
    StatusMsg: "Ollamaサーバーを起動中..."; Flags: runhidden nowait
; 5秒待ってからモデルダウンロード
Filename: "{cmd}"; Parameters: "/c timeout /t 5 /nobreak >nul && ""{app}\ollama\ollama.exe"" pull glm-ocr"; \
    StatusMsg: "OCRモデルをダウンロード中 (glm-ocr 2.2GB)... インターネット接続が必要です"; \
    Flags: runhidden waituntilterminated
; NoaLog起動オプション
Filename: "{app}\NoaLog.exe"; Description: "NoaLogを起動"; \
    Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
; アンインストール時にOllamaプロセスを停止
Filename: "{cmd}"; Parameters: "/c taskkill /f /im ollama.exe 2>nul"; Flags: runhidden

[UninstallDelete]
; アンインストール時にアプリデータを削除
Type: filesandordirs; Name: "{userappdata}\NoaLog"
