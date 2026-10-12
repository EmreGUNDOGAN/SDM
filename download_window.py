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
        self.geometry('820x650')
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
            ('resume', 'Sürdürülebilir'), ('path', 'Kayıt yeri')]):
            tb.Label(info, text=label, foreground='#5b6570').grid(row=row, column=0, sticky='w', padx=(0,24), pady=6)
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
        tb.Button(actions,text='İptal',bootstyle='light',command=lambda:parent.cancel_download(self.download_id)).pack(side='right')
        self.pause_button = tb.Button(actions,text='Duraklat',bootstyle='light',command=self.pause_resume)
        self.pause_button.pack(side='right',padx=8)
        self.details = tb.Frame(content)
        self.details.pack(fill='both',expand=True)
        tb.Separator(self.details).pack(fill='x',pady=(0,12))
        self.detail_label = tb.Label(self.details,text='Bağlantılara göre başlangıç konumları ve ilerleme',anchor='center',foreground='#647080')
        self.detail_label.pack(fill='x',pady=(0,12))
        self.segment_canvas = tk.Canvas(self.details,height=12,bg='#e8edf2',highlightthickness=0)
        self.segment_canvas.pack(fill='x',pady=(0,12))
        self.table = tb.Treeview(self.details,columns=('index','received','start','state'),show='headings',height=7)
        for column,label,width in [('index','N.',45),('received','İndirilen',140),('start','Başlangıç',140),('state','Bilgi',220)]:
            self.table.heading(column,text=label)
            self.table.column(column,width=width,anchor='w')
        self.table.pack(fill='both',expand=True)
        self.update_values()

    def toggle_details(self):
        visible = bool(self.details.winfo_manager())
        if visible:
            self.details.pack_forget()
            self.geometry('820x425')
        else:
            self.details.pack(fill='both',expand=True)
            self.geometry('820x650')
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
        self.title(f'{percent:.0f}% · {record["filename"]}')
        texts = {'url':record['url'],'state':state,'total':format_bytes(total) if total else 'Bilinmiyor',
                 'received':f'{format_bytes(received)}  ({percent:.1f}%)',
                 'speed':format_speed(active.current_speed) if active and state=='İndiriliyor' else '—',
                 'eta':format_eta(active.eta) if active and state=='İndiriliyor' else '—',
                 'resume':'Evet' if task and task.supports_ranges else ('Video motoru' if video else 'Hayır'),
                 'path':record['filepath']}
        for key,value in texts.items():
            self.values[key].set(value)
        self.progress['value'] = percent
        self.pause_button.configure(text='Duraklat' if state in ('İndiriliyor','Bekliyor') else 'Devam Et',
                                    state='disabled' if state in ('Tamamlandı','Birleştiriliyor','Dönüştürülüyor') else 'normal')
        self.segment_canvas.delete('all')
        self.table.delete(*self.table.get_children())
        if task and task.segments:
            width = max(1,self.segment_canvas.winfo_width())
            for segment in task.segments:
                x = segment.index * width/len(task.segments)
                ratio = min(1,segment.downloaded_bytes/segment.total_bytes) if segment.total_bytes else 0
                self.segment_canvas.create_rectangle(x,0,x+width/len(task.segments)*ratio,12,fill='#3478f4',outline='')
                self.table.insert('', 'end', values=(segment.index+1,format_bytes(segment.downloaded_bytes),
                                  format_bytes(segment.start_byte),segment.status))
        elif video:
            self.detail_label.configure(text='Video: geçerli akışın ilerlemesi · Ses ve görüntü sonunda birleştirilir')
            self.table.insert('','end',values=('yt-dlp',format_bytes(received),'—',state))
        if state=='Tamamlandı' and self.auto_close.get():
            self.close()
            return
        self._timer = self.after(500,self.update_values)

    def close(self):
        if self._timer:
            self.after_cancel(self._timer)
        self.parent.detail_windows.pop(self.download_id,None)
        self.destroy()
