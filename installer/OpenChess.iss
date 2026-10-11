#define MyAppName "Open Chess"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "Open Chess"
#define MyAppExeName "OpenChess.exe"

[Setup]
AppId={{6CF8B44E-3172-47A2-B798-37FF8F342C0A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Open Chess
DefaultGroupName=Open Chess
OutputDir=..\dist\installer
OutputBaseFilename=OpenChess-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\OpenChess.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\OpenChess\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Open Chess"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Open Chess"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Open Chess"; Flags: nowait postinstall skipifsilent
