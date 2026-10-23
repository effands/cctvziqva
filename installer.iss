[Setup]
AppId={{4BBA7E1D-2D93-4CE7-85B8-D9A203949CA2}
AppName=CCTV ZIQVA
AppVersion=1.0.23
AppPublisher=ZIQVA
DefaultDirName={localappdata}\Programs\CCTV ZIQVA
DefaultGroupName=CCTV ZIQVA
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=dist
OutputBaseFilename=CCTV_ZIQVA_Setup_1.0.23
SetupIconFile=cctv_icon.ico
UninstallDisplayIcon={app}\CCTV ZIQVA.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Tasks]
Name: desktopicon; Description: "Buat shortcut di Desktop"; Flags: checkedonce

[Files]
Source: "dist\CCTV ZIQVA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "build\installer-assets\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "INSTALL_EXE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CCTV ZIQVA"; Filename: "{app}\CCTV ZIQVA.exe"
Name: "{userdesktop}\CCTV ZIQVA"; Filename: "{app}\CCTV ZIQVA.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CCTV ZIQVA.exe"; Description: "Buka CCTV ZIQVA"; Flags: nowait postinstall skipifsilent
