"""Out-of-process update waiter; never replace a running application's files."""
import json
import os
from pathlib import Path
import subprocess
import sys
from utils import ensure_config_dir

def quote(value):return "'"+str(value).replace("'","''")+"'"
def helper_script(installer,app_path,old_pid,state,log):
    return f'''$ErrorActionPreference = 'Stop'
$sdmResult = @{{ok=$false; message='Güncelleme tamamlanamadı'}}
try {{
  $sdmOld = Get-Process -Id {int(old_pid)} -ErrorAction SilentlyContinue
  if ($sdmOld) {{ Wait-Process -Id {int(old_pid)} -Timeout 90 -ErrorAction Stop }}
  $sdmProcess = Start-Process -FilePath {quote(installer)} -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/SDMNOOPEN=1','/CLOSEAPPLICATIONS',{quote('/LOG="'+str(log)+'"')}) -WindowStyle Hidden -PassThru -Wait
  if ($sdmProcess.ExitCode -notin @(0,3010)) {{throw "Kurulum hata kodu: $($sdmProcess.ExitCode)"}}
  $sdmResult.ok = $true
  $sdmResult.message = 'Güncelleme tamamlandı'
}} catch {{ $sdmResult.message = $_.Exception.Message }}
$sdmResult | ConvertTo-Json | Set-Content -LiteralPath {quote(state)} -Encoding UTF8
if (Test-Path -LiteralPath {quote(app_path)}) {{ Start-Process -FilePath {quote(app_path)} -WindowStyle Hidden }}
'''

def launch_handoff(installer):
    if not getattr(sys,'frozen',False):raise RuntimeError('Otomatik kurulum yalnızca kurulu SDM uygulamasında çalışır.')
    installer=Path(installer).resolve()
    folder=ensure_config_dir()/'updates';folder.mkdir(exist_ok=True)
    if installer.parent!=folder.resolve() or not installer.name.startswith('SDM-Setup-'):raise ValueError('Güncelleme paketi beklenen klasörde değil.')
    if not installer.is_file():raise ValueError('Güncelleme paketi bulunamadı.')
    script=folder/'install-and-restart.ps1'
    script.write_text(helper_script(installer,Path(sys.executable).resolve(),os.getpid(),folder/'result.json',folder/'install.log'),encoding='utf-8-sig')
    return subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)],close_fds=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def read_result():
    path=ensure_config_dir()/'updates/result.json'
    if not path.exists():return None
    try:result=json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError,OSError):return None
    path.unlink(missing_ok=True);return result
