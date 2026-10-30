"""P05 exact source/PNG bytes and measured transfer-card alignment."""
import hashlib,json,math,os,sys
from pathlib import Path
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette
SOURCES=('download_window.py','ui_indicators.py','theme_widgets.py','ui_surface.py','ui_tokens.py',
    'ui_dialog.py','utils.py','atlas_view.py','test_ui_pano_details.py','tools/report_pano_details.py')
STATES=('wide','compact','unknown','completed')


def validate(directory,root=ROOT):
    data=json.loads((directory/'pano-details-layout.json').read_text(encoding='utf-8'))
    if data.get('sources')!={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCES}:raise ValueError('Stale P05 sources')
    for key,limit in (('metric_width_delta',1),('metric_y_delta',0),('technical_overflow',0)):
        value=data.get(key)
        if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=limit:raise ValueError('Invalid P05 geometry')
    rows=[]
    for state in STATES:
        path=directory/f'pano-details-{state}.png';payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError('Stale P05 PNG')
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w<660 or h<420 or image.getpixel((4,4))!=ImageColor.getrgb(palette('pano_light')['dialog']):raise ValueError('Invalid P05 dimensions/palette')
            if image.getcolors(32) is not None:raise ValueError('Blank P05 PNG')
        rows.append((path.name,w,h,digest))
    return rows


def main():
    rows=validate(ROOT/'build')
    report='\n'.join(['## Pano P05: 4/4 source/PNG/geometry checks passed','',
        '| Preview | Size | SHA-256 |','|---|---|---|',*(f'| {name} | {w}x{h} | `{digest}` |' for name,w,h,digest in rows)])+'\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
