[Setup]
AppName=NoaLog
AppVersion=1.0.0
AppPublisher=nennchakki
DefaultDirName={autopf}\NoaLog
DefaultGroupName=NoaLog
OutputBaseFilename=NoaLogSetup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitModeOnly=x64compatible
WizardStyle=modern
SetupIconFile=..\src\NoaLog.App\Assets\icon.ico

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Files]
; NoaLog本体（self-contained publish）
Source: "publish\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

; Ollama
Source: "ollama\*"; DestDir: "{app}\ollama"; Flags: recursesubdirs ignoreversion

; 辞書データ
Source: "data\dictionaries\*"; DestDir: "{app}\data\dictionaries"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\NoaLog"; Filename: "{app}\NoaLog.exe"
Name: "{commondesktop}\NoaLog"; Filename: "{app}\NoaLog.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加オプション:"

[Run]
; インストール後にモデルをダウンロード
Filename: "{app}\ollama\ollama.exe"; Parameters: "serve"; StatusMsg: "Ollamaサーバーを起動中..."; Flags: runhidden nowait
Filename: "{cmd}"; Parameters: "/c timeout /t 5 /nobreak >nul && ""{app}\ollama\ollama.exe"" pull glm-ocr"; StatusMsg: "OCRモデルをダウンロード中 (glm-ocr 2.2GB)..."; Flags: runhidden waituntilterminated
Filename: "{cmd}"; Parameters: "/c ""{app}\ollama\ollama.exe"" pull gemma4"; StatusMsg: "AIモデルをダウンロード中 (gemma4 9.6GB)..."; Flags: runhidden waituntilterminated
Filename: "{app}\NoaLog.exe"; Description: "NoaLogを起動"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im ollama.exe"; Flags: runhidden
