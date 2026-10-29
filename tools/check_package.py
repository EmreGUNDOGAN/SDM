"""Verify frozen code/static assets, isolated desktop exit/reopen and setup SHA."""
import hashlib
import json
import marshal
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import types
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from tools.source_manifest import git,index_files
from app_version import VERSION
from tools.check_source import SIGNATURES

REQUIRED=('gui','utils','database','download_engine','video_downloader','browser_bridge',
 'theme_layouts','layout_atlas','layout_odak','modern_settings','queue_ui','download_window',
 'odak_cards','odak_drawer','batch_dialog','capture_dialog','completion_dialog','feature_ui',
 'feature_windows','ui_dialog','ui_controls','ui_indicators','ui_overlays','ui_surface','ui_thumbnail','package_smoke')

# Derived from the independently SHA-pinned ffmpeg.zip in prepare_ci_tools.
# These exact vendor blobs contain NUL-terminated PEM delimiter strings, not
# key payloads. No other binary/hash or nonterminated key header is exempt.
PEM_LITERAL_BINARIES={
    'ffmpeg.exe':'3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec',
    'ffprobe.exe':'f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52',
}
# This exact upstream module includes a public shared client identifier. Keep
# site support without treating it as a local/user credential. Any byte change
# is rejected and all other credential signatures remain checked.
# https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/extractor/shahid.py
PUBLIC_VENDOR_FILES={
    'yt_dlp/extractor/shahid.py':'f82c1f065f6aa3dd5ce8ee3491d4c49f245d1e7ba921b8cc0cc9c8658a634fbd',
}


def scan_packaged_credentials(path,content):
    expected=PEM_LITERAL_BINARIES.get(path.name.lower())
    public_expected=PUBLIC_VENDOR_FILES.get('/'.join(path.parts[-3:]))
    if expected and hashlib.sha256(content).hexdigest()!=expected:
        raise ValueError('Packaged vendor binary mismatch: '+path.name)
    if public_expected and hashlib.sha256(content).hexdigest()!=public_expected:
        raise ValueError('Packaged vendor source mismatch: '+path.name)
    for label,pattern in SIGNATURES:
        for match in re.finditer(pattern.encode('ascii'),content):
            if label=='private key' and expected and content[match.end():match.end()+1]==b'\0':
                continue
            if label=='AWS access key' and public_expected:
                continue
            raise ValueError('Packaged credential signature: '+label+' in '+path.name)


def normalized(code):
    if not isinstance(code,types.CodeType):raise ValueError('Expected compiled module code')
    return code.replace(co_filename='<source>',co_consts=tuple(normalized(value) if isinstance(value,types.CodeType) else value for value in code.co_consts))


def compare_code(name,actual,source):
    expected=compile(source,name,'exec',dont_inherit=True,optimize=0)
    if normalized(actual)!=normalized(expected):raise ValueError('Frozen/source code mismatch: '+name)


def verify_archive(executable,files,script,required=()):
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(executable));compare_code(script,marshal.loads(archive.extract(script)),git(ROOT,'cat-file','blob',files[script+'.py']))
    pyz=archive.open_embedded_archive('PYZ.pyz');missing=set(required)-set(pyz.toc)
    if missing:raise ValueError('Missing frozen modules: '+', '.join(sorted(missing)))
    checked=[]
    for path,oid in files.items():
        module=path[:-3].replace('/','.') if path.endswith('.py') else ''
        if module.endswith('.__init__'):module=module[:-9]
        if module in pyz.toc:
            compare_code(path,pyz.extract(module),git(ROOT,'cat-file','blob',oid));checked.append(path)
    return checked


def main():
    subprocess.run([sys.executable,str(ROOT/'tools/check_source.py')],cwd=ROOT,check=True)
    files=index_files(ROOT);executable=ROOT/'dist/SDM/SDM.exe';host=ROOT/'dist/SDMHost/SDMHost.exe'
    checked=verify_archive(executable,files,'main',REQUIRED)+verify_archive(host,files,'native_host')
    for folder in (executable.parent,host.parent):
        for path in folder.rglob('*'):
            if not path.is_file():continue
            if path.suffix.lower() in ('.db','.sqlite','.sqlite3','.key') or path.name.lower() in ('.env','browser-token.txt','github-update-token.bin','config.json'):raise ValueError('Forbidden packaged user-data/credential file: '+path.name)
            content=path.read_bytes()
            scan_packaged_credentials(path,content)
    static=[]
    for path in files:
        if path.startswith('assets/') and not path.endswith('.py'):
            target=executable.parent/'_internal'/path
            if target.read_bytes()!=(ROOT/path).read_bytes():raise ValueError('Packed asset mismatch: '+path)
            static.append(path)
    # The extension is a separate installer input. Its bytes and manifest are
    # covered by check_source; do not read any installed browser/profile copy.
    setup=ROOT/'dist'/f'SDM-Setup-{VERSION}.exe';digest=hashlib.sha256(setup.read_bytes()).hexdigest()
    checksum=setup.with_suffix('.sha256');checksum.write_text(f'{digest}  {setup.name}\n',encoding='ascii')
    if checksum.read_text(encoding='ascii').split()[0]!=hashlib.sha256(setup.read_bytes()).hexdigest():raise ValueError('Setup checksum mismatch')
    (ROOT/'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='package-check-',dir=ROOT/'build') as folder:
        for attempt in range(2):
            profile=Path(folder)/str(attempt);profile.mkdir();downloads=profile/'downloads';downloads.mkdir()
            (profile/'config.json').write_text(json.dumps(dict(download_dir=str(downloads),clipboard_monitoring=False,notifications_enabled=False,update_check_on_start=False,mini_hud=False)),encoding='utf-8')
            env=dict(os.environ,SDM_DATA_DIR=str(profile));subprocess.run([str(executable),'--package-self-test'],cwd=ROOT,env=env,check=True,timeout=90)
            result=json.loads((profile/'package-result.json').read_text(encoding='utf-8'))
            if result['views']!=['atlas_light','atlas_dark','odak_light','odak_dark'] or not result['tray_visible']:raise ValueError('Frozen desktop matrix failed')
    subprocess.run([sys.executable,str(ROOT/'test_update_handoff_live.py')],cwd=ROOT,env=dict(os.environ,SDM_DATA_DIR=str(ROOT/'build/package-handoff-data')),check=True)
    report=dict(version=VERSION,modules=checked,assets=static,desktop_runs=2,setup=setup.name,sha256=digest)
    (ROOT/'build/package-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'Frozen/source modules {len(checked)}, assets {len(static)}, desktop/tray exit/reopen, PowerShell handoff and setup SHA-256: OK')


if __name__=='__main__':main()
