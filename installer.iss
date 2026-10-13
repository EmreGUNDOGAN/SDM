[Setup]
#ifdef SDM_TEST_BUILD
AppId={{DA66AE91-880E-4ED8-977D-9AC2298A341B}
#else
AppId={{7D41A428-758B-4932-A29D-03767B5E5587}
#endif
AppName=SDM
AppVersion=0.4.3
DefaultDirName={localappdata}\Programs\SDM
DefaultGroupName=SDM
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
OutputDir=dist
OutputBaseFilename=SDM-Setup-0.4.3
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\SDM.exe
SetupIconFile=assets\sdm.ico

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; Flags: unchecked
Name: "operaextension"; Description: "Opera eklentisini hazırla ve yükleme sayfasını aç"; Flags: unchecked
Name: "chromeextension"; Description: "Chrome eklentisini hazırla ve yükleme sayfasını aç"; Flags: unchecked

[Files]
Source: "dist\SDM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "UPSTREAM-NOTICES.md"; DestDir: "{app}\notices"; Flags: ignoreversion
Source: "README*.md"; DestDir: "{app}\notices"; Flags: ignoreversion
Source: "dist\SDMHost\*"; DestDir: "{app}\browser-host"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "extension-setup.html"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.sdm.bridge"; ValueType: string; ValueName: ""; ValueData: "{app}\browser-host\com.sdm.bridge.json"; Flags: uninsdeletekey; Tasks: chromeextension
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.sdm.bridge"; ValueType: string; ValueName: ""; ValueData: "{app}\browser-host\com.sdm.bridge.json"; Flags: uninsdeletekey; Tasks: operaextension
Root: HKCU; Subkey: "Software\Opera Software\NativeMessagingHosts\com.sdm.bridge"; ValueType: string; ValueName: ""; ValueData: "{app}\browser-host\com.sdm.bridge.json"; Flags: uninsdeletekey; Tasks: operaextension

[Icons]
Name: "{group}\SDM"; Filename: "{app}\SDM.exe"
Name: "{autodesktop}\SDM"; Filename: "{app}\SDM.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\extension-setup.html"; Flags: shellexec postinstall skipifsilent; Tasks: operaextension chromeextension; Description: "Eklenti kurulum adımlarını göster"
Filename: "{win}\explorer.exe"; Parameters: """{app}\extension"""; Flags: nowait skipifsilent; Tasks: operaextension chromeextension
Filename: "{code:GetOperaPath}"; Parameters: "opera://extensions"; Flags: nowait skipifsilent; Tasks: operaextension; Check: OperaAvailable
Filename: "{code:GetChromePath}"; Parameters: "chrome://extensions"; Flags: nowait skipifsilent; Tasks: chromeextension; Check: ChromeAvailable
Filename: "{app}\SDM.exe"; Description: "SDM'yi aç"; Flags: nowait postinstall skipifsilent
Filename: "{app}\SDM.exe"; Flags: nowait; Check: SilentReopen

[Code]
function SilentReopen: Boolean;
begin
  #ifdef SDM_TEST_BUILD
  Result := False;
  #else
  Result := WizardSilent and (ExpandConstant('{param:SDMNOOPEN|0}') <> '1');
  #endif
end;

function GetOperaPath(Param: String): String;
begin
  Result := ExpandConstant('{localappdata}\Programs\Opera\launcher.exe');
  if not FileExists(Result) then Result := ExpandConstant('{autopf}\Opera\launcher.exe');
  if not FileExists(Result) then Result := ExpandConstant('{localappdata}\Programs\Opera GX\launcher.exe');
end;

function OperaAvailable: Boolean;
begin
  Result := FileExists(GetOperaPath(''));
end;

function GetChromePath(Param: String): String;
begin
  Result := ExpandConstant('{autopf}\Google\Chrome\Application\chrome.exe');
  if not FileExists(Result) then Result := ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe');
end;

function ChromeAvailable: Boolean;
begin
  Result := FileExists(GetChromePath(''));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  HostPath, JsonText: String;
begin
  if CurStep = ssPostInstall then begin
    HostPath := ExpandConstant('{app}\browser-host\SDMHost.exe');
    StringChangeEx(HostPath, '\', '\\', True);
    JsonText := '{"name":"com.sdm.bridge","description":"SDM browser bridge","path":"' + HostPath + '","type":"stdio","allowed_origins":["chrome-extension://eipmgfnkhpeaefhjpbgkccckcacafjkj/"]}';
    SaveStringToFile(ExpandConstant('{app}\browser-host\com.sdm.bridge.json'), JsonText, False);
  end;
end;
