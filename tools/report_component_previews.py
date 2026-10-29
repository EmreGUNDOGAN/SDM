"""Validate all eight native preview files and write a quota-free job summary.

This is a required validation step, not an ignored artifact-upload error.
Images stay local to the runner; only their checks and SHA-256 enter the summary.
"""
import hashlib
import os
from pathlib import Path
import sys
from PIL import Image,ImageColor

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import THEMES,palette


def validate_previews(directory):
    rows=[]
    for theme in THEMES:
        p=palette(theme)
        for suffix in ('','-timeline'):
            path=directory/f'phase1-components-{theme}{suffix}.png'
            if not path.is_file():raise ValueError(f'Missing required preview: {path.name}')
            data=path.read_bytes()
            with Image.open(path) as image:
                image.load()
                if image.format!='PNG' or image.width<20 or image.height<20:
                    raise ValueError(f'Invalid PNG preview: {path.name}')
                image=image.convert('RGB')
                if image.getpixel((image.width-10,10))!=ImageColor.getrgb(p['bg']):
                    raise ValueError(f'Wrong palette background: {path.name}')
                if image.getpixel((4,4))!=ImageColor.getrgb(p['accent']):
                    raise ValueError(f'Wrong rendered marker: {path.name}')
                rows.append((path.name,image.width,image.height,hashlib.sha256(data).hexdigest()))
    return rows


def main():
    rows=validate_previews(ROOT/'build')
    lines=['## Native component previews: 8/8 validated','',
           'Palette/background/marker checks passed; screenshots remain on the runner.',
           'No artifact upload or storage quota is required.','',
           '| Preview | Size | SHA-256 |','|---|---|---|']
    lines.extend(f'| {name} | {width}×{height} | `{digest}` |' for name,width,height,digest in rows)
    report='\n'.join(lines)+'\n';print(report)
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as file:file.write(report)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError) as error:
        print(f'Preview validation FAILED: {error}',file=sys.stderr);raise SystemExit(1)
