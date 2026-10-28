"""Validate all six settings sections in four design/mode combinations."""
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
    for design in ('atlas','odak'):
        for mode in ('light','dark'):
            p=palette(design+'_'+mode)
            for index in range(6):
                path=ROOT/'build'/f'phase4-{design}-{mode}-{index}.png'
                data=path.read_bytes()
                with Image.open(path) as picture:
                    image=picture.convert('RGB');w,h=image.size
                    if w<760 or h<500 or image.getcolors(32) is not None:raise ValueError('Wrong/blank settings preview: '+path.name)
                    if image.getpixel((10,10))!=ImageColor.getrgb(p['side']) or image.getpixel((230,10))!=ImageColor.getrgb(p['dialog']):raise ValueError('Wrong settings palette: '+path.name)
                rows.append(f'| {path.name} | {w}x{h} | `{hashlib.sha256(data).hexdigest()}` |')
    report='\n'.join(['## Settings previews: 24/24 validated','','| Preview | Size | SHA-256 |','|---|---|---|',*rows])+'\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
