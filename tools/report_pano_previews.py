"""Validate P01/P02/P18/P19 PNGs and measured geometry against current sources."""
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

SOURCES=('layout_pano.py','pano_view.py','atlas_table.py','atlas_view.py','gui.py',
    'layout_atlas.py','theme_widgets.py','ui_overlays.py','ui_table_surface.py',
    'ui_surface.py','ui_tokens.py','ui_indicators.py','theme_layouts.py','test_ui_pano.py','tools/report_pano_previews.py')
STATES=('main','empty','compact','selection','menu','toast')
HUD_SOURCES=('feature_windows.py','ui_dialog.py','theme_widgets.py','ui_surface.py','ui_tokens.py',
    'ui_indicators.py','test_ui_pano_hud.py','tools/report_pano_previews.py')


def validate_hud(directory,source_root=ROOT):
    data=json.loads((directory/'pano-hud-layout.json').read_text(encoding='utf-8'))
    expected={name:hashlib.sha256((source_root/name).read_bytes()).hexdigest() for name in HUD_SOURCES}
    if data.get('sources')!=expected:raise ValueError('Stale Pano HUD source measurements')
    heights=[];rows=[]
    for size in ('normal','large','xlarge'):
        value=data.get(size,{})
        if value.get('card_width_delta') not in (0,1) or value.get('value_y_delta')!=0:
            raise ValueError('Invalid Pano HUD alignment')
        height=value.get('height')
        if not isinstance(height,int) or height<=0:raise ValueError('Invalid Pano HUD height')
        heights.append(height)
    if heights!=sorted(heights) or heights[0]>=heights[-1]:raise ValueError('Pano HUD text size did not grow')
    for state in ('normal','large','xlarge','empty'):
        path=directory/f'pano-hud-{state}.png';payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError('Stale Pano HUD PNG')
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w!=340 or h<150 or image.getpixel((w//2,4))!=ImageColor.getrgb(palette('pano_light')['bg']):
                raise ValueError('Invalid Pano HUD dimensions/palette')
            if image.getcolors(32) is not None:raise ValueError('Blank Pano HUD PNG')
        rows.append((path.name,w,h,digest))
    return rows


def validate_measurements(data,source_root=ROOT):
    actual=data.get('sources',{})
    expected={name:hashlib.sha256((source_root/name).read_bytes()).hexdigest() for name in SOURCES}
    if actual!=expected:raise ValueError('Stale Pano source measurements')
    errors=data.get('count_center_errors',[])
    if len(errors)!=4 or any(not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1.5 for value in errors):
        raise ValueError('Invalid Pano count centring')
    baseline=data.get('metric_baseline_spread')
    if not isinstance(baseline,(int,float)) or not math.isfinite(baseline) or not 0<=baseline<=1.5:
        raise ValueError('Invalid Pano metric baseline')
    for state in ('wide','compact'):
        geometry=data.get(state,{})
        for key in ('viewport','hero','list'):
            size=geometry.get(key,[])
            if len(size)!=2 or any(not isinstance(value,int) or value<=0 for value in size):
                raise ValueError('Invalid Pano geometry')
        if geometry['hero'][0]>geometry['viewport'][0] or geometry['list'][0]>geometry['viewport'][0]:
            raise ValueError('Overflowing Pano tile')
    return data


def validate_previews(directory,source_root=ROOT):
    data=validate_measurements(json.loads((directory/'pano-layout.json').read_text(encoding='utf-8')),source_root)
    p=palette('pano_light');rows=[]
    for state in STATES:
        path=directory/f'pano-{state}.png'
        if not path.is_file():raise ValueError('Missing Pano preview: '+path.name)
        payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if digest!=data.get('previews',{}).get(state):raise ValueError('Stale Pano PNG: '+path.name)
        with Image.open(path) as source:
            source.load()
            if source.format!='PNG':raise ValueError('Invalid Pano PNG')
            image=source.convert('RGB');width,height=image.size
            if state in ('menu','toast'):
                valid=width>=200 and height>=36 and image.getpixel((width//2,height-(10 if state=='toast' else 4)))==ImageColor.getrgb(p['toast'] if state=='toast' else p['bg'])
            else:valid=width>=1000 and height>=600 and image.getpixel((10,10))==ImageColor.getrgb(p['bg'])
            if not valid:raise ValueError('Invalid Pano dimensions/palette: '+path.name)
            if image.getcolors(maxcolors=32) is not None:raise ValueError('Blank Pano PNG: '+path.name)
            rows.append((path.name,width,height,digest))
    return rows,data


def main():
    rows,data=validate_previews(ROOT/'build')
    rows.extend(validate_hud(ROOT/'build'))
    lines=['## Pano P01/P02/P18/P19: 6/6 previews validated','',
        f'Measured count centre error ≤ {max(data["count_center_errors"]):g} px; metric baseline spread {data["metric_baseline_spread"]:g} px.',
        'Current source hashes, wide/compact tile geometry and exact PNG bytes checked. Files stay on the runner.','',
        'P15 HUD: 4/4 previews, three font sizes, equal cards and aligned values validated.','',
        '| Preview | Size | SHA-256 |','|---|---|---|']
    lines.extend(f'| {name} | {width}x{height} | `{digest}` |' for name,width,height,digest in rows)
    report='\n'.join(lines)+'\n';print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('Pano preview validation FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
