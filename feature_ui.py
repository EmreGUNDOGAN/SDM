"""Small Tk views; all expensive operations run outside the UI thread."""
from collections import deque
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from ui_messages import messagebox
import threading
import ttkbootstrap as tb
from utils import format_speed,format_bytes,format_eta
from ui_dialog import AppWindow

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



class ToolsDialog(AppWindow):
    def __init__(self,parent):
        super().__init__(parent,'Araçlar',900,760)
        from feature_windows import build_tools
        build_tools(self,parent)
    def update_mode(self):
        for name,button in self.mode_buttons.items():button.selected=name==self.mode.get();button.draw()
        if self.mode.get() in ('Bağlantı kontrolü','Klasörü düzenleme','Altyazı indirme'):self.list.pack(fill='both',expand=True)
        else:self.list.pack_forget()
        if self.mode.get()=='Video / ses kesme':self.cut_fields.pack(fill='x')
        else:self.cut_fields.pack_forget()
        if self.mode.get() in ('Biçim dönüştürme','Video / ses kesme'):
            self.format_host.pack(fill='x',pady=12)
            if self.format.get() not in ('mp4','mkv','mp3','m4a','wav'):self.format.set('mp4')
        else:self.format_host.pack_forget()
        self.run_button.configure(command=self.run,text={'Biçim dönüştürme':'Dönüştür','Video / ses kesme':'Kes','Bağlantı kontrolü':'Kontrol et','Klasörü düzenleme':'Önizle ve taşı','Altyazı indirme':'Altyazıyı indir'}[self.mode.get()])
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
        from ui_controls import Select
        from ui_dialog import label
        self.finished('Dil ve altyazı biçimini seç.')
        for child in self.subtitle_host.winfo_children():child.destroy()
        if not choices:return self.finished('Bu videoda erişilebilir altyazı bulunamadı.')
        labels={language+(' (otomatik)' if automatic else ' (yayıncı)'):(language,automatic) for language,automatic in choices}
        selected=tk.StringVar(self,next(iter(labels)))
        output=tk.StringVar(self,fmt if fmt in ('srt','vtt') else 'srt')
        Select(self.subtitle_host,labels.keys(),selected,palette=self.p,width=260).pack(fill='x',pady=8)
        Select(self.subtitle_host,{'srt':'SRT','vtt':'VTT'},output,palette=self.p,width=120).pack(anchor='w')
        def download():
            language,automatic=labels[selected.get()];extension=output.get()
            target_folder=self.output.get().strip() or folder
            self.busy=True;self.run_button.configure(state='disabled');self.status.set('Altyazı indiriliyor…');self.cancel.clear()
            def work():
                try:
                    from subtitle_tools import download_subtitle
                    paths=download_subtitle(url,target_folder,language,automatic,extension,self.cancel)
                    self.deliver(lambda:self.finished('Altyazı kaydedildi: '+', '.join(str(p) for p in paths)))
                except Exception as error:
                    text=str(error);self.deliver(lambda:self.finished(text))
            threading.Thread(target=work,daemon=True).start()
        self.run_button.configure(command=download)

from feature_windows import SpeedGraph,MiniHUD
