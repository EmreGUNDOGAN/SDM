"""
gui.py - Modern Graphical User Interface for SDM using ttkbootstrap.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from PIL import ImageTk
from tkinter import filedialog
from ui_messages import messagebox
from typing import Any, Dict, List, Optional

try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
except ImportError:
    import tkinter.ttk as tb
    from tkinter.constants import *

try:
    from plyer import notification
except ImportError:
    notification = None

from assets.icon import create_default_icon_image, get_app_icon_image
from database import DownloadDatabase
from download_engine import DownloadEngine
from utils import (
    clean_filename,
    extract_filename_from_url,
    format_bytes,
    format_eta,
    format_speed,
    get_category_by_extension,
    get_unique_filepath,
    is_valid_url,
    load_settings,
    save_settings,
)
from video_downloader import VideoDownloadTask, fetch_video_info, is_video_site
from download_window import DownloadDetailDialog
from list_display import COLUMNS, row_values
from modern_ui import ModernUI
from app_actions import AppActions
from advanced_actions import AdvancedActions
from transfer_control import GLOBAL_LIMITER
from download_cleanup import delete_download_files
from ui_mailbox import UIMailbox

logger = logging.getLogger("SDM.GUI")


def show_desktop_notification(title: str, message: str) -> None:
    """Show a desktop notification using plyer if enabled."""
    if notification:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="SDM",
                timeout=5,
            )
        except Exception as e:
            logger.debug(f"Notification error: {e}")


class MainWindow(ModernUI, AdvancedActions, AppActions, tb.Window):


    """SDM desktop window using the approved modern UI."""

    CATEGORIES = ["Tümü", "Belgeler", "Resimler", "Müzik", "Video", "Arşivler", "Programlar", "Diğer",'Devam Edenler','Tamamlananlar']

    def __init__(self):
        super().__init__(themename='cosmo')
        self._mailbox=UIMailbox(self)
        self._deleting=set()
        self.style.configure('.',foreground='#111111')
        self.style.configure('TLabel',foreground='#111111',background='#ffffff')
        self.style.configure('TEntry',foreground='#111111',fieldbackground='#ffffff')
        self.style.configure('SDM.Treeview',foreground='#111111',background='#ffffff',fieldbackground='#ffffff',rowheight=30,font=('Inter',10))
        self.style.configure('SDM.Treeview.Heading',foreground='#111111',background='#f4f6f8',font=('Inter',10))
        self.style.map('SDM.Treeview',foreground=[('selected','#111111')],background=[('selected','#e6f1fc')])
        self.detail_windows = {}
        self.title("SDM")
        self.geometry(f'{min(1440,self.winfo_screenwidth()-70)}x{min(840,self.winfo_screenheight()-100)}')
        self.minsize(1080, 640)

        self.settings = load_settings()
        self.db = DownloadDatabase()
        self.engine = DownloadEngine(
            max_concurrent=self.settings.get("max_simultaneous_downloads", 3),
            default_connections=self.settings.get("default_connections", 8),
            speed_limit_kbs=self.settings.get("speed_limit_kbs", 0),
        )
        self.engine.start_engine()

        # In-memory tracking for video tasks
        self.video_tasks: Dict[int, VideoDownloadTask] = {}
        self.current_category = "Tümü"
        self.search_term = ""

        # Setup icon
        try:
            self._icon_pil = get_app_icon_image()
            self._icon_photo = ImageTk.PhotoImage(self._icon_pil.resize((64, 64)), master=self)
            self.iconphoto(True, self._icon_photo)
            icon_path = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets' / 'sdm.ico'
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
                self.iconbitmap(default=str(icon_path))
        except Exception as e:
            logger.debug(f"Could not set Tk icon: {e}")

        self._build_ui()
        self._setup_shortcuts()
        self._load_downloads_from_db()
        self.initialize_actions()
        self.initialize_drop()
        self._start_status_updater()

        # Handle close event (minimize to tray vs exit)
        self.protocol("WM_DELETE_WINDOW", self.on_close_window)

    def _setup_shortcuts(self) -> None:
        self.bind("<Control-n>", lambda e: self.open_add_dialog())
        self.bind("<Control-N>", lambda e: self.open_add_dialog())
        self.bind("<Delete>", self._delete_shortcut)
        self.bind("<F5>", lambda e: self.refresh_downloads())

    def _delete_shortcut(self,event):
        if event.widget.winfo_class() in ('Entry','TEntry','Text','TCombobox','Spinbox','TSpinbox'):return
        self.delete_selected()

    def select_category(self, cat: str) -> None:
        self.current_category = cat
        self.current_queue_filter=None
        for name,btn in self.category_buttons.items():
            btn.selected=name==cat;btn.draw()
        for name,btn in self.status_buttons.items():
            btn.selected=name==getattr(self,'current_status_filter','Tümü');btn.draw()
        self.refresh_downloads()

    def _on_search_change(self) -> None:
        self.search_term = self.search_var.get().strip()
        self.refresh_downloads()

    def _load_downloads_from_db(self) -> None:
        self.db.recover_interrupted_downloads()
        self.refresh_downloads()

    def refresh_downloads(self):
        from atlas_view import matches_status
        selected=set(self._get_selected_ids())
        special=self.current_category in ('Devam Edenler','Tamamlananlar','Hatalı')
        all_records=self.db.get_all_downloads()
        records=self.db.get_all_downloads(category=None if special else self.current_category,search_term=self.search_term)
        if special:records=[r for r in records if matches_status(r['status'],self.current_category)]
        state=getattr(self,'current_status_filter','Tümü')
        records=[r for r in records if matches_status(r['status'],state)]
        queue=getattr(self,'current_queue_filter',None)
        if queue:records=[r for r in records if r.get('queue_name')==queue]
        workspace=getattr(self,'_atlas_workspace',None)
        if workspace and hasattr(workspace,'sort_records'):records=workspace.sort_records(records)
        self._visible_records={r['id']:r for r in records};self._all_records=all_records
        wanted=[f'download-{r["id"]}' for r in records]
        stale=set(self.tree.get_children())-set(wanted)
        if stale:self.tree.delete(*stale)
        for record,item in zip(records,wanted):
            values=tuple(map(str,row_values(self,record)))
            if self.tree.exists(item):
                if tuple(self.tree.item(item,'values'))!=values:self.tree.item(item,values=values)
            else:self.tree.insert('',END,iid=item,values=values)
        if tuple(self.tree.get_children())!=tuple(wanted):
            for index,item in enumerate(wanted):self.tree.move(item,'',index)
        selection=tuple(item for record,item in zip(records,wanted) if record['id'] in selected)
        if tuple(self.tree.selection())!=selection:self.tree.selection_set(selection)
        self.filter_summary.set(f'{self.current_category} · {len(records)} sonuç'+(f' · {self.search_term}' if self.search_term else ''))
        self.page_title.set('Tüm indirmeler' if self.current_category=='Tümü' else self.current_category)
        workspace=getattr(self,'_atlas_workspace',None)
        if workspace and workspace.alive:
            workspace.sync(records,all_records)
        elif not records:
            self.empty_label.configure(text='Aramanızla eşleşen indirme bulunamadı' if self.search_term else 'Bu kategoride henüz indirme yok')
            self.empty_label.place(relx=.5,rely=.35,anchor='center')
            if self.search_term:self.empty_clear.place(relx=.5,rely=.35,y=40,anchor='center')
            else:self.empty_clear.place_forget()
        else:self.empty_label.place_forget();self.empty_clear.place_forget()
        self.update_action_states()


    def _start_status_updater(self):
        videos=[t for t in self.video_tasks.values() if t.status=='İndiriliyor']
        speed=self.engine.get_total_speed()+sum(t.current_speed for t in videos)
        self.lbl_status_summary.configure(text='Hazır' if not self.engine.get_active_count()+len(videos) else f'{self.engine.get_active_count()+len(videos)} aktif indirme')
        records={record['id']:record for record in self.db.get_all_downloads()}
        self._all_records=list(records.values())
        self._visible_records={did:records[did] for did in getattr(self,'_visible_records',{}) if did in records}
        for item in self.tree.get_children():
            did=int(self.tree.item(item,'values')[0])
            record=records.get(did)
            if record:
                values=tuple(map(str,row_values(self,record)))
                if self.tree.item(item,'values')!=values:self.tree.item(item,values=values)
        self.update_hud()
        self.after(1000,self._start_status_updater)

    def open_add_dialog(self, initial_url: str = "") -> None:
        from app_dialogs import BatchDialog
        BatchDialog(self, initial_url)

    def open_settings_dialog(self) -> None:
        from modern_settings import SettingsDialog as ModernSettingsDialog
        for child in self.winfo_children():
            if isinstance(child,ModernSettingsDialog):child.lift();child.focus_set();return
        workspace=getattr(self,'_atlas_workspace',None)
        if self.theme_family=='odak' and workspace and workspace.alive:return workspace.navigate('settings')
        ModernSettingsDialog(self)

    def apply_visible_columns(self):
        if self.theme_family=='odak':self.tree.configure(displaycolumns=('filename',));return
        valid={c[0] for c in COLUMNS}
        visible=[c for c in self.settings.get('visible_columns',[]) if c in valid]
        if 'filename' not in visible:visible.insert(0,'filename')
        self.tree.configure(displaycolumns=visible)

    def show_column_menu(self):
        workspace=getattr(self,'_atlas_workspace',None)
        if workspace and workspace.alive:return workspace.column_menu()
        menu=tk.Menu(self,tearoff=False)
        self.column_vars={}
        visible=set(self.tree.cget('displaycolumns'))
        for name,label,width in COLUMNS:
            variable=tk.BooleanVar(value=name in visible)
            self.column_vars[name]=variable
            menu.add_checkbutton(label=label,variable=variable,
                state='disabled' if name=='filename' else 'normal',command=self.save_columns)
        menu.tk_popup(self.winfo_pointerx(),self.winfo_pointery())

    def save_columns(self):
        self.settings['visible_columns']=[name for name,var in self.column_vars.items() if var.get()]
        save_settings(self.settings)
        self.apply_visible_columns()

    def show_download_details(self,did):
        workspace=getattr(self,'_atlas_workspace',None)
        if self.theme_family=='odak' and workspace and workspace.alive:return workspace.open_detail(did)
        existing=self.detail_windows.get(did)
        if existing and existing.winfo_exists():
            existing.lift()
            return
        record=self.db.get_download(did)
        if record:
            window=DownloadDetailDialog(self,record)
            self.detail_windows[did]=window
            from app_dialogs import foreground
            foreground(window)

    def pause_download(self,did):
        record=self.db.get_download(did)
        if not record or record['status'] in ('Tamamlandı','İptal Edildi'):return
        if did in self.video_tasks:self.video_tasks[did].pause()
        else:self.engine.pause_task(did)

    def resume_download(self,did):
        record=self.db.get_download(did)
        if not record or record['status']=='Tamamlandı':return False
        task=self.video_tasks.get(did) or self.engine.get_task(did)
        worker=(getattr(task,'_worker',None) or getattr(task,'_thread',None)) if task else None
        if worker and worker.is_alive():return False
        options=json.loads(record.get('options_json') or '{}')
        if not task:
            if record['download_type']=='video':
                task=VideoDownloadTask(did,record['url'],Path(record['filepath']).parent,
                    quality=options.get('quality','Yalnızca Ses (MP3)' if record['filepath'].endswith('.mp3') else 'En İyi'),
                    selected_height=options.get('height'),connections=record['num_connections'],
                    output_name=options.get('output_name'),
                    section=options.get('section'),
                    progress_callback=self._on_download_progress,status_callback=self._on_download_status_change,
                    metadata_callback=self._on_metadata_updated)
                self.video_tasks[did]=task
            else:
                task=self.engine.add_task(did,record['url'],record['filepath'],num_connections=record['num_connections'],
                    resume_legacy_parts=record['downloaded_bytes']>0,headers=json.loads(record['headers'] or '{}'),
                    auto_start=False,progress_callback=self._on_download_progress,
                    status_callback=self._on_download_status_change,metadata_callback=self._on_metadata_updated)
        task.queue_requested=False
        task.priority=record.get('priority',0)
        task.status='Bekliyor'
        self.db.update_download_status(did,'Bekliyor')
        self._session_baselines.setdefault(did,record['downloaded_bytes'])
        self.refresh_downloads()
        return True

    def cancel_download(self,did):
        record=self.db.get_download(did)
        if not record or record['status']=='Tamamlandı':return
        if did in self.video_tasks:self.video_tasks[did].cancel()
        else:self.engine.cancel_task(did)

    def apply_settings(self, new_settings: Dict[str, Any]) -> None:
        self.settings = new_settings
        self.engine.max_concurrent = new_settings.get("max_simultaneous_downloads", 3)
        self.engine.default_connections = new_settings.get("default_connections", 8)
        self.engine.speed_limit_kbs = new_settings.get("speed_limit_kbs", 0)
        GLOBAL_LIMITER.configure(self.engine.speed_limit_kbs)
        self.configure_rate()
        if hasattr(self,'clipboard_monitor'):
            self.clipboard_monitor.set_extensions(new_settings.get('monitored_extensions',[]))
            if new_settings.get('clipboard_monitoring',True):self.clipboard_monitor.start()
            else:self.clipboard_monitor.stop()
        self.rebuild_appearance()

    def preview_appearance(self,design,color_mode):
        """Rebuild visual surfaces without saving or applying other preferences."""
        saved=self.settings
        try:
            self.settings=dict(saved,design=design,color_mode=color_mode)
            self.rebuild_appearance()
        finally:self.settings=saved

    def rebuild_appearance(self):
        from modern_settings import SettingsDialog
        for child in list(self.winfo_children()):
            if isinstance(child,tk.Toplevel) and not isinstance(child,SettingsDialog):
                if hasattr(child,'close'):child.close()
                elif hasattr(child,'finish'):child.finish(None)
                else:child.destroy()
        for child in self.winfo_children():
            if not isinstance(child, tk.Toplevel):child.destroy()
        self._build_ui()
        self.initialize_drop()
        if self.settings.get('mini_hud'):self.show_mini_hud()

    def add_download_from_dialog(
        self,
        url: str,
        filename: str,
        dest_path: str,
        is_video: bool = False,
        video_quality: str = "En İyi",
        connections: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        auto_start: bool = True,
        selected_height: Optional[int] = None,
        from_browser: bool = False,
        expected_size: int = 0,
        section=None,
    ) -> None:
        if self.check_duplicate(url,is_video,video_quality,selected_height,section):return None
        if self.settings.get('disk_check',True):
            from file_tools import ensure_space
            try:ensure_space(dest_path,expected_size if not is_video else 0,multiplier=2)
            except OSError:
                messagebox.showwarning('Disk alanı yetersiz','Başka bir kayıt klasörü seçmelisin.',parent=self)
                folder=filedialog.askdirectory(parent=self)
                if not folder:return None
                dest_path=str(Path(folder)/filename);ensure_space(dest_path)
        cat = get_category_by_extension(filename)
        connections=connections or self.settings.get('default_connections',8)
        status = "Bekliyor" if auto_start else "Kuyrukta"
        destination=Path(dest_path)
        reserved={Path(record['filepath']) for record in self.db.get_all_downloads()}
        candidate=get_unique_filepath(destination.parent,destination.name)
        index=1
        while candidate in reserved:
            candidate=destination.with_name(f'{destination.stem} ({index}){destination.suffix}')
            candidate=get_unique_filepath(candidate.parent,candidate.name)
            index+=1
        dest_path=str(candidate)
        filename=candidate.name

        did = self.db.add_download(
            url=url,
            filename=filename,
            filepath=dest_path,
            filesize=max(0,int(expected_size or 0)),
            category=cat,
            num_connections=connections,
            headers=headers or {},
            download_type="video" if is_video else "direct",
            status=status,
        )

        self.db.set_options(did, {'quality':video_quality,'height':selected_height,'output_name':candidate.name if from_browser else None,'section':section})
        self.db.set_queue(did,self.settings['queues'][0]['name'])
        self._session_baselines[did]=0
        self._session_received[did]=0
        if is_video:
            vtask = VideoDownloadTask(
                download_id=did,
                url=url,
                dest_folder=Path(dest_path).parent,
                quality=video_quality,
                selected_height=selected_height,
                section=section,
                connections=connections,
                output_name=candidate.name if from_browser else None,
                progress_callback=self._on_download_progress,
                status_callback=self._on_download_status_change,
                metadata_callback=self._on_metadata_updated,
            )
            self.video_tasks[did] = vtask
            vtask.status=status
        else:
            self.engine.add_task(
                download_id=did,
                url=url,
                dest_path=dest_path,
                num_connections=connections,
                headers=headers,
                auto_start=auto_start,
                progress_callback=self._on_download_progress,
                status_callback=self._on_download_status_change,
                metadata_callback=self._on_metadata_updated,
            )

        if not auto_start:
            task=self.video_tasks.get(did) or self.engine.get_task(did)
            if task:task.status='Kuyrukta'
        self.refresh_downloads()
        if auto_start and (from_browser or self.settings.get('auto_open_details',True)):
            self.show_download_details(did)
        return did

    def _on_download_progress(
        self, did: int, downloaded: int, total: int, speed: float, eta: float, status: str
    ) -> None:
        self.post_ui(lambda:self._apply_progress(did,downloaded,total),key=('progress',did))

    def _apply_progress(self,did,downloaded,total):
        if did in self._deleting or not self.db.get_download(did):return
        self.db.update_download_progress(did, downloaded, total)
        baseline=self._session_baselines.setdefault(did,downloaded)
        self._session_received[did]=max(self._session_received.get(did,0),downloaded-baseline,0)

    def _on_download_status_change(self, did: int, status: str, error: str) -> None:
        self.post_ui(lambda:self._apply_status(did,status,error))

    def _apply_status(self,did,status,error):
        if did in self._deleting or not self.db.get_download(did):return
        task=self.video_tasks.get(did) or self.engine.get_task(did)
        if status=='Duraklatıldı' and task and getattr(task,'queue_requested',False):
            status='Kuyrukta';task.status=status
        elif task and task.status!=status:return
        completed = status == "Tamamlandı"
        self.db.update_download_status(did, status, error, completed=completed)

        if completed and self.settings.get("notifications_enabled", True):
            rec = self.db.get_download(did)
            fname = rec["filename"] if rec else f"İndirme #{did}"
            threading.Thread(target=show_desktop_notification,args=('İndirme Tamamlandı',f'{fname} başarıyla indirildi.'),daemon=True).start()

        self.post_ui(self.refresh_downloads,key='refresh')
        if completed:self.completed_popup(did)
        elif status=='Hata':self.show_download_error(did,error)

    def _on_metadata_updated(
        self, did: int, filename: str, filepath: str, filesize: int, category: str
    ) -> None:
        def apply():
            if did in self._deleting or not self.db.get_download(did):return
            self.db.update_download_metadata(did,filename,filepath,filesize,category)
            self.post_ui(self.refresh_downloads,key='refresh')
        self.post_ui(apply,key=('metadata',did))

    def post_ui(self,callback,key=None):
        self._mailbox.post(callback,key)

    def destroy(self):
        if hasattr(self,'_mailbox'):self._mailbox.close()
        super().destroy()

    def _get_selected_ids(self) -> List[int]:
        selected = []
        for item in self.tree.selection():
            values = self.tree.item(item, "values")
            if values:
                selected.append(int(values[0]))
        return selected

    def resume_selected(self):
        for did in self._get_selected_ids():self.resume_download(did)

    def pause_selected(self):
        for did in self._get_selected_ids():self.pause_download(did)
        self.refresh_downloads()

    def cancel_selected(self):
        for did in self._get_selected_ids():self.cancel_download(did)
        self.refresh_downloads()

    def delete_selected(self, delete_file: bool = False, ids=None) -> None:
        ids = self._get_selected_ids() if ids is None else list(ids)
        if not ids:
            return

        msg = f"{len(ids)} indirme listeden kaldırılsın mı? Dosyalar diskte kalır."
        if delete_file:
            msg = f"{len(ids)} indirme ve dosyası kalıcı olarak silinsin mi? Bu işlem geri alınamaz."

        listing=[record['filename']+' · '+format_bytes(record['filesize']) for did in ids if (record:=self.db.get_download(did))]
        if not messagebox.askyesno("Dosyaları sil" if delete_file else "Listeden kaldır", msg,parent=self,items=listing,
                affirmative='Dosyaları sil' if delete_file else 'Listeden kaldır',danger=delete_file):
            return

        pending = []
        for did in ids:
            if did in self._deleting:continue
            self._deleting.add(did)
            task = self.video_tasks.get(did) or self.engine.get_task(did)
            if task:
                task.cancel()
            pending.append((did, self.db.get_download(did), task))
        def remove():
            errors = []
            removed=[]
            for did, rec, task in pending:
                try:
                    if delete_file and rec:
                        delete_download_files(rec, task)
                    self.engine.remove_task(did)
                    self.db.delete_download(did)
                    removed.append(did)
                except Exception as error:
                    errors.append(f'#{did}: {error}')
            def finished():
                for did in removed:self.video_tasks.pop(did,None)
                self._deleting.difference_update(did for did,_,_ in pending)
                self.refresh_downloads()
                if errors:
                    messagebox.showerror('Silme tamamlanamadı', '\n'.join(errors), parent=self)
            self.post_ui(finished)
        threading.Thread(target=remove, daemon=True).start()

    def open_file(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            return
        rec = self.db.get_download(ids[0])
        if rec and rec.get("filepath"):
            fp = Path(rec["filepath"])
            if fp.exists():
                os.startfile(str(fp))
            else:
                from ui_messages import show_error
                show_error(self,'Dosya bulunamadı','Dosya belirtilen konumda bulunamadı.',actions=(('remove','Listeden kaldır',lambda:self.remove_missing_record(rec['id'])),))

    def remove_missing_record(self,did):
        record=self.db.get_download(did)
        if not record:return
        self.delete_selected(ids=[did])

    def open_folder(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            return
        rec = self.db.get_download(ids[0])
        if rec and rec.get("filepath"):
            parent_dir = Path(rec["filepath"]).parent
            if parent_dir.exists():
                subprocess.Popen(["explorer", str(parent_dir)])

    def show_selected_details(self) -> None:
        ids = self._get_selected_ids()
        if not ids:
            return
        rec = self.db.get_download(ids[0])
        if rec:
            self.show_download_details(rec['id'])

    def _on_tree_double_click(self, event) -> None:
        self.show_selected_details()

    def _on_tree_right_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            workspace=getattr(self,'_atlas_workspace',None)
            if workspace and workspace.alive:return workspace.context_menu(event)
            self.context_menu.post(event.x_root, event.y_root)

    def on_close_window(self) -> None:
        """Handle window close: minimize or exit based on settings."""
        self.withdraw()  # Minimize to system tray
