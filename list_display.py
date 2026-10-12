from utils import format_bytes, format_speed, format_eta

COLUMNS = [('id','ID',45),('filename','Dosya Adı',260),('size','Boyut',95),
           ('downloaded','İndirilen',100),('remaining','Kalan Boyut',100),
           ('progress','İlerleme',85),('speed','Hız',100),('eta','Kalan Süre',120),
           ('status','Durum',115),('category','Kategori',90),('date_added','Eklenme Tarihi',140)]


def row_values(window, record):
    task=window.engine.get_task(record['id'])
    video=window.video_tasks.get(record['id'])
    active=video or task
    status=active.status if active else record['status']
    received=record['downloaded_bytes']
    total=record['filesize']
    if status=='İndiriliyor':
        received=video.downloaded_bytes if video else (sum(s.downloaded_bytes for s in task.segments) if task else received)
        total=video.total_bytes if video else (task.filesize if task else total)
    pct=min(100,received/total*100) if total else 0
    if status=='Tamamlandı':pct=100
    speed=format_speed(active.current_speed) if active and status=='İndiriliyor' else '—'
    eta=format_eta(active.eta) if active and status=='İndiriliyor' else '—'
    return (record['id'],record['filename'],format_bytes(total) if total else 'Bilinmiyor',
            format_bytes(received),format_bytes(max(0,total-received)) if total else '—',
            f'{pct:.1f}%',speed,eta,status,record['category'],record['date_added'])
