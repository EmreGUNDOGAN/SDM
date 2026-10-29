"""Final transient cleanup and missing-file decisions in a disposable profile."""
def main():
    import time
    from pathlib import Path
    from gui import MainWindow
    from utils import ensure_config_dir
    from app_dialogs import BatchDialog
    from feature_ui import SpeedGraph,SpeedHistory,ToolsDialog
    from ui_overlays import MessageDialog
    app=MainWindow();app.engine.stop_engine();errors=[];app.report_callback_exception=lambda *args:errors.append(args)
    app.settings.update(duplicate_warning=False,auto_open_details=False,completion_popup=False,notifications_enabled=False)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    did=app.add_download_from_dialog('https://example.invalid/missing','missing.bin',str(folder/'missing.bin'),auto_start=False)
    other=app.add_download_from_dialog('https://example.invalid/other','other.bin',str(folder/'other.bin'),auto_start=False)
    app.speed_history[did]=SpeedHistory()
    try:
        for design in ('atlas','odak'):
            app.apply_settings(dict(app.settings,design=design,color_mode='light'));app.update()
            graph=SpeedGraph(app,did);tools=ToolsDialog(app);batch=BatchDialog(app);app.show_mini_hud();hud=app._mini_hud
            app.show_download_details(did);detail=app.detail_windows[did];app.update()
            app.apply_settings(dict(app.settings,color_mode='dark'));app.update()
            assert not graph.winfo_exists() and not tools.winfo_exists() and not batch.winfo_exists()
            assert not detail.winfo_exists() and not graph._owned_timers and batch._closed.is_set() and hud._timer is None
            assert not app.detail_windows
        app.select_category('Tümü');app.select_status_filter('Tümü');app.tree.selection_set('download-'+str(did));app.open_file();app.update()
        message=next(w for w in app.winfo_children() if isinstance(w,MessageDialog));assert 'remove' in message.actions
        # Change selection/filter while the error is open; remove its captured
        # record, never the newly selected visible record.
        app.search_var.set('other');app.update();app.tree.selection_set('download-'+str(other))
        def approve():
            dialog=next(w for w in app.winfo_children() if isinstance(w,MessageDialog));dialog.actions['yes'].invoke()
        app.after(100,approve);message.actions['remove'].invoke()
        deadline=time.monotonic()+8
        while app.db.get_download(did) and time.monotonic()<deadline:app.update();time.sleep(.01)
        assert app.db.get_download(did) is None and app.db.get_download(other) is not None
        assert not errors,errors
        print('Transient windows/owned timers/inspection cleanup and missing-file removal targets the original record after filter/selection changes: OK')
    finally:app.engine.stop_engine();app.destroy()

if __name__=='__main__':main()
