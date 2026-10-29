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
import subprocess
import time


def reveal_file(path):
    """Open Explorer with the finished file selected, as the A14 footer promises."""
    subprocess.Popen(['explorer','/select,',str(path)])


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
        if self.mode.get() in ('Bağlantı kontrolü','Klasörü düzenleme','Altyazı indirme'):self.list.pack(fill='both',expand=True,pady=(12,0))
        else:self.list.pack_forget()
        if self.mode.get()=='Video / ses kesme':self.cut_fields.pack(fill='x')
        else:self.cut_fields.pack_forget()
        media=self.mode.get() in ('Biçim dönüştürme','Video / ses kesme')
        if media:
            # `before` keeps the cards above the output row after a mode switch re-packs them.
            self.format_host.pack(fill='x',pady=(0,12),before=self.output_row)
            if self.format.get() not in ('mp4','mkv','mp3','m4a','wav'):self.format.set('mp4')
        else:self.format_host.pack_forget()
        if media and self.format.get() in ('mp3','m4a'):self.quality_box.pack(side='left',pady=6,padx=(0,12),before=self.output_box)
        else:self.quality_box.pack_forget()
        if media:self.footer_note.pack(side='left')
        else:self.footer_note.pack_forget()
        self.output_step.title.configure(text={'Biçim dönüştürme':'Çıktı biçimi','Video / ses kesme':'Aralık ve biçim'}.get(self.mode.get(),'Çıktı'))
        self.run_button.configure(command=self.run,text={'Biçim dönüştürme':'Dönüştür','Video / ses kesme':'Kes','Bağlantı kontrolü':'Kontrol et','Klasörü düzenleme':'Önizle ve taşı','Altyazı indirme':'Altyazıyı indir'}[self.mode.get()])
        titles={'Biçim dönüştürme':'Biçim dönüştür','Video / ses kesme':'Video / ses kes','Bağlantı kontrolü':'Bağlantı kontrolü','Klasörü düzenleme':'Klasörü düzenle','Altyazı indirme':'Altyazı indir'}
        self.title_label.configure(text=titles[self.mode.get()])
        if not self.description_label.winfo_manager():self.description_label.pack(anchor='w',pady=(6,0))
        self.description_label.configure(text={
            'Video / ses kesme':'Bir aralığı yeni dosyaya kaydet. Kaynak dosya değişmez.',
            'Biçim dönüştürme':'Video veya sesi başka bir biçime çevir. Kaynak dosya değişmez.',
            'Bağlantı kontrolü':'Her satıra bir bağlantı yapıştır; dosyalar indirilmeden sınanır.',
            'Klasörü düzenleme':'Dosyaları türe göre ayır; taşımadan önce önizleme gösterilir.',
            'Altyazı indirme':'Video sayfasının bağlantısını gir; dil ve biçimi sonra seç.'}[self.mode.get()])
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
    def finished(self,text):
        self.busy=False;self.run_button.configure(state='normal');self.stop_button.configure(state='disabled');self.status.set(text)
        self.result_step.title.configure(text='Sonuç')
    def show_progress(self,value):
        """A14 result card: percentage plus position, time left and speed derived from FFmpeg's progress."""
        from atlas_view import number
        self.progress.set(value/100);self.job_percent.configure(text=f'{value:.0f}%')
        elapsed=time.monotonic()-self.job_started;length=self.job_length;parts=[]
        if 0<value<100 and elapsed>1:parts.append('Kalan '+format_eta(elapsed*(100-value)/value))
        if length:
            clock=lambda s:f'{int(s)//3600}:{int(s)//60%60:02d}:{int(s)%60:02d}' if s>=3600 else f'{int(s)//60:02d}:{int(s)%60:02d}'
            done=value/100*length;self.job_time.configure(text=f'{clock(done)} / {clock(length)}')
            if elapsed>1 and done:parts.append('FFmpeg · '+number(self.parent,f'{done/elapsed:.1f}')+'× hız')
        self.job_meta.configure(text=' · '.join(parts))
    def run(self):
        if self.busy:return
        mode=self.mode.get();source=self.input.get().strip();fmt=self.format.get();start=self.start.get();end=self.end.get();urls=self.list.get('1.0','end').splitlines();bitrate=int(self.bitrate.get())
        # Without a chosen folder a media result lands beside its source (A14).
        folder=self.output.get().strip() or (str(Path(source).parent) if source and Path(source).is_file() else self.parent.settings['download_dir'])
        if mode in ('Biçim dönüştürme','Video / ses kesme'):
            if fmt not in ('mp4','mkv','mp3','m4a','wav'):return messagebox.showerror('Biçim','Bir medya çıktı biçimi seç.',parent=self)
            target=filedialog.asksaveasfilename(parent=self,initialdir=folder,initialfile=Path(source).stem+'-SDM.'+fmt,defaultextension='.'+fmt)
            if not target:return
        self.cancel.clear();self.busy=True;self.run_button.configure(state='disabled');self.stop_button.configure(state='normal');self.status.set('İşleniyor…')
        self.progress.set(0);self.job_started=time.monotonic();self.job_length=None
        for widget in (self.job_name,self.job_percent,self.job_time,self.job_meta):widget.configure(text='')
        if mode in ('Biçim dönüştürme','Video / ses kesme'):
            from file_tools import seconds
            self.job_name.configure(text=Path(target).name)
            self.result_step.title.configure(text='Kesiliyor' if mode=='Video / ses kesme' else 'Dönüştürülüyor')
            try:self.job_length=seconds(end)-seconds(start) if mode=='Video / ses kesme' else self.duration
            except ValueError:pass
        def work():
            try:
                if mode in ('Biçim dönüştürme','Video / ses kesme'):
                    from file_tools import process_media
                    result=process_media(source,target,'cut' if mode=='Video / ses kesme' else 'convert',start,end,self.cancel,
                                         lambda p:self.deliver(lambda:self.show_progress(p)),bitrate=bitrate)
                    self.deliver(lambda:(self.finished('Tamamlandı: '+str(result)),reveal_file(result)))
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
            self.busy=True;self.run_button.configure(state='disabled');self.stop_button.configure(state='normal');self.cancel.clear()
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
            self.busy=True;self.run_button.configure(state='disabled');self.stop_button.configure(state='normal');self.status.set('Altyazı indiriliyor…');self.cancel.clear()
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
