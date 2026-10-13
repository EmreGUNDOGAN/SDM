"""Small Tk views; all expensive operations run outside the UI thread."""
from collections import deque
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog,messagebox
import threading
import ttkbootstrap as tb
from utils import format_speed,format_bytes,format_eta

class SpeedHistory:
    def __init__(self):self.points=deque(maxlen=1200);self.last=None;self.bytes=0;self.active_seconds=0
    def sample(self,timestamp,received,speed,active):
        if self.last:
            previous,old_received,old_active=self.last
            elapsed=timestamp-previous
            if active and old_active and 0<elapsed<3:
                self.bytes+=max(0,received-old_received);self.active_seconds+=elapsed
        self.points.append((timestamp,max(0,speed) if active else 0));self.last=(timestamp,received,active)
    @property
    def average(self):return self.bytes/self.active_seconds if self.active_seconds else 0

class SpeedGraph(tb.Toplevel):
    def __init__(self,parent,did):
        super().__init__(parent);self.parent=parent;self.did=did;self.title('SDM · Hız grafiği');self.geometry('700x340')
        self.canvas=tk.Canvas(self,bg=parent.palette['panel'],highlightthickness=0);self.canvas.pack(fill='both',expand=True,padx=20,pady=20)
        self.label=tb.Label(self);self.label.pack(pady=(0,15));self.tick()
    def tick(self):
        if not self.winfo_exists():return
        history=self.parent.speed_history.get(self.did)
        self.canvas.delete('all')
        if history and len(history.points)>1:
            points=list(history.points)[-300:];width=max(1,self.canvas.winfo_width()-30);height=max(1,self.canvas.winfo_height()-35)
            peak=max(1,max(value for _,value in points));first=points[0][0];span=max(1,points[-1][0]-first)
            coords=[c for stamp,value in points for c in (15+(stamp-first)/span*width,15+height-value/peak*height)]
            self.canvas.create_line(*coords,fill='#3478f4',width=2)
            self.canvas.create_text(15,8,text=format_speed(peak),fill=self.parent.palette['text'],anchor='nw')
            self.label.configure(text=f'Aktif aktarım ortalaması: {format_speed(history.average)} · Son 5 dakika · Duraklamalarda hız 0')
        else:self.label.configure(text='Gerçek aktarım örnekleri bekleniyor…')
        self.after(1000,self.tick)

class MiniHUD(tb.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.title('SDM · Canlı indirmeler');self.geometry('350x170');self.attributes('-topmost',True)
        self.label=tb.Label(self,padding=16,justify='left',font=('Segoe UI',11));self.label.pack(fill='both',expand=True)
        tb.Button(self,text='SDM’yi göster',command=self.show_main).pack(pady=(0,10))
        self.protocol('WM_DELETE_WINDOW',self.close);self.tick()
    def show_main(self):self.parent.deiconify();self.parent.lift()
    def close(self):self.parent._mini_hud=None;self.destroy()
    def tick(self):
        if not self.winfo_exists():return
        records=[r for r in self.parent.db.get_all_downloads() if r['status'] in ('İndiriliyor','Birleştiriliyor','Dönüştürülüyor')]
        speed=self.parent.engine.get_total_speed()+sum(v.current_speed for v in list(self.parent.video_tasks.values()) if v.status=='İndiriliyor')
        total=sum(r['filesize'] for r in records);received=sum(r['downloaded_bytes'] for r in records)
        percent=f'{min(100,received/total*100):.1f}%' if total and all(r['filesize'] for r in records) else 'Boyut bilinmiyor'
        eta=format_eta(max(0,total-received)/speed) if speed and total and all(r['filesize'] for r in records) else '—'
        self.label.configure(text=f'{len(records)} aktif indirme   ·   {format_speed(speed)}\n{percent}   ·   Kalan süre: {eta}\nİndirilen: {format_bytes(received)}')
        self.after(1000,self.tick)

class ToolsDialog(tb.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.title('SDM · İndirme araçları');self.geometry('860x720');self.minsize(800,650);self.cancel=threading.Event();self.busy=False
        frame=tb.Frame(self,padding=20);frame.pack(fill='both',expand=True)
        self.mode=tk.StringVar(value='Biçim dönüştürme')
        from theme_widgets import Button
        navigation=tk.Frame(frame,bg=parent.palette['bg']);navigation.pack(fill='x',pady=(0,16))
        self.mode_buttons={}
        for name,short in [('Biçim dönüştürme','Dönüştürme'),('Video / ses kesme','Kesme'),('Bağlantı kontrolü','Bağlantılar'),('Klasörü düzenleme','Klasörler'),('Altyazı indirme','Altyazı')]:
            button=Button(navigation,short,lambda value=name:self.mode.set(value),palette=parent.palette,quiet=True)
            button.pack(side='left',padx=3);self.mode_buttons[name]=button
        self.input=tk.StringVar();self.output=tk.StringVar();self.start=tk.StringVar(value='00:00');self.end=tk.StringVar(value='00:30');self.format=tk.StringVar(value='mp4')
        for label,var in [('Dosya / klasör / video bağlantısı',self.input),('Çıktı klasörü',self.output)]:
            tb.Label(frame,text=label).pack(anchor='w',pady=(12,4));tb.Entry(frame,textvariable=var).pack(fill='x')
        browse=tb.Frame(frame);browse.pack(fill='x',pady=8)
        for label,command in [('Dosya seç',self.browse_file),('Klasör seç',self.browse_folder),('Çıktı klasörü seç',self.browse_output)]:tb.Button(browse,text=label,command=command,bootstyle='secondary-outline').pack(side='left',padx=(0,7))
        row=tb.Frame(frame);row.pack(fill='x');tb.Entry(row,textvariable=self.start,width=12).pack(side='left');tb.Label(row,text=' → ').pack(side='left');tb.Entry(row,textvariable=self.end,width=12).pack(side='left')
        tb.Combobox(row,textvariable=self.format,values=['mp4','mkv','mp3','m4a','wav','srt','vtt'],state='readonly',width=8).pack(side='right')
        self.help_label=tb.Label(frame,text='',wraplength=740);self.help_label.pack(anchor='w',pady=10)
        self.list=tk.Text(frame,height=7,bg=parent.palette['panel'],fg=parent.palette['text'],insertbackground=parent.palette['text']);self.list.pack(fill='both',expand=True)
        self.mode.trace_add('write',lambda *args:self.update_mode())
        self.update_mode()
        self.progress=tb.Progressbar(frame,maximum=100);self.progress.pack(fill='x',pady=8)
        self.status=tk.StringVar(value='');tb.Label(frame,textvariable=self.status,wraplength=610).pack(anchor='w')
        controls=tb.Frame(frame);controls.pack(fill='x',pady=8)
        self.run_button=tb.Button(controls,text='Çalıştır / önizle',command=self.run);self.run_button.pack(side='left')
        tb.Button(controls,text='İşlemi iptal et',command=self.cancel.set,bootstyle='secondary-outline').pack(side='right')
        self.protocol('WM_DELETE_WINDOW',self.close)
        from tkinterdnd2 import DND_FILES
        self.drop_target_register(DND_FILES);self.dnd_bind('<<Drop>>',lambda e:self.input.set(self.tk.splitlist(e.data)[0]))
    def update_mode(self):
        for name,button in self.mode_buttons.items():button.selected=name==self.mode.get();button.draw()
        if self.mode.get()=='Bağlantı kontrolü':self.list.pack(fill='both',expand=True)
        else:self.list.pack_forget()
        self.help_label.configure(text={
            'Video / ses kesme':'İndirilmiş bir medya dosyası seçin. Başlangıç → bitiş aralığı yeni dosyaya kaydedilir; kaynak korunur.',
            'Biçim dönüştürme':'Bir video / ses dosyası seçin ve çıktı biçimini belirleyin. Yeni dosya oluşturulur; kaynak korunur.',
            'Bağlantı kontrolü':'Aşağıya her satıra bir http/https bağlantısı yapıştırın. Dosyalar indirilmeden erişim kontrol edilir.',
            'Klasörü düzenleme':'Bir klasör seçin. Taşınacak dosyalar önce önizlemede gösterilir; onayınızdan sonra taşınır.',
            'Altyazı indirme':'Üst alana video sayfasının bağlantısını girin. İnceleme sonrası altyazı dili ve biçimini seçebilirsiniz.'}[self.mode.get()])
    def close(self):
        if self.busy:self.cancel.set()
        self.destroy()
    def browse_file(self):
        value=filedialog.askopenfilename(parent=self)
        if value:self.input.set(value)
    def browse_folder(self):
        value=filedialog.askdirectory(parent=self)
        if value:self.input.set(value)
    def browse_output(self):
        value=filedialog.askdirectory(parent=self)
        if value:self.output.set(value)
    def deliver(self,callback):self.parent.post_ui(lambda:callback() if self.winfo_exists() else None)
    def finished(self,text):self.busy=False;self.run_button.configure(state='normal');self.status.set(text)
    def run(self):
        if self.busy:return
        mode=self.mode.get();source=self.input.get().strip();folder=self.output.get().strip() or self.parent.settings['download_dir'];fmt=self.format.get();start=self.start.get();end=self.end.get();urls=self.list.get('1.0','end').splitlines()
        if mode in ('Biçim dönüştürme','Video / ses kesme'):
            if fmt not in ('mp4','mkv','mp3','m4a','wav'):return messagebox.showerror('Biçim','Bir medya çıktı biçimi seç.',parent=self)
            target=filedialog.asksaveasfilename(parent=self,initialdir=folder,initialfile=Path(source).stem+'-SDM.'+fmt,defaultextension='.'+fmt)
            if not target:return
        self.cancel.clear();self.busy=True;self.run_button.configure(state='disabled');self.status.set('İşleniyor…');self.progress['value']=0
        def work():
            try:
                if mode in ('Biçim dönüştürme','Video / ses kesme'):
                    from file_tools import process_media
                    result=process_media(source,target,'cut' if mode=='Video / ses kesme' else 'convert',start,end,self.cancel,lambda p:self.deliver(lambda:self.progress.configure(value=p)))
                    self.deliver(lambda:self.finished('Tamamlandı: '+str(result)))
                elif mode=='Bağlantı kontrolü':
                    from link_tools import check_links
                    result=check_links(urls,self.cancel);text='\n'.join(f'{state} · {url}' for url,state in result)
                    self.deliver(lambda:(self.list.delete('1.0','end'),self.list.insert('1.0',text),self.finished('Kontrol tamamlandı. Sunucu koşulları daha sonra değişebilir.')))
                elif mode=='Klasörü düzenleme':
                    from file_tools import organization_plan
                    records=self.parent.db.get_all_downloads();excluded=[r['filepath'] for r in records if r['status']!='Tamamlandı']
                    plan=organization_plan(source,excluded);self.deliver(lambda:self.preview_plan(plan))
                else:
                    from subtitle_tools import subtitle_choices
                    choices=subtitle_choices(source);self.deliver(lambda:self.choose_subtitles(source,folder,fmt,choices))
            except Exception as error:
                text=str(error);self.deliver(lambda:self.finished(text))
        threading.Thread(target=work,daemon=True).start()
    def preview_plan(self,plan):
        self.finished(f'{len(plan)} dosya taşınacak.');self.list.delete('1.0','end');self.list.insert('1.0','\n'.join(f'{s.name} → {t.parent.name}/{t.name}' for s,t in plan))
        if plan and messagebox.askyesno('Taşıma önizlemesi',f'{len(plan)} dosyayı gösterilen klasörlere taşıyalım mı?',parent=self):
            # Keep the operation serialized with new download creation; only short renames.
            records=self.parent.db.get_all_downloads();active={Path(r['filepath']).resolve() for r in records if r['status']!='Tamamlandı'}
            if any(s.resolve() in active for s,_ in plan):return self.finished('Aktif dosya bulundu. Önizlemeyi yenile.')
            self.busy=True;self.run_button.configure(state='disabled');self.cancel.clear()
            def work():
                from file_tools import move_plan
                try:
                    for source,target in plan:
                        if self.cancel.is_set():raise ValueError('Düzenleme durduruldu; taşınan dosyalar yeni klasöründe kaldı.')
                        move_plan([(source,target)])
                        for record in records:
                            if Path(record['filepath']).resolve()==source.resolve():self.parent.db.update_download_metadata(record['id'],target.name,str(target),record['filesize'],record['category'])
                    self.deliver(lambda:self.finished('Dosyalar düzenlendi.'))
                except Exception as error:
                    text=str(error);self.deliver(lambda:self.finished(text))
                self.parent.post_ui(self.parent.refresh_downloads,key='refresh')
            threading.Thread(target=work,daemon=True).start()
    def choose_subtitles(self,url,folder,fmt,choices):
        self.finished('Dil seç.');self.list.delete('1.0','end')
        if not choices:return self.finished('Bu videoda erişilebilir altyazı bulunamadı.')
        window=tb.Toplevel(self);window.title('Altyazı dili');window.geometry('390x240')
        labels={f'{language}'+(' · otomatik' if automatic else ' · yayıncı'): (language,automatic) for language,automatic in choices}
        selected=tk.StringVar(value=next(iter(labels)))
        tb.Combobox(window,textvariable=selected,values=list(labels),state='readonly',width=40).pack(padx=20,pady=30)
        output=tk.StringVar(value=fmt if fmt in ('srt','vtt') else 'srt');tb.Combobox(window,textvariable=output,values=['srt','vtt'],state='readonly').pack()
        def download():
            language,automatic=labels[selected.get()];extension=output.get();window.destroy();self.busy=True;self.run_button.configure(state='disabled');self.status.set('Altyazı indiriliyor…')
            def work():
                try:
                    from subtitle_tools import download_subtitle
                    paths=download_subtitle(url,folder,language,automatic,extension,self.cancel)
                    self.deliver(lambda:self.finished('Altyazı kaydedildi: '+', '.join(str(p) for p in paths)))
                except Exception as error:
                    text=str(error);self.deliver(lambda:self.finished(text))
            threading.Thread(target=work,daemon=True).start()
        tb.Button(window,text='Altyazıyı indir',command=download).pack(pady=20)
