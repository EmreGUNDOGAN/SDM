"""Prepare the existing SHA-pinned FFmpeg/FFprobe solely for isolated tests."""
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from prepare_ci_tools import fetch,CACHE,TOOLS


def main():
    CACHE.mkdir(exist_ok=True);TOOLS.mkdir(exist_ok=True)
    archive=fetch('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip','ffmpeg.zip','60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba')
    with zipfile.ZipFile(archive) as bundle:
        for name in ('ffmpeg.exe','ffprobe.exe'):
            entry=next(path for path in bundle.namelist() if path.endswith('/'+name))
            (TOOLS/name).write_bytes(bundle.read(entry))
    print('SHA-256 verified FFmpeg/FFprobe ready for disposable-profile tests')


if __name__=='__main__':main()
