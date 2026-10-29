"""Validate B01/B02/B03/B06 plus selection and adjacent queue menu previews."""
import hashlib
import os
from pathlib import Path
import sys
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette


def main():
    rows=[]
    for mode in ('light','dark'):
        p=palette('odak_'+mode)
        for name in ('main','drawer','multi','settings','empty','queue'):
            path=ROOT/'build'/f'phase5-odak-{mode}-{name}.png';data=path.read_bytes()
            with Image.open(path) as picture:
                image=picture.convert('RGB');w,h=image.size
                if image.getcolors(32) is not None:raise ValueError('Blank Odak preview: '+path.name)
                if name=='queue':valid=w>=250 and h>=100 and image.getpixel((w//2,h-4))==ImageColor.getrgb(p['card'])
                else:valid=w>=900 and h>=600 and image.getpixel((10,10))==ImageColor.getrgb(p['side']) and image.getpixel((70,10))==ImageColor.getrgb(p['side'] if name=='settings' else p['bg'])
                if not valid:raise ValueError('Wrong Odak palette/dimensions: '+path.name)
            rows.append(f'| {path.name} | {w}x{h} | `{hashlib.sha256(data).hexdigest()}` |')
    report='\n'.join(['## Odak previews: 12/12 validated','','| Preview | Size | SHA-256 |','|---|---|---|',*rows])+'\n';print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
