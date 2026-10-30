"""Atlas presentation values. No engine, persistence or scheduling mutations."""
import json
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_COLUMNS=('filename','size','progress','speed','eta','status')
CATEGORY_TILES={'Belgeler':('DOC','document'),'Resimler':('IMG','image'),
    'Müzik':('AUD','audio'),'Video':('VID','video'),'Arşivler':('ARC','archive'),
    'Programlar':('APP','program'),'Diğer':('…','other')}


def column_preferences(design):
    if design=='pano':return 'pano_visible_columns',('filename','progress','size','status')
    if design=='yorunge':return 'yorunge_visible_columns',('filename','progress','speed','eta','status')
    return 'visible_columns',DEFAULT_COLUMNS


def file_kind(record):
    if Path(record.get('filename','')).suffix.lower() in ('.iso','.img'):return 'disk'
    return CATEGORY_TILES.get(record.get('category'),('','other'))[1]


def domain(record):
    try:return urlsplit(record.get('url','')).hostname or ''
    except ValueError:return ''


def subtitle(record):
    fields=[record.get('category','Diğer'),domain(record)]
    try:options=json.loads(record.get('options_json') or '{}')
    except (TypeError,ValueError):options={}
    if isinstance(options,dict) and options.get('height'):fields.append(str(options['height'])+'p')
    return ' · '.join(str(value) for value in fields if value)


def matches_status(status,selected):
    # Keep the existing unfinished-download filter, and add the error view.
    if selected=='Etkin':return status in ('İndiriliyor','Birleştiriliyor','Dönüştürülüyor')
    if selected=='Kuyrukta':return status in ('Bekliyor','Kuyrukta')
    if selected=='Duraklatılanlar':return status=='Duraklatıldı'
    if selected=='Devam Edenler':return status not in ('Tamamlandı','İptal Edildi')
    if selected=='Tamamlananlar':return status=='Tamamlandı'
    if selected=='Hatalı':return status not in ('Tamamlandı','Bekliyor','Kuyrukta',
        'Duraklatıldı','İndiriliyor','Birleştiriliyor','Dönüştürülüyor')
    return True


def available_actions(statuses):
    statuses=tuple(statuses);single=len(statuses)==1;selected=bool(statuses)
    unfinished=any(s!='Tamamlandı' for s in statuses)
    return dict(open=single and statuses[0]=='Tamamlandı',folder=single,details=single,
        resume=any(s not in ('Tamamlandı','İndiriliyor','Bekliyor','Birleştiriliyor','Dönüştürülüyor') for s in statuses),
        pause=any(s not in ('Tamamlandı','İptal Edildi','Duraklatıldı') for s in statuses),
        cancel=any(s not in ('Tamamlandı','İptal Edildi') for s in statuses),
        restart=selected,queue=unfinished,priority=selected,graph=single,
        verify=single and statuses[0]=='Tamamlandı',remove=selected)


def number(app,value):
    """Display form of a formatted value: Turkish decimal comma and 'KB/sn' speeds."""
    if app.settings.get('language','tr')!='tr':return str(value)
    import re
    return re.sub(r'/s\b','/sn',str(value).replace('.',','))


def observed_parts(app,record):
    task=app.video_tasks.get(record['id']) or app.engine.get_task(record['id'])
    if not task:return (),None
    if hasattr(task,'transfer_details'):streams=task.transfer_details.snapshot()
    elif hasattr(task,'transfer_snapshot'):streams=(task.transfer_snapshot(),)
    else:return (),None
    rows=tuple(row for stream in streams for row in stream['rows'])
    counts=[stream.get('active_count') if stream.get('observed',bool(stream['rows'])) else None for stream in streams]
    active=sum(counts) if counts and all(count is not None for count in counts) else None
    return rows,active
