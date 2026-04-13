; NoaLog Installer - Inno Setup Script

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
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
LicenseFile=LICENSE.txt
InfoAfterFile=USAGE.txt
PrivilegesRequired=admin
; Ollama (3.4GB) + glm-ocr model (2.2GB) = 約6GB追加
ExtraDiskSpaceRequired=6442450944

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Files]
; NoaLog本体（self-contained publish）
Source: "publish\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
; アイコンファイル
Source: "..\src\NoaLog.App\Assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\NoaLog"; Filename: "{app}\NoaLog.exe"; IconFilename: "{app}\icon.ico"
Name: "{commondesktop}\NoaLog"; Filename: "{app}\NoaLog.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加オプション:"

[Run]
; NoaLog起動オプション
Filename: "{app}\NoaLog.exe"; Description: "NoaLogを起動"; \
    Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im ollama.exe 2>nul"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\NoaLog"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := MsgBox(
    'NoaLog のインストールには以下の条件が必要です:' + #13#10 +
    '' + #13#10 +
    '・ディスク空き容量: 6GB以上' + #13#10 +
    '・メモリ (RAM): 4GB以上' + #13#10 +
    '・インターネット接続（初回約4GBのダウンロード）' + #13#10 +
    '・GPU推奨: NVIDIA GTX 1650以上（なくても動作可）' + #13#10 +
    '' + #13#10 +
    'インストールを続行しますか？',
    mbConfirmation, MB_YESNO) = IDYES;
end;

procedure DownloadAndSetupOllama();
var
  ResultCode: Integer;
  ZipPath, OllamaDir: String;
begin
  OllamaDir := ExpandConstant('{app}\ollama');
  ZipPath := ExpandConstant('{tmp}\ollama-windows-amd64.zip');

  WizardForm.StatusLabel.Caption := 'Ollamaをダウンロード中...';
  Exec('curl.exe', '-L -o "' + ZipPath + '" https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  WizardForm.StatusLabel.Caption := 'Ollamaを展開中...';
  Exec('powershell.exe', '-Command "Expand-Archive -Path ''' + ZipPath + ''' -DestinationPath ''' + OllamaDir + ''' -Force"',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  DeleteFile(ZipPath);

  WizardForm.StatusLabel.Caption := 'Ollamaサーバーを起動中...';
  Exec(OllamaDir + '\ollama.exe', 'serve', '', SW_HIDE, ewNoWait, ResultCode);

  WizardForm.StatusLabel.Caption := 'OCRモデルをダウンロード中 (glm-ocr, 約2.2GB)...';
  Sleep(5000);
  Exec(OllamaDir + '\ollama.exe', 'pull glm-ocr', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    DownloadAndSetupOllama();
end;
