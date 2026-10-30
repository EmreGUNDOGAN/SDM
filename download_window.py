"""A05 transfer content reused by a separate window and the Odak drawer."""
from pathlib import Path
import tkinter as tk
import os
from ui_dialog import AppWindow,AutoCard,label,action
from ui_controls import CheckBox
from ui_indicators import ProgressRing,SpeedChart,PartMap,FileTile,StatusBadge
from theme_widgets import Button
from ui_tokens import SIZES,YORUNGE_MONO_FAMILY
from ui_surface import TextLabel
from utils import format_bytes,format_speed,format_eta
from atlas_view import number,file_kind,subtitle


class TransferContent(tk.Frame):
    def __init__(self,master,parent,did):
        super().__init__(master,bg=parent.palette['canvas']);self.parent=parent;self.did=did;self.p=parent.palette
        keys=('url','state','total','received','speed','eta','resume','method','connections','path','average','peak','active_time')
        self.values={key:tk.StringVar(self,'') for key in keys};self.display={key:tk.StringVar(self,'') for key in keys}
        self.pano=self.p.get('design')=='pano';self.orbit=self.p.get('design')=='yorunge'
        # Yörünge F05 keeps Pano's P05 grid; it adds mono captions and stripe metric boxes.
        self.panels=self.pano or self.orbit
        top=tk.Frame(self,bg=self.p['canvas']);top.pack(fill='x',pady=(16,0))
        left=AutoCard(top,self.p);self.progress_card=left
        if self.panels:self.caption(left.content,'İLERLEME').pack(anchor='w')
        else:left.pack_configure(side='left',fill='both',expand=True,padx=(24,8))
        self.ring=ProgressRing(left.content,self.p,value=None,size=160 if self.orbit else None)
        # Pano stretches its horizontal bar; Yörünge's ring stays a circle.
        if self.orbit:self.ring.pack(pady=(8,0))
        else:self.ring.pack(fill='x') if self.panels else self.ring.pack(side='left',padx=(0,12))
        if self.panels:
            if self.pano:self.ring.configure(height=115)
            self.amount=tk.StringVar(self,'—');self.active_connections=tk.StringVar(self,'—')
            self.value(left.content,self.amount,12,muted=True).pack(anchor='w' if self.pano else 'center',pady=(0,10))
        summary=tk.Frame(left.content,bg=self.p['card']);summary.pack(fill='x') if self.panels else summary.pack(side='left',fill='x',expand=True)
        fields=(('eta','Kalan süre'),('connections','Bağlantı')) if self.panels else (('received','İndirilen'),('total','Toplam'),('eta','Kalan süre'))
        for key,title in fields:
            content=summary
            if self.panels:
                well=self.metric(summary,self.p['accent']) if self.orbit else AutoCard(summary,dict(self.p,card=self.p['well'],line=self.p['well']),padding=12)
                if self.pano:well.radius=14
                well.pack_configure(side='left',fill='both',expand=True,padx=(0,4) if key=='eta' else (4,0),pady=0);content=well.content
            if self.orbit:self.caption(content,title,mark=False).pack(anchor='w',pady=(4,2))
            else:label(content,title,palette=self.p,size=12,muted=True).pack(anchor='w',pady=(4,2))
            variable=self.active_connections if self.panels and key=='connections' else self.display[key]
            self.value(content,variable,14,'SemiBold').pack(anchor='w')
        right=AutoCard(top,self.p);self.speed_card=right
        if not self.panels:right.pack_configure(side='left',fill='both',expand=True,padx=(8,24))
        if self.orbit:right.brackets=False;self.caption(right.content,'HIZ · SON 60 SN').pack(anchor='w')
        else:label(right.content,'Aktarım hızı',palette=self.p,size=12,muted=True).pack(anchor='w')
        self.value(right.content,self.display['speed'],24,'Bold').pack(anchor='w')
        self.chart=SpeedChart(right.content,self.p,width=380,height=90 if self.panels else 130,formatter=lambda text:number(parent,text));self.chart.pack(fill='x')
        self.metric_cards=[]
        if self.panels:
            self.mean=tk.StringVar(self,'—');self.highest=tk.StringVar(self,'—')
            for title,variable,stripe in (('Ortalama',self.mean,'violet'),('En yüksek',self.highest,'success')):
                card=self.metric(top,self.p.get(stripe,self.p['accent'])) if self.orbit else AutoCard(top,self.p)
                if self.orbit:self.caption(card.content,title,mark=False).pack(anchor='w')
                else:label(card.content,title,palette=self.p,size=12,muted=True).pack(anchor='w')
                self.value(card.content,variable,18,'Bold').pack(anchor='w',pady=(6,0));self.metric_cards.append(card)
            for card in (left,right,*self.metric_cards):
                card.pack_forget()
                if self.pano:card.radius=22
            top.bind('<Configure>',self.arrange_pano)
        else:
            average=label(right.content,variable=self.display['average'],palette=self.p,size=12,muted=True);average.pack(anchor='w')
            # Ellipsize to the card instead of running past its right edge.
            right.content.bind('<Configure>',lambda e:(setattr(average,'max_width',max(40,e.width-4)),average.draw()),add='+')
            top.bind('<Configure>',lambda e:self.arrange_cards(e,left,right))
        parts=AutoCard(self,self.p)
        if self.pano:parts.radius=22
        if self.orbit:parts.brackets=False;self.caption(parts.content,'PARÇA HARİTASI').pack(anchor='w')
        else:label(parts.content,'Parça haritası',palette=self.p,weight='SemiBold').pack(anchor='w')
        label(parts.content,variable=self.display['connections'],palette=self.p,size=12,muted=True).pack(anchor='w',pady=6)
        self.parts=PartMap(parts.content,self.p,rows=(),height=80);self.parts.pack(fill='x')
        technical=AutoCard(self,self.p);self.technical_card=technical
        if self.pano:technical.radius=22
        if self.orbit:technical.brackets=False
        # A05: one label column, equal row heights and hairlines; values used to
        # start right after each label, so every row began at a different x.
        for index,(key,title) in enumerate((('url','Adres'),('path','Kayıt yeri'),('method','Yöntem'),('resume','Sürdürme'))):
            if index:tk.Frame(technical.content,bg=self.p['line_soft'],height=1).pack(fill='x')
            row=tk.Frame(technical.content,bg=self.p['card'],height=44);row.pack(fill='x');row.pack_propagate(False)
            column=tk.Frame(row,bg=self.p['card'],width=140,height=44);column.pack(side='left');column.pack_propagate(False)
            if self.orbit:self.caption(column,title,mark=False,size=11).pack(side='left')
            else:label(column,title,palette=self.p,muted=True).pack(side='left')
            button=None
            if key=='url':button=Button(row,'Kopyala',self.copy_url,palette=self.p,kind='soft',height=SIZES['small_button'])
            if key=='path':button=Button(row,'Klasörü aç',self.open_folder,palette=self.p,kind='soft',height=SIZES['small_button'])
            if button:button.pack(side='right')
            item=label(row,variable=self.display[key],palette=self.p);item.max_width=520;item.pack(side='left')
            if self.panels:
                row.bind('<Configure>',lambda event,item=item,button=button:(setattr(item,'max_width',max(1,event.width-140-(button.winfo_reqwidth()+8 if button else 0))),item.draw()),add='+')
        self.snapshot=None

    def caption(self,parent,text,mark=True,size=10):
        """Small heading: Pano's muted caps; Yörünge's mono '// TEXT'."""
        if not self.orbit:return label(parent,text.upper(),palette=self.p,size=12,weight='SemiBold',muted=True)
        text=text.replace('i','İ').replace('ı','I').upper()
        return TextLabel(parent,('// ' if mark else '')+text,size=size,fg=self.p['muted'],family=YORUNGE_MONO_FAMILY)

    def value(self,parent,variable,size,weight='Regular',muted=False):
        if not self.orbit:return label(parent,variable=variable,palette=self.p,size=size,weight=weight,muted=muted)
        return TextLabel(parent,textvariable=variable,size=size,weight=weight,fg=self.p['muted'] if muted else self.p['text'],family=YORUNGE_MONO_FAMILY)

    def metric(self,parent,stripe):
        """Yörünge ölçü kutusu: plain panel with a coloured left stripe."""
        card=AutoCard(parent,self.p,padding=12);card.brackets=False;card.stripe=stripe;return card

    def arrange_pano(self,event):
        if event.widget is not self.progress_card.master:return
        top=event.widget;wide=event.width>=800
        for column in range(4):top.columnconfigure(column,weight=1 if wide or column<2 else 0,uniform='detail' if wide or column<2 else '')
        left,right=self.progress_card,self.speed_card
        left.grid(row=0,column=0,rowspan=2 if wide else 1,columnspan=2,sticky='nsew',padx=(24,8) if wide else 24,pady=(0,16))
        right.grid(row=0 if wide else 1,column=2 if wide else 0,columnspan=2,sticky='nsew',padx=(8,24) if wide else 24,pady=(0,16))
        for index,card in enumerate(self.metric_cards):
            card.grid(row=1 if wide else 2,column=2+index if wide else index,sticky='nsew',padx=(8,16) if wide and index==0 else (0,24) if wide else (24,8) if index==0 else (8,24),pady=(0,16))

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
        if self.panels:
            self.mean.set(number(app,format_speed(history.average)) if history else '—');self.highest.set(number(app,texts['peak']) if points else '—')
            self.amount.set(number(app,format_bytes(received)+' / '+(format_bytes(total) if total else 'Bilinmiyor')))
            self.active_connections.set(count)
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
        description=label(text,subtitle(record),palette=self.p,size=12,muted=True);description.pack(anchor='w',pady=(2,0))
        if self.p.get('design') in ('pano','yorunge'):
            def fit_header(event):
                for item in (name,description):item.max_width=event.width;item.draw()
            text.bind('<Configure>',fit_header)
        self.content=TransferContent(self.body,parent,self.download_id);self.content.pack(fill='both',expand=True)
        self.values=self.content.values;self.auto_close=tk.BooleanVar(self,False)
        CheckBox(self.actionbar,'Bitince kapat' if self.p.get('design')=='yorunge' else 'Bitince bu pencereyi kapat',self.auto_close,palette=self.p).pack(side='left')
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
