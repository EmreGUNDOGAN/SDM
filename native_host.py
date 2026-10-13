"""Browser native messaging host: launch SDM and return local pairing token."""
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import hashlib

def extension_status():
    folder=Path(sys.executable).parent.parent/'extension'
    if not folder.is_dir():return {'error':'SDM kurulum klasöründeki eklenti bulunamadı.'}
    files={path.relative_to(folder).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in folder.rglob('*') if path.is_file() and not path.is_symlink()}
    version=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))['version']
    return {'version':version,'files':files}


def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'chrome-extension://eipmgfnkhpeaefhjpbgkccckcacafjkj/':
        return
    header = sys.stdin.buffer.read(4)
    if len(header) != 4:
        return
    length = struct.unpack('<I', header)[0]
    if not 0 < length <= 4096:
        return
    raw = sys.stdin.buffer.read(length)
    request = json.loads(raw)
    if request == {'action':'extension-status'}:
        response=extension_status()
    elif request != {'action': 'connect'}:
        response = {'error': 'Unsupported action'}
    else:
        data_dir = Path(os.environ.get('SDM_DATA_DIR', str(Path.home() / '.sdm')))
        data_dir.mkdir(parents=True, exist_ok=True)
        token_path = data_dir / 'browser-token.txt'
        try:
            with token_path.open('x', encoding='ascii') as stream:
                stream.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app = Path(sys.executable).parent.parent / 'SDM.exe'
        if not app.is_file():
            response = {'error': 'SDM application not found'}
        else:
            process = subprocess.Popen([str(app), '--background'], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            response = {'token': token_path.read_text(encoding='ascii').strip(),
                        'port': int(os.environ.get('SDM_BRIDGE_PORT', '49282')),
                        'pid': process.pid}
    body = json.dumps(response).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('<I', len(body)) + body)
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
