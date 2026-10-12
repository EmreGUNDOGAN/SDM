param([string]$InnoCompiler = "$PSScriptRoot\build-tools\inno\ISCC.exe")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" -m PyInstaller --noconfirm SDM.spec
if ($LASTEXITCODE -ne 0) { throw 'Application build failed' }
& "$PSScriptRoot\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --onedir --console --name SDMHost native_host.py
if ($LASTEXITCODE -ne 0) { throw 'Browser host build failed' }
& $InnoCompiler installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
