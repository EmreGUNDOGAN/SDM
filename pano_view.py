"""Pano presentation from live application rows; no engine or selection mutations."""
from pathlib import Path
from atlas_view import observed_parts, subtitle, number, matches_status, file_kind
from list_display import row_values

SUMMARY_FILTERS=(('Etkin','etkin'),('Kuyrukta','kuyrukta'),
    ('Duraklatılanlar','durdu'),('Tamamlananlar','bitti'))


def transfer_counts(app,records):
    statuses=[]
    for record in records:
        task=app.video_tasks.get(record['id']) or app.engine.get_task(record['id'])
        statuses.append(task.status if task else record['status'])
    return {key:sum(matches_status(status,key) for status in statuses) for key,_ in SUMMARY_FILTERS}


def current_transfer(app, records):
    """Show the fastest running transfer; saved/queued rows never fake activity."""
    rows=[(record,row_values(app,record)) for record in records]
    running=[row for row in rows if row[1][8] in ('İndiriliyor','Birleştiriliyor','Dönüştürülüyor')]
    def speed(row):
        task=app.video_tasks.get(row[0]['id']) or app.engine.get_task(row[0]['id'])
        return task.current_speed if task and task.status=='İndiriliyor' else 0
    running.sort(key=speed,reverse=True)
    if not running:return None
    queued=[row for row in rows if row[1][8] in ('Bekliyor','Kuyrukta')]
    candidates=running+queued
    record,values=running[0]
    _,connections=observed_parts(app,record)
    return dict(id=record['id'],name=record['filename'],subtitle=subtitle(record),
        extension=Path(record['filename']).suffix.lstrip('.').upper()[:4] or 'FILE',kind=file_kind(record),
        progress=min(1,max(0,float(values[5].rstrip('%'))/100)),
        received=number(app,values[3]),total=number(app,values[2]),
        speed=number(app,values[6]),eta=values[7],status=values[8],
        connections='—' if connections is None else str(connections),
        next_name=candidates[1][0]['filename'] if len(candidates)>1 else 'Başka indirme yok')
