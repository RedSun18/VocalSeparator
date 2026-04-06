[Setup]
AppName=VocalSeparator
AppVersion=1.0.0
AppPublisher=VocalSeparator
DefaultDirName={localappdata}\Programs\VocalSeparator
DefaultGroupName=VocalSeparator
OutputDir=dist
OutputBaseFilename=VocalSeparator_Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\VocalSeparator.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Files]
Source: "dist\VocalSeparator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VocalSeparator"; Filename: "{app}\VocalSeparator.exe"
Name: "{userdesktop}\VocalSeparator"; Filename: "{app}\VocalSeparator.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\VocalSeparator.exe"; Description: "Launch VocalSeparator"; Flags: nowait postinstall skipifsilent