"""A05 transfer content reused by a separate window and the Odak drawer."""
from pathlib import Path
import tkinter as tk
import os
from ui_dialog import AppWindow,AutoCard,label,action
from ui_controls import CheckBox
from ui_indicators import ProgressRing,SpeedChart,PartMap,FileTile,StatusBadge
from theme_widgets import Button
from ui_tokens import SIZES
from utils import format_bytes,format_speed,format_eta
from atlas_view import number,file_kind,subtitle


class TransferContent(tk.Frame):
    def __init__(self,master,parent,did):
        super().__init__(master,bg=parent.palette['canvas']);self.parent=parent;self.did=did;self.p=parent.palette
        keys=('url','state','total','received','speed','eta','resume','method','connections','path','average','peak','active_time')
        self.values={key:tk.StringVar(self,'') for key in keys};self.display={key:tk.StringVar(self,'') for key in keys}
        top=tk.Frame(self,bg=self.p['canvas']);top.pack(fill='x',pady=(16,0))
        left=AutoCard(top,self.p);left.pack_configure(side='left',fill='both',expand=True,padx=(24,8))
        self.ring=ProgressRing(left.content,self.p,value=None);self.ring.pack(side='left',padx=(0,12))
        summary=tk.Frame(left.content,bg=self.p['card']);summary.pack(side='left',fill='x',expand=True)
        for key,title in (('received','İndirilen'),('total','Toplam'),('eta','Kalan süre')):
            label(summary,title,palette=self.p,size=12,muted=True).pack(anchor='w',pady=(4,2))
            label(summary,variable=self.display[key],palette=self.p,size=14,weight='SemiBold').pack(anchor='w')
        right=AutoCard(top,self.p);right.pack_configure(side='left',fill='both',expand=True,padx=(8,24))
        label(right.content,'Aktarım hızı',palette=self.p,size=12,muted=True).pack(anchor='w')
        label(right.content,variable=self.display['speed'],palette=self.p,size=24,weight='Bold').pack(anchor='w')
        self.chart=SpeedChart(right.content,self.p,width=380,height=130,formatter=lambda text:number(parent,text));self.chart.pack(fill='x')
        average=label(right.content,variable=self.display['average'],palette=self.p,size=12,muted=True);average.pack(anchor='w')
        # Ellipsize to the card instead of running past its right edge.
        right.content.bind('<Configure>',lambda e:(setattr(average,'max_width',max(40,e.width-4)),average.draw()),add='+')
        top.bind('<Configure>',lambda e:self.arrange_cards(e,left,right))
        parts=AutoCard(self,self.p)
        label(parts.content,'Parça haritası',palette=self.p,weight='SemiBold').pack(anchor='w')
        label(parts.content,variable=self.display['connections'],palette=self.p,size=12,muted=True).pack(anchor='w',pady=6)
        self.parts=PartMap(parts.content,self.p,rows=(),height=80);self.parts.pack(fill='x')
        technical=AutoCard(self,self.p)
        # A05: one label column, equal row heights and hairlines; values used to
        # start right after each label, so every row began at a different x.
        for index,(key,title) in enumerate((('url','Adres'),('path','Kayıt yeri'),('method','Yöntem'),('resume','Sürdürme'))):
            if index:tk.Frame(technical.content,bg=self.p['line_soft'],height=1).pack(fill='x')
            row=tk.Frame(technical.content,bg=self.p['card'],height=44);row.pack(fill='x');row.pack_propagate(False)
            column=tk.Frame(row,bg=self.p['card'],width=140,height=44);column.pack(side='left');column.pack_propagate(False)
            label(column,title,palette=self.p,muted=True).pack(side='left')
            if key=='url':Button(row,'Kopyala',self.copy_url,palette=self.p,kind='soft',height=SIZES['small_button']).pack(side='right')
            if key=='path':Button(row,'Klasörü aç',self.open_folder,palette=self.p,kind='soft',height=SIZES['small_button']).pack(side='right')
            item=label(row,variable=self.display[key],palette=self.p);item.max_width=520;item.pack(side='left')
        self.snapshot=None

    def arrange_cards(self,event,left,right):
        if event.widget is not left.master:return
        stacked=event.width<800
        left.pack_configure(side='top' if stacked else 'left',fill='x' if stacked else 'both',expand=not stacked,padx=24 if stacked else (24,8))
        right.pack_configure(side='top' if stacked else 'left',fill='x' if stacked else 'both',expand=not stacked,padx=24 if stacked else (8,24))

    def copy_url(self):self.clipboard_clear();self.clipboard_append(self.values['url'].get())
    def open_folder(self):
        path=Path(self.values['path'].get()).parent
        if path.exists():os.startfile(str(path))

    def refresh(self):
        app=self.parent;record=app.db.get_download(self.did)
        if not record:return None
        video=app.video_tasks.get(self.did);task=app.engine.get_task(self.did);active=video or task
        state=active.status if active else record['status']
        total=video.total_bytes if video else task.filesize if task else record['filesize']
        received=video.downloaded_bytes if video else sum(s.downloaded_bytes for s in task.segments) if task else record['downloaded_bytes']
        if state=='Tamamlandı':received=record['downloaded_bytes'];total=record['filesize']
        ratio=min(1,received/total) if total else None
        if state=='Tamamlandı':ratio=1
        streams=video.transfer_details.snapshot() if video else []
        if task:
            direct=task.transfer_snapshot();streams=[dict(direct,label='Dosya',observed=bool(direct['rows']))]
        measured=bool(streams) and all(s.get('observed',False) and s.get('active_count') is not None for s in streams)
        count=str(sum(s['active_count'] for s in streams)) if measured else 'Henüz ölçülmedi'
        peak=max((s.get('peak',0) for s in streams),default=0)
        method=' / '.join(dict.fromkeys(s['method'] for s in streams)) if streams else getattr(video,'unobserved_method','Hazırlanıyor · henüz ölçüm yok')
        history=getattr(app,'speed_history',{}).get(self.did);points=tuple(history.points) if history else ()
        latest=points[-1][0] if points else 0
        self.chart.set(tuple((t,v) for t,v in points if t>=latest-60),history.average if history else None)
        self.parts.rows=tuple((s.get('label','Dosya'),s['method'],tuple(min(1,r['received']/r['total']) if r['total'] else None for r in s['rows'])) for s in streams)
        self.parts.configure(height=max(44,len(streams)*48));self.parts.draw();self.ring.set(ratio)
        texts=dict(url=record['url'],path=record['filepath'],state=state,total=format_bytes(total) if total else 'Bilinmiyor',
            received=f'{format_bytes(received)}  ({ratio*100:.1f}%)' if ratio is not None else format_bytes(received),
            speed=format_speed(active.current_speed) if active and state=='İndiriliyor' else '—',eta=format_eta(active.eta) if active and state=='İndiriliyor' else '—',
            resume='Desteklenir' if task and task.supports_ranges else 'Video motoru' if video else 'Hayır',method=method,
            connections=count+(' aktif bağlantı' if measured else '')+(' · Gözlenen en çok: '+str(peak) if peak else ''),
            average='Ortalama '+format_speed(history.average)+' · En yüksek '+format_speed(max((v for _,v in points),default=0)) if history else 'Gerçek aktarım örnekleri bekleniyor…',
            peak=format_speed(max((v for _,v in points),default=0)),active_time=f'{history.active_seconds:.0f} sn' if history else '—')
        for key,value in texts.items():self.values[key].set(value);self.display[key].set(number(app,value) if key in ('total','received','speed','average') else value)
        self.snapshot=dict(record=record,state=state,progress=ratio,total=total,received=received,streams=streams)
        return self.snapshot


class DownloadDetailDialog(AppWindow):
    def __init__(self,parent,record):
        self.download_id=record['id'];self._timer=None
        super().__init__(parent,'İndirme ayrıntıları',880,780)
        self.minsize(660,min(420,self.winfo_screenheight()-100));self.transient(parent)
        # A05 header: file tile, name over "site · quality", status badge before ×.
        top=self.title_label.master;self.title_label.pack_forget()
        FileTile(top,Path(record['filename']).suffix.lstrip('.') or 'FILE',file_kind(record),self.p,size=44).pack(side='left',padx=(0,14))
        self.status_badge=StatusBadge(top,record['status'],self.p);self.status_badge.pack(side='right',padx=(0,12))
        text=tk.Frame(top,bg=self.p['dialog']);text.pack(side='left',fill='x',expand=True)
        name=label(text,record['filename'],palette=self.p,size=16,weight='Bold');name.max_width=560;name.pack(anchor='w')
        label(text,subtitle(record),palette=self.p,size=12,muted=True).pack(anchor='w',pady=(2,0))
        self.content=TransferContent(self.body,parent,self.download_id);self.content.pack(fill='both',expand=True)
        self.values=self.content.values;self.auto_close=tk.BooleanVar(self,False)
        CheckBox(self.actionbar,'Bitince bu pencereyi kapat',self.auto_close,palette=self.p).pack(side='left')
        self.pause_button=action(self.actionbar,'Duraklat',self.pause_resume,self.p,'primary')
        self.cancel_button=action(self.actionbar,'İptal et',self.cancel,self.p,'danger_ghost')
        self.update_values()

    def pause_resume(self):
        snapshot=self.content.refresh()
        if snapshot and snapshot['state'] in ('İndiriliyor','Bekliyor'):self.parent.pause_download(self.download_id)
        else:self.parent.resume_download(self.download_id)

    def update_values(self):
        snapshot=self.content.refresh()
        if not snapshot:return self.close()
        state=snapshot['state'];pct=snapshot['progress'];self.status_badge.set(state)
        self.title(('—' if pct is None else f'{pct:.0%}')+' · '+snapshot['record']['filename'])
        self.cancel_button.configure(text='Kapat' if state=='Tamamlandı' else 'İptal et',command=self.close if state=='Tamamlandı' else self.cancel)
        self.pause_button.configure(text='Duraklat' if state in ('İndiriliyor','Bekliyor') else 'Devam et',state='disabled' if state in ('Tamamlandı','Birleştiriliyor','Dönüştürülüyor') else 'normal')
        if state=='Tamamlandı' and self.auto_close.get():return self.close()
        self._timer=self.later(500,self.update_values)

    def close(self):self.parent.detail_windows.pop(self.download_id,None);self.destroy()
    def cancel(self):self.parent.cancel_download(self.download_id);self.close()
