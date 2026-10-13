"""Observed transfer details. Configured limits are never reported as live counts."""
from collections import OrderedDict
import threading

def stream_label(info):
    label='Ses' if info.get('vcodec')=='none' else 'Görüntü' if info.get('acodec')=='none' else 'Video/ses'
    return label+(' · '+str(info['format_id']) if info.get('format_id') else '')

class TransferDetails:
    def __init__(self):self.lock=threading.Lock();self.streams=OrderedDict()
    def begin(self,key,method,label,reason='',task=None):
        with self.lock:
            self.streams[key]=dict(key=key,method=method,label=label,reason=reason,task=task,rows=OrderedDict(),observed=False,completed=0,peak=0)
    def progress(self,key,row_key,index,received,total,active,state):
        with self.lock:
            stream=self.streams.get(key)
            if not stream:return
            previous=stream['rows'].get(row_key)
            if state=='Tamamlandı' and (not previous or previous['state']!='Tamamlandı'):stream['completed']+=1
            stream['observed']=True
            stream['rows'][row_key]=dict(index=index,start=None,received=received,total=total,active=active,state=state)
            stream['peak']=max(stream['peak'],sum(row['active'] for row in stream['rows'].values()))
            # Keep active fragments and recent history; never grow with a multi-hour video.
            while len(stream['rows'])>80:
                old=next((k for k,v in stream['rows'].items() if not v['active'] and k!=row_key),None)
                if old is None:break
                del stream['rows'][old]
    def ensure(self,key,method,label):
        with self.lock:
            if key not in self.streams:
                self.streams[key]=dict(key=key,method=method,label=label,reason='',task=None,rows=OrderedDict(),observed=False,completed=0,peak=0)
    def snapshot(self):
        with self.lock:
            streams=[dict(s,rows=[dict(row) for row in s['rows'].values()]) for s in self.streams.values()]
        results=[]
        for stream in streams:
            task=stream.pop('task')
            if task:
                data=task.transfer_snapshot();stream['rows']=data['rows'];stream['observed']=True
                stream['peak']=data['peak']
            stream['active_count']=sum(row['active'] for row in stream['rows']) if stream['observed'] else None
            stream['part_count']=len(stream['rows']) if stream['method']=='HTTP Range' else None
            results.append(stream)
        return results
