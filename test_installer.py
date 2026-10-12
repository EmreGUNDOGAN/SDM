"""Install/uninstall validation inside the workspace; restores native-host keys."""
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import sqlite3
import struct
import subprocess
import time
import winreg

ROOT = Path(__file__).parent.resolve()
TARGET = ROOT / 'build' / 'installer-test-030'
DATA = ROOT / 'build' / 'installed-test-data-030'
KEYS = ['Software\\Google\\Chrome\\NativeMessagingHosts\\com.sdm.bridge',
        'Software\\Opera Software\\NativeMessagingHosts\\com.sdm.bridge']
NODE = Path('C:/Users/emreg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
backup = {}
for name in KEYS:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,name) as key:
            values=[]
            for index in range(winreg.QueryInfoKey(key)[1]):
                values.append(winreg.EnumValue(key,index))
            backup[name]=values
    except FileNotFoundError:
        backup[name]=None

DATA.mkdir(parents=True,exist_ok=True)
(DATA/'config.json').write_text(json.dumps({'download_dir':str(DATA/'downloads'),
    'clipboard_monitoring':False,'notifications_enabled':False,'auto_open_details':False}),encoding='utf-8')
env=dict(os.environ,SDM_DATA_DIR=str(DATA),
    SDM_BRIDGE_PORT='49382',SDM_INSTANCE_PORT='49381',
    PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'build-tools/playwright'),
    NODE_PATH='C:/Users/emreg/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')
pid=None
installed=False
try:
    # Avoid touching any existing SDM instance.
    with socket.socket() as check:
        check.bind(('127.0.0.1',49381))
    subprocess.run([str(ROOT/'build/SDM-TestSetup.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES',
        '/NORESTART','/NOICONS','/TASKS=operaextension,chromeextension',f'/DIR={TARGET}',
        f'/LOG={ROOT / "build/install-test.log"}'],env=env,check=True)
    installed=True
    manifest=json.loads((TARGET/'browser-host/com.sdm.bridge.json').read_text())
    assert Path(manifest['path']).is_file()
    assert (TARGET/'extension/manifest.json').is_file()
    # Copy only the extension fixture. Its fixed production port validation is
    # redirected to the isolated app's test port; production files stay intact.
    test_extension=ROOT/'build/installed-test-extension'
    shutil.copytree(TARGET/'extension',test_extension,dirs_exist_ok=True)
    background=test_extension/'background.js'
    background.write_text(background.read_text(encoding='utf-8').replace('49282','49382'),encoding='utf-8')
    env['SDM_TEST_EXTENSION_PATH']=str(test_extension)
    body=json.dumps({'action':'connect'}).encode()
    host=subprocess.run([manifest['path'],manifest['allowed_origins'][0]],
        input=struct.pack('<I',len(body))+body,capture_output=True,env=env,check=True,timeout=20)
    count=struct.unpack('<I',host.stdout[:4])[0]
    response=json.loads(host.stdout[4:4+count])
    assert len(response['token'])==64
    pid=response['pid']
    for attempt in range(60):
        try:
            with socket.create_connection(('127.0.0.1',49382),timeout=1):
                break
        except OSError:
            time.sleep(.3)
    subprocess.run([str(NODE),'test_extension_live.cjs'],cwd=ROOT,env=env,check=True,timeout=120)
    for attempt in range(90):
        with sqlite3.connect(DATA/'downloads.db') as db:
            rows=db.execute('SELECT status,filepath FROM downloads ORDER BY id').fetchall()
        if len(rows)==2 and all(row[0]=='Tamamlandı' for row in rows):
            break
        if any(row[0]=='Hata' for row in rows):
            raise RuntimeError('Packaged video download failed')
        time.sleep(1)
    assert len(rows)==2 and all(row[0]=='Tamamlandı' for row in rows), rows
    assert all(Path(row[1]).is_file() and Path(row[1]).stat().st_size>0 for row in rows)
    print('Installed native host, actual Chromium extension, packaged YouTube/MKV/MP3 downloads: OK')
finally:
    if pid:
        try: os.kill(pid,signal.SIGTERM)
        except OSError: pass
        time.sleep(1)
    if installed:
        subprocess.run([str(TARGET/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True)
        assert not (TARGET/'SDM.exe').exists()
    for name,values in backup.items():
        if values is not None:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,name) as key:
                for value,data,kind in values:
                    winreg.SetValueEx(key,value,0,kind,data)
    print('Uninstall completed; previous native-host registry values preserved')
