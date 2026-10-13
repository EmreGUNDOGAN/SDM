"""Explicit integration script; never runs on unittest discovery."""

def main():
    """Exercise real Tk widgets and user decisions in isolated SDM app data."""
    import tkinter as tk
    from pathlib import Path
    from unittest.mock import patch
    from gui import MainWindow
    from download_engine import SegmentInfo
    from app_dialogs import CapturePrompt,CompletionDialog
    from utils import ensure_config_dir,save_settings

    app=MainWindow();app.engine.stop_engine()
    app.settings['download_dir']=str(ensure_config_dir()/'downloads')
    app.settings['auto_open_details']=False;app.settings['notifications_enabled']=False
    app.settings['duplicate_warning']=False
    save_settings(app.settings)
    Path(app.settings['download_dir']).mkdir(exist_ok=True)
    did=app.add_download_from_dialog('https://example.com/file.zip','file.zip',str(Path(app.settings['download_dir'])/'file.zip'),auto_start=False)
    task=app.engine.get_task(did);task.filesize=1000000;task.supports_ranges=True
    segment=SegmentInfo(0,0,999999);segment.downloaded_bytes=250000;task.segments=[segment];task.status='İndiriliyor';task.current_speed=50000;task.eta=15
    app.show_download_details(did);app.update()
    dialog=app.detail_windows[did]
    assert dialog.values['received'].get().startswith('244.14 KB')
    assert dialog.values['speed'].get()=='48.83 KB/s'
    dialog.cancel_button.invoke();app.update()
    assert did not in app.detail_windows and task.status=='İptal Edildi'
    print('Cancel button stops download and closes actual detail window: OK')

    decisions=[]
    request={'kind':'file','url':'https://example.com/browser.zip','filename':'browser.zip','filesize':1234,'ticket':'test'}
    count=len(app.db.get_all_downloads())
    prompt=CapturePrompt(app,request,lambda t,a:decisions.append(a));app.update()
    assert len(app.db.get_all_downloads())==count
    prompt.buttons['cancel'].invoke();app.update()
    assert decisions[-1]=='cancel' and len(app.db.get_all_downloads())==count
    prompt=CapturePrompt(app,request,lambda t,a:decisions.append(a));prompt.buttons['queue'].invoke();app.update()
    queued=app.db.get_all_downloads()[0]
    assert queued['status']=='Kuyrukta' and decisions[-1]=='queue'
    prompt=CapturePrompt(app,request,lambda t,a:decisions.append(a));prompt.buttons['start'].invoke();app.update()
    started=app.db.get_all_downloads()[0]
    assert started['status']=='Bekliyor' and decisions[-1]=='start'
    assert started['id'] in app.detail_windows
    print('Browser prompt: no automatic start; cancel / queue / start + forced details: OK')

    for theme,background in [('dark','#151d29'),('light','#ffffff')]:
        settings=dict(app.settings,theme=theme);app.apply_settings(settings);app.update()
        app.geometry('1080x640');app.update()
        sidebar=app.sidebar_scroll
        sidebar.yview_moveto(0);app.update()
        assert sidebar.yview()[1]<1
        sidebar.yview_moveto(1);app.update()
        assert sidebar.yview()[1]==1 and sidebar.yview()[0]>0
        assert sidebar.vbar.winfo_ismapped()
        assert app.style.lookup('SDM.Treeview','background')==background
        assert len(app.icon_images)==18
        assert app.hud_active.get()
        app.paint_progress()
        assert app.tree.tk.call('tkdnd::drop_target','register',app.tree._w,'DND_Text') is not None
    print('Approved light/dark widgets, 18 icons, HUD and native drag/drop: OK')

    app.start_queue();app.update()
    assert app.db.get_download(queued['id'])['status']=='Bekliyor'
    app.pause_queue();app.update()
    assert app.db.get_download(queued['id'])['status']=='Kuyrukta'
    print('Manual queue start / pause: OK')

    from modern_settings import SettingsDialog
    settings_dialog=SettingsDialog(app);app.update()
    assert len(settings_dialog.tabs)==6
    settings_dialog.vars['theme'].set('dark');values=settings_dialog.collect()
    assert values['excluded_sites']==['canva.com'] and values['theme']=='dark'
    settings_dialog.destroy()
    completion=CompletionDialog(app,dict(started,filesize=1000000));app.update()
    assert completion.winfo_exists();completion.destroy()
    print('Five settings sections and completion popup: OK')

    for window in list(app.detail_windows.values()):window.close()
    app.destroy()


if __name__ == "__main__":
    main()
