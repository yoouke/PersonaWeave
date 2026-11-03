#ifndef AppVersion
#define AppVersion "0.2.1"
#endif
[Setup]
AppId={{C2748A91-A105-4D7A-9F2A-98E49DA1DA6B}
AppName=PersonaWeave
AppVersion={#AppVersion}
AppPublisher=PersonaWeave contributors
DefaultDirName={localappdata}\Programs\PersonaWeave
DefaultGroupName=PersonaWeave
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=PersonaWeave-{#AppVersion}-Windows-x64-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\PersonaWeave.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
CloseApplications=yes
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\dist\PersonaWeave\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\PersonaWeave"; Filename: "{app}\PersonaWeave.exe"
Name: "{autodesktop}\PersonaWeave"; Filename: "{app}\PersonaWeave.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\PersonaWeave.exe"; Description: "Launch PersonaWeave"; Flags: nowait postinstall skipifsilent
; Uninstall intentionally preserves user characters and credentials.
