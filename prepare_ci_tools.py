"""Fetch verified vendor binaries only during CI packaging, never at app runtime."""
import hashlib
import shutil
import subprocess
from pathlib import Path
import zipfile
import requests

ROOT=Path(__file__).resolve().parent
TOOLS=ROOT/'tools'
CACHE=ROOT/'build-tools'
INNO_VERSION='6.7.4'
INNO_SHA256='a549929319f9120716677c685535ca4671e4b937b5fdc87e2585f32d8eb30e8c'

def fetch(url,name,digest):
    target=CACHE/name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:return target
    with requests.get(url,stream=True,timeout=(30,180)) as response:
        response.raise_for_status()
        with target.open('wb') as stream:
            for chunk in response.iter_content(1024*1024):stream.write(chunk)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Vendor binary SHA-256 mismatch: '+name)
    return target


def prepare_inno():
    """Use the vendor's portable mode: no installed compiler, registry or icons."""
    installer=fetch(f'https://github.com/jrsoftware/issrc/releases/download/is-6_7_4/innosetup-{INNO_VERSION}.exe',
                    f'innosetup-{INNO_VERSION}.exe',INNO_SHA256)
    folder=CACHE/'inno'
    subprocess.run([str(installer),'/PORTABLE=1','/CURRENTUSER','/VERYSILENT',
                    '/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',
                    '/DIR='+str(folder)],check=True,timeout=120)
    if not (folder/'ISCC.exe').is_file():raise RuntimeError('Portable Inno Setup compiler is missing.')
    return folder/'ISCC.exe'

def main():
    TOOLS.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)
    ffmpeg=fetch('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip','ffmpeg.zip','60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba')
    with zipfile.ZipFile(ffmpeg) as archive:
        for name in ['ffmpeg.exe','ffprobe.exe','LICENSE','README.txt']:
            entry=next(p for p in archive.namelist() if p.endswith('/'+name))
            (TOOLS/name).write_bytes(archive.read(entry))
    deno=fetch('https://github.com/denoland/deno/releases/download/v2.9.7/deno-x86_64-pc-windows-msvc.zip','deno.zip','a0c3101b4158d1dfb7d6a78a7bf0f3de80c96bb423c152beec8beb22786f2238')
    with zipfile.ZipFile(deno) as archive:(TOOLS/'deno.exe').write_bytes(archive.read('deno.exe'))
    seven=Path('C:/Program Files/7-Zip')
    for name in ['7z.exe','7z.dll']:
        if not (seven/name).is_file():raise RuntimeError('Runner 7-Zip installation is missing.')
        shutil.copyfile(seven/name,TOOLS/name)
    shutil.copyfile(seven/'License.txt',TOOLS/'7ZIP-LICENSE.txt')
    prepare_inno()
    print('Verified FFmpeg, Deno and portable Inno Setup; runner 7-Zip copied with license.')

if __name__=='__main__':main()
