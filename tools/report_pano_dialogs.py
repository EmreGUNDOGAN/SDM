"""P03/P04 previews, source hashes and measured card/quality alignment."""
import hashlib,json,math,os,sys
from pathlib import Path
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette
SOURCES=('batch_dialog.py','capture_dialog.py','ui_dialog.py','theme_widgets.py','ui_surface.py',
    'ui_tokens.py','ui_controls.py','section_fields_ui.py','test_ui_pano_dialogs.py','tools/report_pano_dialogs.py')
STATES=('batch-empty','batch','batch-focus','batch-compact','capture-video','capture-audio','capture-file')


def validate(directory,root=ROOT):
    data=json.loads((directory/'pano-dialog-layout.json').read_text(encoding='utf-8'))
    if data.get('sources')!={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCES}:
        raise ValueError('Stale Pano dialog sources')
    if data.get('save_width_delta') not in (0,1) or data.get('quality_y_delta')!=0:raise ValueError('Wrong Pano dialog alignment')
    coverage=data.get('focus_coverage',[])
    if len(coverage)!=2 or any(not isinstance(value,(int,float)) or not math.isfinite(value) or not .9<=value<=1 for value in coverage):
        raise ValueError('Wrong Pano focus stroke')
    rows=[]
    for state in STATES:
        path=directory/f'pano-dialog-{state}.png';payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError('Stale Pano dialog PNG')
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w<560 or h<420 or image.getpixel((4,4))!=ImageColor.getrgb(palette('pano_light')['dialog']):
                raise ValueError('Wrong Pano dialog dimensions/palette')
            if image.getcolors(32) is not None:raise ValueError('Blank Pano dialog preview')
        rows.append((path.name,w,h,digest))
    return rows


def main():
    rows=validate(ROOT/'build')
    report='\n'.join(['## Pano P03/P04: 7/7 source/PNG/alignment checks passed','',
        '| Preview | Size | SHA-256 |','|---|---|---|',
        *(f'| {name} | {w}x{h} | `{digest}` |' for name,w,h,digest in rows)])+'\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
