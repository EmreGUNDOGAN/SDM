"""Exercise native widgets in an isolated app data directory."""
import tkinter as tk
from gui import MainWindow
from download_engine import SegmentInfo
from utils import load_settings

app=MainWindow()
app.engine.stop_engine()
did=app.db.add_download('https://example.com/file.zip','file.zip','file.zip',filesize=1000000)
task=app.engine.add_task(did,'https://example.com/file.zip','file.zip',auto_start=False)
task.status='İndiriliyor'
task.filesize=1000000
task.supports_ranges=True
segment=SegmentInfo(0,0,999999)
segment.downloaded_bytes=250000
segment.status='İndiriliyor'
task.segments=[segment]
task.current_speed=50000
task.eta=15
app.refresh_downloads()
app.show_download_details(did)
app.update()
window=app.detail_windows[did]
assert window.values['received'].get().startswith('244.14 KB')
assert window.values['speed'].get()=='48.83 KB/s'
assert app.style.lookup('SDM.Treeview','foreground')=='#111111'
assert app.style.lookup('SDM.Treeview','background')=='#ffffff'
assert app.style.theme_use()=='cosmo'
assert 'downloaded' in app.tree.cget('displaycolumns')
window.toggle_details()
assert not window.details.winfo_manager()
window.toggle_details()
assert window.details.winfo_manager()
app.column_vars={'filename':tk.BooleanVar(value=True),'remaining':tk.BooleanVar(value=True),'eta':tk.BooleanVar(value=True)}
app.save_columns()
assert load_settings()['visible_columns']==['filename','remaining','eta']
window.close()
assert did not in app.detail_windows
app.add_download_from_dialog('https://example.com/auto.zip','auto.zip','auto.zip')
assert len(app.detail_windows)==1
for dialog in list(app.detail_windows.values()):dialog.close()
app.destroy()
print('Native white UI, black text, details, progress, toggle and saved columns: OK')
