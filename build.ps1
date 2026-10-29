param([string]$InnoCompiler = "$PSScriptRoot\build-tools\inno\ISCC.exe")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" tools/check_source.py
if ($LASTEXITCODE -ne 0) { throw 'Source verification failed' }
$sdmVersion = & "$PSScriptRoot\.venv\Scripts\python.exe" -c "from app_version import VERSION; print(VERSION)"
if ($LASTEXITCODE -ne 0 -or $sdmVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid application version' }
& "$PSScriptRoot\.venv\Scripts\python.exe" -m PyInstaller --noconfirm SDM.spec
if ($LASTEXITCODE -ne 0) { throw 'Application build failed' }
& "$PSScriptRoot\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --onedir --console --name SDMHost native_host.py
if ($LASTEXITCODE -ne 0) { throw 'Browser host build failed' }
& "$PSScriptRoot\.venv\Scripts\python.exe" tools/check_source.py
if ($LASTEXITCODE -ne 0) { throw 'Source changed during build' }
& $InnoCompiler "/DSDM_VERSION=$sdmVersion" installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
& "$PSScriptRoot\.venv\Scripts\python.exe" tools/check_package.py
if ($LASTEXITCODE -ne 0) { throw 'Compiled package verification failed' }
