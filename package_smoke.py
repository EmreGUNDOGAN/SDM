"""Explicit source/frozen desktop check; no installed app or real profile access."""
def run():
    import json,os,time
    from pathlib import Path
    from utils import ensure_config_dir
    data=Path(os.environ['SDM_DATA_DIR']).resolve();build=(Path.cwd()/'build').resolve()
    if not data.is_relative_to(build):raise RuntimeError('Package check profile must be inside workspace/build')
    from gui import MainWindow
    from main import TrayManager
    from modern_settings import SettingsDialog
    from app_dialogs import CapturePrompt,CompletionDialog
    from feature_ui import ToolsDialog,SpeedGraph,SpeedHistory
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:(errors.append(str(args)),app.destroy())
    app.settings.update(clipboard_monitoring=False,notifications_enabled=False,update_check_on_start=False,duplicate_warning=False,completion_popup=False,auto_open_details=False)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True);app.settings['download_dir']=str(folder)
    did=app.add_download_from_dialog('https://example.invalid/fixture','synthetic.bin',str(folder/'synthetic.bin'),auto_start=False)
    tray=None;matrix=[]
    try:
        for design in ('atlas','odak'):
            for mode in ('light','dark'):
                app.apply_settings(dict(app.settings,design=design,color_mode=mode));app.update()
                assert app.winfo_viewable() and app._icon_photo.width()==64
                dialog=SettingsDialog(app);app.update();assert len(dialog.tabs)==6;dialog.destroy()
                decisions=[];prompt=CapturePrompt(app,dict(kind='file',url='https://example.invalid/fixture',filename='synthetic.bin',filesize=1234,ticket='synthetic'),lambda token,result:decisions.append(result))
                prompt.buttons['cancel'].invoke();assert decisions==['cancel']
                tools=ToolsDialog(app);app.update();tools.close()
                app.speed_history[did]=SpeedHistory();app.speed_history[did].sample(1,0,0,True);app.speed_history[did].sample(2,50,50,True)
                graph=SpeedGraph(app,did);app.update();graph.close()
                app.show_download_details(did);app.update();assert did in app.detail_windows;app.detail_windows[did].close()
                app.show_mini_hud();app.update();app._mini_hud.close()
                assert not errors,errors;matrix.append(design+'_'+mode)
        tray=TrayManager(app)
        if tray.icon is None:raise RuntimeError('Real system tray is required')
        tray.start();deadline=time.monotonic()+8
        def ready():
            if errors:raise RuntimeError(str(errors))
            if tray.icon.visible:
                (data/'package-result.json').write_text(json.dumps(dict(views=matrix,tray_visible=True,profile=str(data))),encoding='utf-8')
                tray.quit_app();return
            if time.monotonic()>deadline:raise RuntimeError('System tray did not become visible')
            app.after(40,ready)
        app.after(40,ready);app.mainloop()
        if errors:raise RuntimeError(str(errors))
    finally:
        app.engine.stop_engine()
        if tray:tray.stop()
