[Setup]
; Identifiants de l'application
AppName=Écriture
; Récupère la version passée en ligne de commande (avec "1.0.0" comme valeur par défaut de sécurité)
AppVersion={#AppVersion}

AppPublisher=Neomars
AppPublisherURL=https://github.com/neomars/ecriture
AppSupportURL=https://github.com/neomars/ecriture/issues
AppUpdatesURL=https://github.com/neomars/ecriture/releases

; Chemin d'installation par défaut (Program Files/Ecriture)
DefaultDirName={autopf}\Ecriture

; Nom du menu Démarrer
DefaultGroupName=Écriture

; Nom du fichier Setup généré
OutputBaseFilename=Ecriture_Installer
OutputDir=dist

; Compression pour réduire la taille du setup
Compression=lzma2/ultra64
SolidCompression=yes

; Droits d'administrateur nécessaires pour l'installation
PrivilegesRequired=admin

; Icône de l'installeur (optionnel, utilisez la même que votre app)
SetupIconFile=ico-ecriture.ico

; --- AJOUTER TOUTE CETTE PARTIE ---

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Indique à l'installeur de prendre l'exécutable généré par PyInstaller et de le copier dans le dossier d'installation
Source: "dist\ecriture.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Crée le raccourci dans le menu Démarrer
Name: "{group}\Écriture"; Filename: "{app}\ecriture.exe"
; Crée le raccourci sur le Bureau
Name: "{autodesktop}\Écriture"; Filename: "{app}\ecriture.exe"; Tasks: desktopicon

[Run]
; Option pour lancer l'application à la fin de l'installation
Filename: "{app}\ecriture.exe"; Description: "{cm:LaunchProgram,Écriture}"; Flags: nowait postinstall skipifsilent
