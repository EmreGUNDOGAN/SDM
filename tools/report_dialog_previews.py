"""Required source-window and browser previews: exact palette and actual PNG SHA."""
import hashlib
import os
import sys
from pathlib import Path
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette
NAMES=('batch','capture','detail','graph','hud','completion','update','message','tools')


def validate(directory):
    results=[]
    for mode in ('light','dark'):
        p=palette('atlas_'+mode)
        for name in NAMES:
            path=directory/f'phase3-{name}-{mode}.png'
            if not path.is_file():raise ValueError('Missing dialog preview: '+path.name)
            data=path.read_bytes()
            with Image.open(path) as image:
                image.load();image=image.convert('RGB');w,h=image.size
                # The HUD fits its rows: exactly 340 px wide, shorter with no active download (A15).
                if (name=='hud' and (w!=340 or h<120)) or (name!='hud' and (w<300 or h<150)):raise ValueError('Wrong dialog dimensions: '+path.name)
                expected=p['hud'] if name=='hud' else p['side'] if name=='tools' else p['dialog']
                if image.getpixel((10,10))!=ImageColor.getrgb(expected):raise ValueError('Wrong dialog palette: '+path.name)
                if name=='tools' and image.getpixel((w-10,10))!=ImageColor.getrgb(p['dialog']):raise ValueError('Wrong tools content palette: '+path.name)
                if image.getcolors(32) is not None:raise ValueError('Blank dialog preview: '+path.name)
            results.append((path.name,w,h,hashlib.sha256(data).hexdigest()))
    for kind in ('video','audio'):
        path=directory/f'phase3-extension-{kind}.png'
        if not path.is_file():raise ValueError('Missing browser preview: '+path.name)
        data=path.read_bytes()
        with Image.open(path) as image:
            image.load();image=image.convert('RGB');w,h=image.size
            colors=image.getcolors(w*h)
            if w<800 or h<500 or not any(color==(33,86,217) for _,color in colors):raise ValueError('Wrong browser preview: '+path.name)
        results.append((path.name,w,h,hashlib.sha256(data).hexdigest()))
    return results


def main():
    rows=validate(ROOT/'build')
    lines=['## Download/tool/message and browser previews: 20/20 validated','',
        '| Preview | Size | SHA-256 |','|---|---|---|']
    lines.extend(f'| {name} | {w}x{h} | `{digest}` |' for name,w,h,digest in rows)
    report='\n'.join(lines)+'\n';print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
