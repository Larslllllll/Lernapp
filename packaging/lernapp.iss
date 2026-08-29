; Inno-Setup-Beschreibung fuer LernApp (Windows)
;
; Bauen:  .venv/Scripts/python.exe packaging/build_windows.py --installer
; Die Version wird vom Build-Skript aus lernapp/__init__.py uebergeben.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef QuellVerzeichnis
  #define QuellVerzeichnis "..\dist\LernApp"
#endif

#define AppName        "LernApp"
#define AppPublisher   "LernApp"
#define AppExeName     "LernApp.exe"
#define AppUserModelID "ch.lernapp.desktop"

[Setup]
; Diese GUID identifiziert das Produkt ueber alle Versionen hinweg und darf
; nie geaendert werden - sonst erkennt der Installer kein Upgrade mehr,
; sondern legt eine zweite Installation an.
AppId={{7C4C1A62-8E3F-4C51-9C2B-0A5D3E7F1B94}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=LernApp-Setup-{#AppVersion}
SetupIconFile=..\ico.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 64-Bit-Installation; das Bundle enthaelt 64-Bit-Qt.
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
; Ohne Administratorrechte nach %LOCALAPPDATA% installieren. Wichtig fuer
; Schulrechner, auf denen Schueler keine Adminrechte haben.
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=lowest

[Languages]
Name: "deutsch"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop anlegen"; \
    GroupDescription: "Zusätzliche Verknüpfungen:"; Flags: unchecked

[Files]
; Das gesamte PyInstaller-Bundle.
Source: "{#QuellVerzeichnis}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    AppUserModelID: "{#AppUserModelID}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "LernApp jetzt starten"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nur programmeigene Reste entfernen. Die Nutzerdaten liegen in
; %USERPROFILE%\.lernapp und werden bewusst NICHT angefasst - eine
; Deinstallation darf niemals gelernten Fortschritt vernichten.
Type: filesandordirs; Name: "{app}\_internal"

[Code]
// Vor dem Upgrade sicherstellen, dass die App nicht mehr laeuft - sonst
// lassen sich die Qt-DLLs nicht ersetzen.
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
