from pathlib import Path
import tkinter as tk
import ttkbootstrap as tb
from utils import format_bytes, format_speed, format_eta


class DownloadDetailDialog(tb.Toplevel):
    def __init__(self, parent, record):
        super().__init__(parent)
        self.parent = parent
        self.download_id = record['id']
        self.title(record['filename'])
        self.geometry('860x740')
        self.minsize(660, 420)
        self.transient(parent)
        self._timer = None
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.auto_close = tk.BooleanVar(value=False)
        self.values = {}
        content = tb.Frame(self, padding=22)
        content.pack(fill='both', expand=True)
        info = tb.Frame(content)
        info.pack(fill='x')
        info.columnconfigure(1, weight=1)
        for row, (key, label) in enumerate([
            ('url', 'URL'), ('state', 'Durum'), ('total', 'Dosya boyutu'),
            ('received', 'İndirilen'), ('speed', 'Aktarım hızı'), ('eta', 'Kalan süre'),
            ('resume', 'Sürdürülebilir'), ('method','İndirme yöntemi'),('connections','Aktif bağlantı / aktarım'), ('path', 'Kayıt yeri')]):
            tb.Label(info, text=label).grid(row=row, column=0, sticky='w', padx=(0,24), pady=6)
            variable = tk.StringVar()
            self.values[key] = variable
            if key in ('url', 'path'):
                tb.Entry(info, textvariable=variable, state='readonly').grid(row=row,column=1,sticky='ew',pady=6)
            else:
                tb.Label(info, textvariable=variable).grid(row=row,column=1,sticky='w',pady=6)
        self.progress = tb.Progressbar(content, maximum=100, bootstyle='primary')
        self.progress.pack(fill='x', pady=(20,22))
        actions = tb.Frame(content)
        actions.pack(fill='x', pady=(0,18))
        self.toggle = tb.Button(actions,text='≪ Detayları Gizle',command=self.toggle_details,bootstyle='light')
        self.toggle.pack(side='left')
        tb.Checkbutton(actions,text='Tamamlanınca kapat',variable=self.auto_close).pack(side='left',padx=15)
        self.cancel_button = tb.Button(actions,text='İptal et',bootstyle='secondary-outline',command=self.cancel)
        self.cancel_button.pack(side='right')
        self.pause_button = tb.Button(actions,text='Duraklat',bootstyle='light',command=self.pause_resume)
        self.pause_button.pack(side='right',padx=8)
        tb.Button(actions,text='Hız grafiği',bootstyle='secondary-outline',command=lambda:parent.show_speed_graph(self.download_id)).pack(side='right',padx=8)
        self.details = tb.Frame(content)
        self.details.pack(fill='both',expand=True)
        tb.Separator(self.details).pack(fill='x',pady=(0,12))
        self.detail_label = tb.Label(self.details,text='Bağlantılara göre başlangıç konumları ve ilerleme',anchor='center')
        self.detail_label.pack(fill='x',pady=(0,12))
        self.segment_canvas = tk.Canvas(self.details,height=12,bg='#e8edf2',highlightthickness=0)
        self.segment_canvas.pack(fill='x',pady=(0,12))
        table_frame=tb.Frame(self.details)
        table_frame.pack(fill='both',expand=True)
        self.table = tb.Treeview(table_frame,columns=('index','received','start','percent','state'),show='headings',height=7)
        for column,label,width in [('index','Akış / Parça',140),('received','İndirilen',110),('start','Başlangıç',110),('percent','İlerleme',90),('state','Bilgi',190)]:
            self.table.heading(column,text=label)
            self.table.column(column,width=width,anchor='w')
        self.table.pack(side='left',fill='both',expand=True)
        scroll=tb.Scrollbar(table_frame,orient='vertical',command=self.table.yview);scroll.pack(side='right',fill='y');self.table.configure(yscrollcommand=scroll.set)
        self.update_values()

    def toggle_details(self):
        visible = bool(self.details.winfo_manager())
        if visible:
            self.details.pack_forget()
            self.geometry('860x510')
        else:
            self.details.pack(fill='both',expand=True)
            self.geometry('860x740')
        self.toggle.configure(text='≫ Detayları Göster' if visible else '≪ Detayları Gizle')

    def pause_resume(self):
        record = self.parent.db.get_download(self.download_id)
        if record and record['status'] in ('İndiriliyor','Bekliyor'):
            self.parent.pause_download(self.download_id)
        else:
            self.parent.resume_download(self.download_id)

    def update_values(self):
        record = self.parent.db.get_download(self.download_id)
        if not record:
            self.close()
            return
        task = self.parent.engine.get_task(self.download_id)
        video = self.parent.video_tasks.get(self.download_id)
        active = video or task
        state = active.status if active else record['status']
        total = video.total_bytes if video else (task.filesize if task else record['filesize'])
        received = video.downloaded_bytes if video else (sum(s.downloaded_bytes for s in task.segments) if task else record['downloaded_bytes'])
        percent = min(100, received/total*100) if total else 0
        if state == 'Tamamlandı':
            percent = 100
            total, received = record['filesize'], record['downloaded_bytes']
        streams=video.transfer_details.snapshot() if video else []
        if task:
            direct=task.transfer_snapshot();streams=[dict(direct,label='Dosya',reason='',observed=bool(direct['rows']))]
        if streams:
            method=' / '.join(dict.fromkeys(s['method'] for s in streams))
            measured=all(s.get('active_count') is not None for s in streams)
            count=str(sum(s['active_count'] for s in streams)) if measured else 'Henüz ölçülmedi'
            peak=max((s.get('peak',0) for s in streams),default=0)
            count+=f' · Gözlenen en çok: {peak}' if peak else ''
        else:method=video.unobserved_method if video else 'Hazırlanıyor · henüz ölçüm yok';count='Henüz ölçülmedi'
        self.title(f'{percent:.0f}% · {record["filename"]}')
        texts = {'url':record['url'],'state':state,'total':format_bytes(total) if total else 'Bilinmiyor',
                 'received':f'{format_bytes(received)}  ({percent:.1f}%)',
                 'speed':format_speed(active.current_speed) if active and state=='İndiriliyor' else '—',
                 'eta':format_eta(active.eta) if active and state=='İndiriliyor' else '—',
                 'resume':'Evet' if task and task.supports_ranges else ('Video motoru' if video else 'Hayır'),
                 'method':method,'connections':count,
                 'path':record['filepath']}
        for key,value in texts.items():
            self.values[key].set(value)
        self.progress['value'] = percent
        self.cancel_button.configure(text='Kapat' if state=='Tamamlandı' else 'İptal et',command=self.close if state=='Tamamlandı' else self.cancel)
        self.pause_button.configure(text='Duraklat' if state in ('İndiriliyor','Bekliyor') else 'Devam Et',
                                    state='disabled' if state in ('Tamamlandı','Birleştiriliyor','Dönüştürülüyor') else 'normal')
        self.segment_canvas.delete('all')
        self.table.delete(*self.table.get_children())
        rows=[(s,row) for s in streams for row in s['rows']]
        reasons=' '.join(dict.fromkeys(s.get('reason','') for s in streams if s.get('reason')))
        self.detail_label.configure(text=reasons or ('Gerçek parça ölçümleri · HLS/DASH için son parçalar' if video else 'Bağlantılara göre başlangıç konumları ve ilerleme'),wraplength=780)
        width=max(1,self.segment_canvas.winfo_width())
        for i,(stream,row) in enumerate(rows):
            ratio=min(1,row['received']/row['total']) if row['total'] else None
            if ratio is not None:self.segment_canvas.create_rectangle(i*width/len(rows),0,(i+ratio)*width/len(rows),12,fill='#3478f4',outline='')
            label=f"{stream['label']} #{row['index']}"
            self.table.insert('','end',values=(label,format_bytes(row['received']),format_bytes(row['start']) if row['start'] is not None else '—',f'{ratio*100:.1f}%' if ratio is not None else 'Bilinmiyor',row['state']))
        if state=='Tamamlandı' and self.auto_close.get():
            self.close()
            return
        self._timer = self.after(500,self.update_values)

    def close(self):
        if self._timer:
            self.after_cancel(self._timer)
        self.parent.detail_windows.pop(self.download_id,None)
        self.destroy()

    def cancel(self):
        self.parent.cancel_download(self.download_id)
        self.close()
