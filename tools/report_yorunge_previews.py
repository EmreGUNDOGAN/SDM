"""Validate Yörünge source-bound screenshots and native instrument geometry."""
import hashlib,json,math,os,sys
from pathlib import Path
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette
SOURCES=('layout_yorunge.py','yorunge_view.py','yorunge_indicators.py','ui_surface.py','ui_tokens.py',
    'theme_widgets.py','theme_layouts.py','ui_indicators.py','ui_overlays.py','atlas_table.py',
    'atlas_view.py','ui_table_surface.py','utils.py','preferences.py','test_ui_yorunge.py','tools/report_yorunge_previews.py')
STATES=('empty','main','selection','compact','compact-telemetry','menu','toast')


def validate_previews(directory,root=ROOT):
    data=json.loads((directory/'yorunge-layout.json').read_text(encoding='utf-8'))
    if data.get('sources')!={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCES}:raise ValueError('Stale Yörünge sources')
    errors=data.get('header_center_errors',[])
    if len(errors)!=3 or any(type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=.5 for value in errors):raise ValueError('Invalid Yörünge header alignment')
    error=data.get('gauge_center_error')
    if type(error) not in (int,float) or not math.isfinite(error) or not 0<=error<=1.5:raise ValueError('Invalid Yörünge gauge alignment')
    if data.get('active_progress_cells')!=5:raise ValueError('Invalid Yörünge segmented progress')
    for state in ('wide','compact'):
        entry=data.get(state,{})
        for key in ('viewport','telemetry','list'):
            size=entry.get(key,[])
            if len(size)!=2 or any(type(value) is not int or value<=0 for value in size):raise ValueError('Invalid Yörünge geometry')
        if entry.get('right_visible')!=(state=='wide'):raise ValueError('Invalid Yörünge responsive target')
        if entry['telemetry'][0]>entry['viewport'][0] or entry['list'][0]>entry['viewport'][0]:raise ValueError('Overflowing Yörünge panel')
    rows=[];p=palette('yorunge_dark')
    for state in STATES:
        path=directory/f'yorunge-{state}.png';digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError('Stale Yörünge PNG')
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w<(200 if state in ('menu','toast') else 1080) or h<(36 if state in ('menu','toast') else 640):raise ValueError('Invalid Yörünge dimensions')
            if state not in ('menu','toast') and image.getpixel((10,10))!=ImageColor.getrgb(p['bg']):raise ValueError('Invalid Yörünge palette')
            if image.getcolors(32) is not None:raise ValueError('Blank Yörünge PNG')
        rows.append(f'| {path.name} | {w}x{h} | `{digest}` |')
    return rows,data


def main():
    rows,data=validate_previews(ROOT/'build')
    report='\n'.join(['## Yörünge F01/F02/F18/F19: 7/7 validated','',
        f'Header centres ≤0.5 px; gauge centre error {data["gauge_center_error"]:g} px; 25% = 5 separate cells.',
        'Current source/PNG SHA-256 and wide/compact geometry checked.','',
        '| Preview | Size | SHA-256 |','|---|---|---|',*rows])+'\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as file:file.write(report)


if __name__=='__main__':main()
