"""P14 exact source/PNG bytes and measured tool-card geometry."""
import hashlib,json,os,sys
from pathlib import Path
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from theme_catalog import palette
SOURCES=('feature_windows.py','feature_ui.py','ui_controls.py','ui_dialog.py','theme_widgets.py',
    'ui_surface.py','ui_tokens.py','test_ui_pano_tools.py','tools/report_pano_tools.py')
STATES=('empty','media','links','compact','completed')


def validate(directory,root=ROOT):
    data=json.loads((directory/'pano-tools-layout.json').read_text(encoding='utf-8'))
    if data.get('sources')!={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCES}:raise ValueError('Stale P14 sources')
    if data.get('tool_width_delta') not in (0,1):raise ValueError('Invalid P14 alignment')
    rows=[]
    for state in STATES:
        path=directory/f'pano-tools-{state}.png';payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
        if data.get('previews',{}).get(state)!=digest:raise ValueError('Stale P14 PNG')
        with Image.open(path) as source:
            source.load();image=source.convert('RGB');w,h=image.size
            if source.format!='PNG' or w<560 or h<420 or image.getpixel((4,4))!=ImageColor.getrgb(palette('pano_light')['dialog']):raise ValueError('Invalid P14 dimensions/palette')
            if image.getcolors(32) is not None:raise ValueError('Blank P14 PNG')
        rows.append((path.name,w,h,digest))
    return rows


def main():
    rows=validate(ROOT/'build')
    report='\n'.join(['## Pano P14: 5/5 source/PNG/alignment checks passed','',
        '| Preview | Size | SHA-256 |','|---|---|---|',*(f'| {name} | {w}x{h} | `{digest}` |' for name,w,h,digest in rows)])+'\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write(report)


if __name__=='__main__':main()
