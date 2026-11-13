#ifndef AppSource
  #error AppSource deve apontar para a pasta gerada pelo PyInstaller.
#endif
#ifndef InstallerOutput
  #error InstallerOutput deve apontar para a pasta de destino do instalador.
#endif

[Setup]
AppId={{7AC96695-8768-4CF1-90B2-55E47D53090B}
AppName=AutoClicker Pro
AppVersion=1.0
DefaultDirName={localappdata}\Programs\AutoClicker Pro
DefaultGroupName=AutoClicker Pro
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#InstallerOutput}
OutputBaseFilename=AutoClickerPro-Instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AutoClickerPro.exe
CloseApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AutoClicker Pro"; Filename: "{app}\AutoClickerPro.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\AutoClicker Pro"; Filename: "{app}\AutoClickerPro.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AutoClickerPro.exe"; Description: "Abrir AutoClicker Pro"; Flags: nowait postinstall skipifsilent
