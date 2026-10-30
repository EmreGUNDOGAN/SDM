"""Validate all six settings sections in four design/mode combinations."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette
PANO_SOURCES=('modern_settings.py','queue_ui.py','ui_controls.py','ui_dialog.py','ui_tokens.py',
    'theme_widgets.py','ui_surface.py','test_ui_pano_settings.py','tools/report_settings_previews.py')
PANO_STATES=tuple(str(index) for index in range(6))+('counters','compact','compact-update','compact-backup')


def validate_pano(directory,root=ROOT):
    data=json.loads((directory/'pano-settings-layout.json').read_text(encoding='utf-8'))
    if data.get('sources')!={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in PANO_SOURCES}:raise ValueError('Stale Pano settings sources')
    errors=data.get('control_center_errors',[])
    if len(errors)!=4 or any(not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=.5 for value in errors):raise ValueError('Invalid counter alignment')
    rows=[]
    for state in PANO_STATES:
        path=directory/f'pano-settings-{state}.png';payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError('Stale Pano settings PNG')
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w<760 or h<500 or image.getpixel((4,4))!=ImageColor.getrgb(palette('pano_light')['dialog']):raise ValueError('Invalid Pano settings dimensions/palette')
            if image.getcolors(32) is not None:raise ValueError('Blank Pano settings PNG')
        rows.append(f'| {path.name} | {w}x{h} | `{digest}` |')
    return rows


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
    rows.extend(validate_pano(ROOT/'build'))
    report='\n'.join(['## Settings previews: 24/24 Atlas/Odak and 10/10 Pano validated','',
        'Pano counter centres ≤0.5 px; current source/PNG SHA-256 checked.','',
        '| Preview | Size | SHA-256 |','|---|---|---|',*rows])+'\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
