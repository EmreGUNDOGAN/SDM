"""Real PowerShell execution: wait for old PID, preserve result, restart order."""
def main():
    import json,subprocess,sys,tempfile
    from pathlib import Path
    from update_handoff import helper_script,quote
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        for code in (0,7):
            old=subprocess.Popen([sys.executable,'-c','import time;time.sleep(1)'])
            state=root/f'result-{code}.json';marker=root/f'order-{code}.txt';app=root/'SDM.exe';app.write_bytes(b'fixture')
            # Substitute only the external install/relaunch boundary; execute the
            # wait and exception/result flow in the real Windows shell.
            boundary='''function Start-Process {
param($FilePath,$ArgumentList,$WindowStyle,[switch]$PassThru,[switch]$Wait)
if (Get-Process -Id OLD_PID -ErrorAction SilentlyContinue) {throw 'Started before old app exited'}
Add-Content -LiteralPath MARKER -Value $FilePath
if ($PassThru) {return [pscustomobject]@{ExitCode=EXIT_CODE}}
}
'''.replace('OLD_PID',str(old.pid)).replace('MARKER',quote(marker)).replace('EXIT_CODE',str(code))
            script=root/f'helper-{code}.ps1'
            script.write_text(boundary+helper_script(root/'installer.exe',app,old.pid,state,root/'install.log'),encoding='utf-8-sig')
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)],capture_output=True,text=True,timeout=20)
            old.wait()
            assert result.returncode==0,result.stderr
            data=json.loads(state.read_text(encoding='utf-8-sig'));assert data['ok']==(code==0),data
            lines=marker.read_text().splitlines();assert 'installer.exe' in lines[0] and 'SDM.exe' in lines[1],lines
        print('PowerShell old-process wait, success/failure state and restart order: OK')

if __name__=='__main__':main()
