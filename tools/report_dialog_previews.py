"""Required source-window and browser previews: exact palette and actual PNG SHA."""
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette
NAMES=('batch','capture','detail','graph','hud','completion','update','message','tools')
P06_SOURCES=('completion_dialog.py','ui_dialog.py','theme_widgets.py','ui_surface.py','ui_controls.py',
    'ui_tokens.py','ui_indicators.py','theme_catalog.py','test_ui_pano_completion.py','tools/report_dialog_previews.py')


def validate_pano_completion(directory,source_root=ROOT):
    data=json.loads((directory/'p06-layout.json').read_text(encoding='utf-8'))
    expected={name:hashlib.sha256((source_root/name).read_bytes()).hexdigest() for name in P06_SOURCES}
    if data.get('sources')!=expected:raise ValueError('Stale P06 source measurements')
    for key,limit in (('stat_width_spread',1),('stat_value_y_spread',0),('card_edge_delta',0)):
        value=data.get(key)
        if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=limit:
            raise ValueError('Invalid P06 alignment: '+key)
    rows=[];p=palette('pano_light')
    for state in ('pano','pano-scanned'):
        path=directory/f'p06-{state}.png';payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError('Stale P06 PNG: '+path.name)
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w<560 or h<500 or image.getpixel((0,0))!=ImageColor.getrgb(p['dialog']):
                raise ValueError('Invalid P06 dimensions/palette: '+path.name)
            if image.getcolors(32) is not None:raise ValueError('Blank P06 preview: '+path.name)
        rows.append((path.name,w,h,digest))
    return rows,data


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
    pano,data=validate_pano_completion(ROOT/'build');rows.extend(pano)
    lines=['## Download/tool/message and browser previews: 20/20 validated','',
        'Pano P06: 2/2 current source/PNG digests validated; three equal-width cards, aligned values and file/scan card edges.',
        f'Card width spread {data["stat_width_spread"]:g} px; value row spread {data["stat_value_y_spread"]:g} px; card edge delta {data["card_edge_delta"]:g} px.','',
        '| Preview | Size | SHA-256 |','|---|---|---|']
    lines.extend(f'| {name} | {w}x{h} | `{digest}` |' for name,w,h,digest in rows)
    report='\n'.join(lines)+'\n';print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
