"""Real PowerShell execution: wait for old PID, preserve result, restart order."""
def main():
    import json,subprocess,sys,tempfile
    from pathlib import Path
    from update_handoff import helper_script,quote
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        for code,race in ((0,False),(7,False),(0,True)):
            old=subprocess.Popen([sys.executable,'-c',f'import time;time.sleep({30 if race else 1})'])
            state=root/f'result-{code}-{race}.json';marker=root/f'order-{code}-{race}.txt';app=root/'SDM.exe';app.write_bytes(b'fixture')
            # Substitute only the external install/relaunch boundary; execute the
            # wait and exception/result flow in the real Windows shell.
            boundary=('''function Start-Process {
param($FilePath,$ArgumentList,$WindowStyle,[switch]$PassThru,[switch]$Wait)
if (Get-Process -Id OLD_PID -ErrorAction SilentlyContinue) {throw 'Started before old app exited'}
Add-Content -LiteralPath MARKER -Value $FilePath
if ($PassThru) {return [pscustomobject]@{ExitCode=EXIT_CODE}}
}
'''+('''
# Race: the old app exits right after the first check sees it still running.
$sdmSeen = 0
function Get-Process {
param($Id,$ErrorAction)
$found = Microsoft.PowerShell.Management\\Get-Process -Id $Id -ErrorAction SilentlyContinue
if ($found -and $script:sdmSeen++ -eq 0) { Stop-Process -Id $Id -Force; Start-Sleep -Milliseconds 300 }
$found
}
''' if race else '')).replace('OLD_PID',str(old.pid)).replace('MARKER',quote(marker)).replace('EXIT_CODE',str(code))
            script=root/f'helper-{code}-{race}.ps1'
            script.write_text(boundary+helper_script(root/'installer.exe',app,old.pid,state,root/'install.log'),encoding='utf-8-sig')
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)],capture_output=True,text=True,timeout=20)
            old.wait()
            assert result.returncode==0,result.stderr
            data=json.loads(state.read_text(encoding='utf-8-sig'));assert data['ok']==(code==0),data
            lines=marker.read_text().splitlines();assert 'installer.exe' in lines[0] and 'SDM.exe' in lines[1],lines
        print('PowerShell old-process wait (also when it exits right after the check), success/failure state and restart order: OK')

if __name__=='__main__':main()
