"""Named queues and recurrence, independent of Tk and transfer workers."""
from datetime import datetime, timedelta

def default_queue(name='Ana kuyruk'):
    return dict(name=name,limit=3,enabled=False,days=list(range(7)),start='02:00',stop='07:00',once='')

def validate_queues(queues):
    if not isinstance(queues,list) or not 1<=len(queues)<=30:raise ValueError('1–30 kuyruk tanımlanabilir.')
    names=set()
    for queue in queues:
        name=queue.get('name','')
        if not isinstance(name,str) or not name.strip() or len(name)>60 or name in names:raise ValueError('Kuyruk adları benzersiz ve 1–60 karakter olmalı.')
        names.add(name)
        if type(queue.get('limit')) is not int or not 1<=queue['limit']<=10:raise ValueError('Kuyruk limiti 1–10 olmalı.')
        if type(queue.get('enabled')) is not bool:raise ValueError('Geçersiz zamanlama.')
        for field in ('start','stop'):datetime.strptime(queue[field],'%H:%M')
        if queue['start']==queue['stop']:raise ValueError('Başlangıç ve durma saatleri farklı olmalı.')
        if not isinstance(queue.get('days'),list) or any(type(d) is not int or d not in range(7) for d in queue['days']):raise ValueError('Geçersiz günler.')
        if queue.get('once'):datetime.strptime(queue['once'],'%Y-%m-%d %H:%M')
    return queues

def scheduled_active(queue,now=None):
    now=now or datetime.now()
    if not queue.get('enabled'):return False
    start=datetime.strptime(queue['start'],'%H:%M').time()
    stop=datetime.strptime(queue['stop'],'%H:%M').time()
    anchor=now.date()
    if stop<start and now.time()<stop:anchor-=timedelta(days=1)
    beginning=datetime.combine(anchor,start)
    ending=datetime.combine(anchor,stop)+(timedelta(days=1) if stop<start else timedelta())
    return anchor.weekday() in queue['days'] and beginning<=now<ending

def ordered_records(records):
    return sorted(records,key=lambda r:(-r.get('priority',0),r['id']))
