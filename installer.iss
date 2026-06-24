; installer.iss — Inno Setup script for COA Converter
; Usage:
;   1. Run PyInstaller first: pyinstaller coa_converter.spec --clean --noconfirm
;      (this must produce dist\COA_Converter\COA_Converter.exe)
;   2. Open this file in Inno Setup Compiler and click "Compile"
;   3. Output installer appears in Output\COA_Converter_Setup.exe

#define MyAppName "COA Converter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "COA Converter"
#define MyAppExeName "COA_Converter.exe"

[Setup]
AppId={{B8F1B0B6-7A4B-4C8E-9B1A-COACONVERTER1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=COA_Converter_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
; If you add a real icon later, point SetupIconFile at assets\app_icon.ico
; SetupIconFile=assets\app_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\COA_Converter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
