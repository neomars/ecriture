[Setup]
; Identifiants de l'application
AppName=Écriture
; Récupère la version passée en ligne de commande (avec "1.0.0" comme valeur par défaut de sécurité)
AppVersion={#AppVersion}

AppPublisher=Neomars
AppPublisherURL=https://github.com/neomars/ecriture
AppSupportURL=https://github.com/neomars/ecriture/issues
AppUpdatesURL=https://github.com/neomars/ecriture/releases

; Le reste du fichier reste identique
DefaultDirName={autopf}\Ecriture
DefaultGroupName=Écriture
OutputBaseFilename=Ecriture_Installer
OutputDir=dist
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
SetupIconFile=ico-ecriture.ico
