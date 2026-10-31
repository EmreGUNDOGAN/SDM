import hashlib
import json
import os
from pathlib import Path
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from ui_messages import messagebox
import webbrowser
import ttkbootstrap as tb
from utils import load_settings,save_settings,get_unique_filepath
from app_dialogs import CapturePrompt,CompletionDialog,foreground


class AppActions:
    def initialize_drop(self):
        from tkinterdnd2 import TkinterDnD,DND_TEXT,DND_FILES
        TkinterDnD.require(self)
        self.tree.drop_target_register(DND_TEXT,DND_FILES)
        self.tree.dnd_bind('<<Drop>>',self.on_drop)
        if hasattr(self,'data_view'):
            self.data_view.drop_target_register(DND_TEXT,DND_FILES)
            self.data_view.dnd_bind('<<Drop>>',self.on_drop)
        workspace=getattr(self,'_atlas_workspace',None)
        if workspace and workspace.alive:
            for widget in (workspace.empty,workspace.drop_zone):
                widget.drop_target_register(DND_TEXT,DND_FILES)
                widget.dnd_bind('<<Drop>>',self.on_drop)

    def on_drop(self,event):
        from utils import is_valid_url
        values=self.tk.splitlist(event.data)
        urls=[]
        for value in values:
            if is_valid_url(value):urls.append(value)
            elif Path(value).suffix.lower() in ('.url','.txt') and Path(value).is_file() and Path(value).stat().st_size<1024*1024:
                for line in Path(value).read_text(encoding='utf-8-sig',errors='replace').splitlines():
                    line=line.removeprefix('URL=').strip()
                    if is_valid_url(line):urls.append(line)
        if urls:self.open_add_dialog('\n'.join(urls))
        else:self.notify('Sürükle-bırak','Bir indirme bağlantısı veya bağlantılar içeren .url / .txt dosyası bırakın.')
        return event.action

    def initialize_actions(self):
        self._queue_running=False;self._queue_ids=set();self._session_received={};self._session_baselines={}
        self._completed_notified=set();self._update_busy=False;self._shutdown_window=None
        self.engine.external_active_count=lambda:sum(v.status in ('İndiriliyor','Dönüştürülüyor') for v in list(self.video_tasks.values()))
        self.after(1000,self.queue_tick)
        if self.settings.get('update_check_on_start'):self.after(2500,lambda:self.check_updates(True))
        from update_handoff import read_result
        result=read_result()
        if result:
            self.lbl_status_info.configure(text='Güncelleme tamamlandı' if result.get('ok') else 'Güncelleme tamamlanamadı')
            if not result.get('ok'):self.after(1200,lambda:messagebox.showerror('Güncelleme',result.get('message','Kurulum tamamlanamadı'),parent=self))

    def browser_request(self,request,decision):
        self.deiconify()
        if request['kind']=='batch':
            from batch_dialog import BatchDialog
            return BatchDialog(self,'\n'.join(request['urls']))
        if request['kind']=='music':return self.music_request(request)
        prompt=CapturePrompt(self,request,decision)
        if getattr(self,'integration_test',False):self.after(150,lambda:prompt.choose('start'))
        return prompt

    def music_request(self,request):
        """YouTube Music button: MP3s straight into the downloads, Artist/Album layout."""
        import threading
        from pathlib import Path
        from urllib.parse import parse_qs,urlparse
        folder=Path(self.settings['download_dir']);bitrate=request['bitrate']
        if not request['list']:
            self.add_download_from_dialog(request['url'],'YouTube Music.mp3',str(folder/'YouTube Music.mp3'),is_video=True,
                video_quality='Yalnızca Ses (MP3)',audio=dict(bitrate=bitrate,album=True,track=None))
            return self.notify('Müzik eklendi',f'MP3 · {bitrate} kb/sn')
        # Only album lists ("OLAK5uy_…") number the files; a mixed playlist keeps each song's own data.
        album=parse_qs(urlparse(request['url']).query).get('list',[''])[0].startswith('OLAK5uy_')
        def work():
            from dialog_inspection import inspect_url
            from music_album import ALBUM_LIMIT
            try:
                result=inspect_url(request['url'],force_video=True)
                entries=[url for url,_ in result['entries']][:ALBUM_LIMIT] if result['kind']=='playlist' else [request['url']]
                title=result.get('title') or 'YouTube Music'
            except Exception as error:
                return self.post_ui(lambda e=str(error):self.notify('Liste alınamadı',e,tone='error'))
            def apply():
                # The whole list is one row: its songs download one after another.
                from utils import clean_filename
                name=f'{clean_filename(title)} · {len(entries)} parça'
                self.add_download_from_dialog(request['url'],name,str(folder/name),is_video=True,video_quality='Yalnızca Ses (MP3)',
                    audio=dict(bitrate=bitrate,album=True,track=None,entries=entries,numbered=album,folder=str(folder),title=title))
                self.notify('Müzik eklendi',f'{len(entries)} parça tek indirmede · MP3 · {bitrate} kb/sn')
            self.post_ui(apply)
        threading.Thread(target=work,daemon=True).start()

    def toggle_capture(self):
        self.settings['browser_capture']=not self.settings.get('browser_capture',True)
        if self.settings['browser_capture']:self.settings['capture_paused_until']=0
        save_settings(self.settings);self.update_hud()

    def show_queue_menu(self):
        menu=tk.Menu(self,tearoff=0)
        for label,action in [('Kuyruğu başlat',self.start_queue),('Kuyruğu duraklat',self.pause_queue),('Seçilileri kuyruğa ekle',self.queue_selected),('Zamanlama ve kapanma ayarları',self.open_settings_dialog)]:menu.add_command(label=label,command=action)
        menu.tk_popup(self.winfo_pointerx(),self.winfo_pointery())

    def queue_selected(self):
        for did in self._get_selected_ids():
            record=self.db.get_download(did)
            if not record or record['status']=='Tamamlandı':continue
            self.pause_download(did)
            task=self.video_tasks.get(did) or self.engine.get_task(did)
            if task:task.queue_requested=True;task.status='Kuyrukta'
            self.db.update_download_status(did,'Kuyrukta')
        self.refresh_downloads()

    def start_queue(self):
        self._queue_running=True
        self._queue_ids.update(r['id'] for r in self.db.get_all_downloads() if r['status']=='Kuyrukta')
        self.queue_tick_once()

    def pause_queue(self):
        self._queue_running=False
        for did in self._queue_ids:
            record=self.db.get_download(did)
            if record and record['status'] not in ('Tamamlandı','İptal Edildi'):
                self.pause_download(did)
                task=self.video_tasks.get(did) or self.engine.get_task(did)
                if task:task.queue_requested=True;task.status='Kuyrukta'
                self.db.update_download_status(did,'Kuyrukta')
        self.refresh_downloads()

    def queue_tick_once(self):
        records=self.db.get_all_downloads()
        active=self.engine.get_active_count()+sum(v.status in ('İndiriliyor','Dönüştürülüyor') for v in list(self.video_tasks.values()))
        pending=sum(t.status=='Bekliyor' for t in self.engine.tasks.values())
        slots=max(0,self.settings.get('max_simultaneous_downloads',3)-active-pending)
        for did,task in list(self.video_tasks.items()):
            if task.status=='Bekliyor' and slots:
                task.start();slots-=1
        if self._queue_running:
            for record in sorted(records,key=lambda r:r['id']):
                if slots<=0:break
                if record['status']!='Kuyrukta':continue
                self._queue_ids.add(record['id'])
                if self.resume_download(record['id']):slots-=1
            pending_records=[r for r in records if r['id'] in self._queue_ids]
            if self._queue_ids and pending_records and all(r['status']=='Tamamlandı' for r in pending_records):
                self._queue_running=False;self._queue_ids.clear()
                if self.settings.get('shutdown_after_queue'):self.shutdown_countdown()

    def queue_tick(self):
        latest=load_settings()
        for key in ('browser_capture','capture_paused_until','excluded_sites','capture_extensions'):
            self.settings[key]=latest[key]
        scheduled=self.settings.get('scheduled_start','')
        if scheduled:
            try:
                if datetime.now()>=datetime.strptime(scheduled,'%Y-%m-%d %H:%M'):
                    self.settings['scheduled_start']='';save_settings(self.settings);self.start_queue()
            except ValueError:self.lbl_status_info.configure(text='Zamanlama biçimi geçersiz')
        self.queue_tick_once();self.after(1000,self.queue_tick)

    def restart_selected(self):
        ids=self._get_selected_ids()
        if ids and messagebox.askyesno('Sıfırdan indir','Seçilen indirmeler yeni kayıt olarak sıfırdan başlatılsın mı?'):
            for did in ids:
                record=self.db.get_download(did)
                if not record:continue
                self.cancel_download(did)
                options=json.loads(record.get('options_json') or '{}')
                dest=get_unique_filepath(Path(record['filepath']).parent,record['filename'])
                self.add_download_from_dialog(record['url'],dest.name,str(dest),is_video=record['download_type']=='video',
                    video_quality=options.get('quality','En İyi'),selected_height=options.get('height'),connections=record['num_connections'],audio=options.get('audio'))

    def verify_selected(self):
        ids=self._get_selected_ids()
        if not ids:return
        record=self.db.get_download(ids[0])
        if not record or record['status']!='Tamamlandı':return self.notify('SHA-256','Önce indirme tamamlanmalı.')
        self.lbl_status_info.configure(text='SHA-256 hesaplanıyor…')
        def work():
            try:
                digest=hashlib.sha256()
                with open(record['filepath'],'rb') as stream:
                    while chunk:=stream.read(1024*1024):digest.update(chunk)
                self.post_ui(lambda:self.show_hash(record['filename'],digest.hexdigest()))
            except OSError:self.post_ui(lambda:messagebox.showerror('SHA-256','Dosya okunamadı.'))
        threading.Thread(target=work,daemon=True).start()

    def show_hash(self,name,value):
        from tkinter.simpledialog import askstring
        expected=askstring('SHA-256',f'{name}\n\nHesaplanan değer:\n{value}\n\nKarşılaştırmak için beklenen SHA-256 değerini gir:',parent=self)
        if expected:
            match=expected.strip().lower()==value
            if match:self.notify('SHA-256','Dosya özeti eşleşiyor.')
            else:messagebox.showerror('SHA-256','Dosya özeti EŞLEŞMİYOR.',parent=self)
        self.lbl_status_info.configure(text='SHA-256 kontrolü tamamlandı')

    def completed_popup(self,did):
        if did in self._completed_notified:return
        self._completed_notified.add(did)
        record=self.db.get_download(did)
        if record and self.settings.get('completion_popup',True):CompletionDialog(self,record)

    def show_download_error(self,did,error):
        from error_messages import explain_error
        title,description,action=explain_error(error)
        from ui_overlays import MessageDialog
        window=MessageDialog(self,title,description,self.palette,technical=str(error),tone='error')
        def resolve():
            record=self.db.get_download(did)
            if not record:return window.destroy()
            if action=='Kaynak sayfayı aç':webbrowser.open(record['url'])
            elif action=='Başka klasöre indir':
                folder=filedialog.askdirectory(parent=window)
                if not folder:return
                options=json.loads(record.get('options_json') or '{}')
                dest=get_unique_filepath(folder,record['filename'])
                self.add_download_from_dialog(record['url'],dest.name,str(dest),is_video=record['download_type']=='video',video_quality=options.get('quality','En İyi'),selected_height=options.get('height'),audio=options.get('audio'))
            elif action=='Klasörü göster':os.startfile(str(Path(record['filepath']).parent))
            elif action=='Sıfırdan indir':
                dest=get_unique_filepath(Path(record['filepath']).parent,record['filename'])
                self.add_download_from_dialog(record['url'],dest.name,str(dest))
            else:self.resume_download(did)
            window.destroy()
        window.add_action('resolve',action,'primary')
        window.actions['resolve'].configure(command=resolve)
        window.add_action('close','Kapat','ghost');window.show()

    def shutdown_countdown(self):
        if self._shutdown_window:return
        window=tb.Toplevel(self);self._shutdown_window=window;window.title('SDM · Kuyruk tamamlandı');window.geometry('480x200')
        label=tb.Label(window,padding=20);label.pack(fill='x')
        cancelled=[False]
        def cancel():cancelled[0]=True;self._shutdown_window=None;window.destroy()
        window.protocol('WM_DELETE_WINDOW',cancel)
        tb.Button(window,text='Bilgisayarı kapatmayı iptal et',command=cancel).pack(pady=15)
        def tick(remaining):
            if cancelled[0]:return
            label.configure(text=f'Tüm kuyruk tamamlandı. Bilgisayar {remaining} saniye sonra kapanacak.')
            if remaining<=0:
                import subprocess
                subprocess.Popen(['shutdown','/s','/t','0'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));return
            window.after(1000,lambda:tick(remaining-1))
        foreground(window);tick(60)

    def check_updates(self,quiet=False):
        if self._update_busy:return
        self._update_busy=True;self.lbl_status_info.configure(text='GitHub sürümü kontrol ediliyor…')
        def work():
            try:
                from updater import GitHubUpdater
                updater=GitHubUpdater();update=updater.check()
                if update:
                    from update_dialog import attach_release_notes
                    update=attach_release_notes(updater,update)
                self.post_ui(lambda:self.update_checked(updater,update,quiet))
            except Exception as error:
                message=str(error)
                self.post_ui(lambda:self.update_failed(message,quiet))
        threading.Thread(target=work,daemon=True).start()

    def update_failed(self,message,quiet=False):
        self._update_result_text='Denetim tamamlanamadı. Sonuç doğrulanmadı.'
        if getattr(self,'_update_panel',None) and self._update_panel.winfo_exists():self._update_panel.destroy()
        if getattr(self,'_install_waiting',False):
            self._install_waiting=False;self.engine.start_engine()
        self._update_busy=False;self.lbl_status_info.configure(text='Güncelleme kontrolü tamamlanamadı')
        if not quiet:messagebox.showerror('GitHub güncellemesi',message,parent=self)

    def update_checked(self,updater,update,quiet):
        self._update_busy=False
        from datetime import datetime
        self._update_result_text=('Yeni sürüm var: '+update['version'] if update else 'Güncel')+' · Son denetim: '+datetime.now().strftime('%d.%m.%Y %H:%M')
        if not update:
            self.lbl_status_info.configure(text='SDM güncel')
            if not quiet:self.notify('GitHub güncellemesi','Son kararlı sürümü kullanıyorsun.')
            return
        from update_dialog import confirm_update
        if not confirm_update(self,update):return
        self._update_busy=True
        def work():
            try:
                path=updater.download(update,lambda got,total:self.post_ui(lambda:self.show_update_progress(got,total),key='update-progress'))
                self.post_ui(lambda:self.install_update(path))
            except Exception as error:
                message=str(error);self.post_ui(lambda:self.update_failed(message))
        threading.Thread(target=work,daemon=True).start()

    def install_update(self,path):
        self._update_busy=False
        self._update_busy=True;self._install_waiting=True
        self.engine.stop_engine()
        tasks=list(self.engine.tasks.values())+list(self.video_tasks.values())
        for task in tasks:
            if task.status in ('İndiriliyor','Bekliyor'):task.pause()
        def work():
            for task in tasks:
                worker=getattr(task,'_worker',None) or getattr(task,'_thread',None)
                if worker and worker.is_alive():
                    worker.join(45)
                    if worker.is_alive():
                        self.post_ui(lambda:self.update_failed('İndirme henüz durmadı. Güncellemeyi biraz sonra tekrar deneyin.'));return
            self.post_ui(lambda:self.launch_update(path))
        threading.Thread(target=work,daemon=True).start()

    def show_update_progress(self,got,total):
        percent=min(100,got/total*100) if total else 0
        self.lbl_status_info.configure(text=f'Güncelleme indiriliyor: %{percent:.0f}')
        if not getattr(self,'_update_panel',None) or not self._update_panel.winfo_exists():
            from theme_widgets import Panel
            import ttkbootstrap as tb
            import tkinter as tk
            self._update_panel=Panel(self,self.palette);self._update_panel.configure(width=390,height=110)
            self._update_panel.place(relx=1,rely=1,x=-20,y=-50,anchor='se')
            self._update_text=tk.StringVar()
            tk.Label(self._update_panel.content,textvariable=self._update_text,bg=self.palette['panel'],fg=self.palette['text'],font=('Segoe UI',11,'bold')).pack(anchor='w')
            self._update_bar=tb.Progressbar(self._update_panel.content,maximum=100);self._update_bar.pack(fill='x',pady=10)
            tk.Label(self._update_panel.content,text='Tamamlanınca SDM yeniden açılacak',bg=self.palette['panel'],fg=self.palette['muted']).pack(anchor='w')
        self._update_text.set(f'Güncelleme indiriliyor • %{percent:.0f}');self._update_bar.configure(value=percent)

    def launch_update(self,path):
        from updater import launch_installer
        try:launch_installer(path)
        except Exception as error:return self.update_failed(str(error))
        self.destroy()
