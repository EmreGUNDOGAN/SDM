import json
import time
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox,filedialog
from utils import save_settings,format_speed,format_bytes
from queue_rules import scheduled_active,ordered_records
from transfer_control import GLOBAL_LIMITER

class AdvancedActions:
    def initialize_actions(self):
        self._running_queues=set();self._scheduled_queues=set();self._mini_hud=None;self.speed_history={};self._sample_clock={};self._extracting=set()
        super().initialize_actions();self.configure_rate()
        self.after(1000,self.sample_speeds)
        if self.settings.get('mini_hud'):self.show_mini_hud()
        if self.settings.get('scheduled_start'):
            self.settings['queues'][0]['once']=self.settings['scheduled_start'];self.settings['scheduled_start']='';save_settings(self.settings)

    def configure_rate(self):
        normal=self.settings.get('speed_limit_kbs',0)
        rate=min(normal or self.settings['relax_limit_kbs'],self.settings['relax_limit_kbs']) if self.settings.get('relax_mode') else normal
        GLOBAL_LIMITER.configure(rate)

    def toggle_relax(self):
        self.settings['relax_mode']=not self.settings.get('relax_mode',False);save_settings(self.settings);self.configure_rate()
        self.lbl_status_info.configure(text='İnterneti rahatlat açık' if self.settings['relax_mode'] else 'Önceki hız sınırı geri yüklendi')
        if hasattr(self,'relax_button'):self.relax_button.configure(text='Rahatlat: açık' if self.settings['relax_mode'] else 'İnterneti rahatlat')

    def open_tools(self):
        from feature_ui import ToolsDialog
        ToolsDialog(self)

    def show_mini_hud(self):
        from feature_ui import MiniHUD
        if self._mini_hud and self._mini_hud.winfo_exists():self._mini_hud.lift()
        else:self._mini_hud=MiniHUD(self)

    def show_speed_graph(self,did=None):
        from feature_ui import SpeedGraph
        if did is None:
            ids=self._get_selected_ids()
            if not ids:return
            did=ids[0]
        SpeedGraph(self,did)

    def sample_speeds(self):
        from feature_ui import SpeedHistory
        now=time.monotonic()
        for task in list(self.engine.tasks.values())+list(self.video_tasks.values()):
            did=task.download_id
            if did in self._deleting:continue
            received=getattr(task,'downloaded_bytes',None)
            if received is None:received=sum(s.downloaded_bytes for s in task.segments)
            history=self.speed_history.setdefault(did,SpeedHistory())
            history.sample(now,received,task.current_speed,task.status=='İndiriliyor')
        existing={r['id'] for r in self.db.get_all_downloads()}
        for did in list(self.speed_history):
            if did not in existing:self.speed_history.pop(did,None)
        self.after(1000,self.sample_speeds)

    def change_priority(self,value):
        for did in self._get_selected_ids():
            self.db.set_priority(did,value)
            task=self.video_tasks.get(did) or self.engine.get_task(did)
            if task:task.priority=value
        self.lbl_status_info.configure(text='İndirme önceliği güncellendi');self.refresh_downloads()

    def show_queue_menu(self):
        menu=tk.Menu(self,tearoff=0)
        for queue in self.settings['queues']:
            name=queue['name'];sub=tk.Menu(menu,tearoff=0)
            sub.add_command(label='Başlat',command=lambda n=name:self.start_queue(n))
            sub.add_command(label='Duraklat',command=lambda n=name:self.pause_queue(n))
            sub.add_command(label='Seçilileri bu kuyruğa taşı',command=lambda n=name:self.queue_selected(n))
            menu.add_cascade(label=name,menu=sub)
        menu.add_separator();menu.add_command(label='Kuyruk ve zamanlama ayarları',command=self.open_settings_dialog)
        menu.tk_popup(self.winfo_pointerx(),self.winfo_pointery())

    def queue_selected(self,name=None):
        name=name or self.settings['queues'][0]['name']
        for did in self._get_selected_ids():
            record=self.db.get_download(did)
            if not record or record['status']=='Tamamlandı':continue
            self.db.set_queue(did,name);self.pause_download(did)
            task=self.video_tasks.get(did) or self.engine.get_task(did)
            if task:task.queue_requested=True;task.status='Kuyrukta'
            self.db.update_download_status(did,'Kuyrukta')
        self.refresh_downloads()

    def start_queue(self,name=None):
        self._running_queues.add(name or self.settings['queues'][0]['name']);self._queue_running=True;self.queue_tick_once()

    def pause_queue(self,name=None):
        name=name or self.settings['queues'][0]['name'];self._running_queues.discard(name)
        for record in self.db.get_all_downloads():
            if record['queue_name']!=name or record['id'] not in self._queue_ids or record['status'] in ('Tamamlandı','İptal Edildi','Hata'):continue
            did=record['id'];task=self.video_tasks.get(did) or self.engine.get_task(did)
            if task:task.queue_requested=True
            self.pause_download(did)
            if task:task.status='Kuyrukta'
            self.db.update_download_status(did,'Kuyrukta')
        self._queue_running=bool(self._running_queues);self.refresh_downloads()

    def queue_tick_once(self):
        records=self.db.get_all_downloads();now=datetime.now();names={q['name'] for q in self.settings['queues']}
        for record in records:
            if record['queue_name'] not in names:self.db.set_queue(record['id'],self.settings['queues'][0]['name']);record['queue_name']=self.settings['queues'][0]['name']
        changed=False
        for queue in self.settings['queues']:
            name=queue['name'];scheduled=scheduled_active(queue,now)
            if scheduled and name not in self._scheduled_queues:self._scheduled_queues.add(name);self._running_queues.add(name)
            elif not scheduled and name in self._scheduled_queues:self._scheduled_queues.discard(name);self.pause_queue(name)
            if queue.get('once') and now>=datetime.strptime(queue['once'],'%Y-%m-%d %H:%M'):
                queue['once']='';self._running_queues.add(name);changed=True
        if changed:save_settings(self.settings)
        tasks=list(self.engine.tasks.values())+list(self.video_tasks.values())
        active=sum(t.status in ('İndiriliyor','Birleştiriliyor','Dönüştürülüyor','Bekliyor') for t in tasks)
        slots=max(0,self.settings.get('max_simultaneous_downloads',3)-active)
        # Waiting videos occupy a global slot before launch, just as waiting HTTP tasks do.
        for task in sorted(self.video_tasks.values(),key=lambda t:(-getattr(t,'priority',0),t.download_id)):
            http_reserved=sum(t.status in ('Bekliyor','İndiriliyor','Birleştiriliyor') for t in list(self.engine.tasks.values()))
            if task.status=='Bekliyor' and http_reserved+sum(v.status in ('İndiriliyor','Dönüştürülüyor') for v in self.video_tasks.values())<self.settings.get('max_simultaneous_downloads',3):task.start()
        for record in ordered_records(records):
            name=record['queue_name'];queue=next(q for q in self.settings['queues'] if q['name']==name)
            if slots<=0:break
            if record['status']!='Kuyrukta' or name not in self._running_queues:continue
            queue_active=sum(r['queue_name']==name and r['status'] in ('Bekliyor','İndiriliyor','Birleştiriliyor','Dönüştürülüyor') for r in records)
            if queue_active>=queue['limit']:continue
            self._queue_ids.add(record['id'])
            if self.resume_download(record['id']):slots-=1;record['status']='Bekliyor'
        self._queue_running=bool(self._running_queues)
        pending=[r for r in records if r['id'] in self._queue_ids]
        if self._queue_ids and pending and all(r['status']=='Tamamlandı' for r in pending):
            self._queue_ids.clear();self._running_queues-=self._running_queues-self._scheduled_queues
            if self.settings.get('shutdown_after_queue'):self.shutdown_countdown()

    def completed_popup(self,did):
        super().completed_popup(did)
        record=self.db.get_download(did)
        if record and self.settings.get('auto_extract') and Path(record['filepath']).suffix.lower() in ('.zip','.rar') and did not in self._extracting:
            self._extracting.add(did);folder=self.settings.get('extract_dir') or None
            def work():
                try:
                    from archive_tools import extract_archive
                    target=extract_archive(record['filepath'],folder);result='Arşiv çıkarıldı: '+str(target)
                except Exception as error:result='Arşiv çıkarılamadı: '+str(error)
                self.post_ui(lambda:self.lbl_status_info.configure(text=result))
            threading.Thread(target=work,daemon=True).start()

    def select_existing(self,did):
        self.current_category='Tümü';self.search_term='';self.search_var.set('');self.refresh_downloads()
        for item in self.tree.get_children():
            if int(self.tree.item(item,'values')[0])==did:self.tree.selection_set(item);self.tree.see(item);break
        self.show_download_details(did)

    def check_duplicate(self,url,is_video,quality,height):
        if not self.settings.get('duplicate_warning',True):return False
        for record in self.db.get_all_downloads():
            if record['url']!=url or (record['download_type']=='video')!=is_video:continue
            options=json.loads(record.get('options_json') or '{}')
            if is_video and (options.get('height')!=height or options.get('quality')!=quality):continue
            choice=messagebox.askyesnocancel('Bu bağlantı zaten listede',f'{record["filename"]}\nDurum: {record["status"]}\n\nEvet: mevcut indirmeyi göster\nHayır: yeni bir indirme oluştur\nİptal: ekleme',parent=self)
            if choice is True:self.select_existing(record['id']);return True
            if choice is None:return True
            return False
        return False
