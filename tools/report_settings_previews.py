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
YORUNGE_SOURCES=PANO_SOURCES+('test_ui_yorunge_settings.py',)
PANO_STATES=tuple(str(index) for index in range(6))+('counters','compact','compact-update','compact-backup')


def validate_pano(directory,root=ROOT):
    return validate_settings(directory,'pano',root)


def validate_settings(directory,design,root=ROOT):
    sources=YORUNGE_SOURCES if design=='yorunge' else PANO_SOURCES
    data=json.loads((directory/f'{design}-settings-layout.json').read_text(encoding='utf-8'))
    if data.get('sources')!={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}:raise ValueError(f'Stale {design} settings sources')
    errors=data.get('control_center_errors',[])
    if len(errors)!=4 or any(not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=.5 for value in errors):raise ValueError('Invalid counter alignment')
    if design=='yorunge':
        starts=data.get('nav_text_x',[])
        if len(starts)!=6 or any(type(value) is not int or not 14<=value<=18 for value in starts) or max(starts)-min(starts)>1:raise ValueError('Invalid navigation alignment')
    rows=[]
    for state in PANO_STATES:
        path=directory/f'{design}-settings-{state}.png';payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError(f'Stale {design} settings PNG')
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w<760 or h<500 or image.getpixel((4,4))!=ImageColor.getrgb(palette(design+('_dark' if design=='yorunge' else '_light'))['dialog']):raise ValueError(f'Invalid {design} settings dimensions/palette')
            if image.getcolors(32) is not None:raise ValueError(f'Blank {design} settings PNG')
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
    rows.extend(validate_settings(ROOT/'build','yorunge'))
    report='\n'.join(['## Settings previews: 24/24 Atlas/Odak, 10/10 Pano and 10/10 Yörünge validated','',
        'Pano/Yörünge counter centres ≤0.5 px; current source/PNG SHA-256 checked.','',
        '| Preview | Size | SHA-256 |','|---|---|---|',*rows])+'\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
