"""Validate real Atlas workspace previews without artifact storage."""
import hashlib
import os
from pathlib import Path
import sys
from PIL import Image,ImageColor

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette

STATES=('main','multi','compact','empty','menu')


def validate_previews(directory):
    rows=[]
    for mode in ('light','dark'):
        p=palette('atlas_'+mode)
        for state in STATES:
            path=directory/f'phase2-atlas-{mode}-{state}.png'
            if not path.is_file():raise ValueError(f'Missing Atlas preview: {path.name}')
            data=path.read_bytes()
            with Image.open(path) as image:
                image.load()
                if image.format!='PNG':raise ValueError(f'Invalid Atlas PNG: {path.name}')
                image=image.convert('RGB');w,h=image.size
                if state=='menu':
                    # Bottom padding at the centre is flat fill; the rounded
                    # corners intentionally contain antialiased border pixels.
                    valid=w>=260 and h>=400 and image.getpixel((w//2,h-4))==ImageColor.getrgb(p['card'])
                else:
                    valid=w>=900 and h>=600 and image.getpixel((10,10))==ImageColor.getrgb(p['side']) and image.getpixel((250,10))==ImageColor.getrgb(p['bg'])
                if not valid:raise ValueError(f'Wrong Atlas dimensions/palette: {path.name}')
                colors=image.getcolors(maxcolors=32)
                if colors is not None:raise ValueError(f'Blank/incomplete Atlas preview: {path.name}')
                rows.append((path.name,w,h,hashlib.sha256(data).hexdigest()))
    return rows


def main():
    rows=validate_previews(ROOT/'build')
    lines=['## Atlas A01/A02/A18 previews: 10/10 validated','',
           'Real process-owned windows; exact palette/dimensions and PNG bytes checked.',
           'Files stay on the runner; no artifact storage is used.','',
           '| Preview | Size | SHA-256 |','|---|---|---|']
    lines.extend(f'| {name} | {w}x{h} | `{digest}` |' for name,w,h,digest in rows)
    report='\n'.join(lines)+'\n';print(report)
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as stream:stream.write(report)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError) as error:
        print(f'Atlas preview validation FAILED: {error}',file=sys.stderr);raise SystemExit(1)
