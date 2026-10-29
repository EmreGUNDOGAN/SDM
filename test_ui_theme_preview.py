"""Live appearance selection, rollback and persistence in a disposable profile."""
def main():
    import copy,json
    from pathlib import Path
    from unittest.mock import Mock,patch
    from gui import MainWindow
    from modern_settings import SettingsDialog
    from ui_controls import RadioCard,SegmentedControl
    from theme_catalog import palette
    from utils import CONFIG_FILE,ensure_config_dir,save_settings
    from tools.window_capture import capture_client

    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    app.clipboard_monitor=Mock()
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    def click(button):
        button.event_generate('<ButtonPress-1>',x=12,y=12)
        button.event_generate('<ButtonRelease-1>',x=12,y=12)
        app.update()
    def choose(key,value):
        editor=app._settings_editor
        if key=='design':
            button=next(w for w in descendants(editor) if isinstance(w,RadioCard) and w.value==value and w.variable is editor.vars[key])
        else:
            segment=next(w for w in descendants(editor) if isinstance(w,SegmentedControl) and w.variable is editor.vars[key])
            button=segment.buttons[value]
        click(button)
        return app._settings_editor
    try:
        for initial in ('atlas','odak'):
            app.apply_settings(dict(app.settings,design=initial,color_mode='light',auto_open_details=False,completion_popup=False))
            save_settings(app.settings);app.update()
            saved=copy.deepcopy(app.settings);disk=CONFIG_FILE.read_bytes()
            engine=(app.engine.default_connections,app.engine.max_concurrent,app.engine.speed_limit_kbs)
            did=app.add_download_from_dialog('https://example.invalid/preview',initial+'.bin',str(ensure_config_dir()/(initial+'.bin')),auto_start=False)
            app.open_settings_dialog();app.update();editor=app._settings_editor
            editor.vars['default_connections'].set('invalid')
            editor.queue_editor.name.set('Synthetic draft queue')
            editor.queue_editor.once_enabled.set(True);editor.queue_editor.date_text.set('invalid date')
            editor.new_site.set('draft.example.invalid')
            app.clipboard_monitor.reset_mock()
            with patch.object(app,'configure_rate') as rate,patch('gui.GLOBAL_LIMITER.configure') as limiter:
                editor=choose('color_mode','dark')
                assert app.ui_theme=='dark' and app.cget('bg')==palette(initial+'_dark')['bg']
                assert editor.p==app.palette and editor.save_button.disabled
                assert editor.vars['default_connections'].get()=='invalid'
                assert editor.queue_editor.name.get()=='Synthetic draft queue'
                assert editor.queue_editor.date_text.get()=='invalid date' and editor.queue_editor.once_enabled.get()
                assert editor.new_site.get()=='draft.example.invalid'
                assert app.settings==saved and CONFIG_FILE.read_bytes()==disk
                other='odak' if initial=='atlas' else 'atlas'
                editor=choose('design',other)
                assert app.theme_family==other and app.ui_theme=='dark' and editor.p==app.palette
                assert editor.vars['default_connections'].get()=='invalid' and editor.save_button.disabled
                assert app.settings==saved and CONFIG_FILE.read_bytes()==disk
                rate.assert_not_called();limiter.assert_not_called();app.clipboard_monitor.assert_not_called()
                assert not app.clipboard_monitor.method_calls
                assert (app.engine.default_connections,app.engine.max_concurrent,app.engine.speed_limit_kbs)==engine
                assert app.db.get_download(did)['queue_name']==saved['queues'][0]['name']
            editor.revert();app.update();editor=app._settings_editor
            assert (app.theme_family,app.ui_theme)==(initial,'light') and not editor.change_count.get()
            # Preview is reversible even when fields are invalid, via Escape/window X.
            editor=choose('color_mode','dark')
            if editor.embedded:
                from ui_overlays import MessageDialog
                app.after(30,lambda:next(w for w in app.winfo_children() if isinstance(w,MessageDialog)).actions['discard'].invoke())
                app._atlas_workspace.navigate('downloads')
            else:
                dialog=editor.winfo_toplevel();dialog.focus_force();app.update();dialog.event_generate('<Escape>')
            app.update();assert app.ui_theme=='light' and app.settings==saved and CONFIG_FILE.read_bytes()==disk
            # A failed save retains both draft and preview, then real Save persists them.
            app.open_settings_dialog();app.update();editor=choose('color_mode','dark')
            editor.queue_editor.name.set('Synthetic saved '+initial)
            with patch('modern_settings.save_settings',return_value=False):
                assert not editor.save() and editor.error.get()
            assert app.ui_theme=='dark' and app.settings==saved and CONFIG_FILE.read_bytes()==disk
            capture_client(app).save(Path('build')/('live-theme-'+initial+'-dark.png'))
            click(editor.save_button)
            assert app.ui_theme=='dark' and app.settings['color_mode']=='dark'
            assert json.loads(CONFIG_FILE.read_text(encoding='utf-8'))['color_mode']=='dark'
            assert app.db.get_download(did)['queue_name']=='Synthetic saved '+initial
            # Closing and reopening settings cannot resurrect an old preview/draft.
            app.open_settings_dialog();app.update();editor=app._settings_editor
            assert editor.vars['color_mode'].get()=='dark' and not editor.change_count.get()
            editor=choose('color_mode','light')
            if editor.embedded:
                app._atlas_workspace.settings_page.cancel_preview()
            else:
                dialog=editor.winfo_toplevel();dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
            app.update();assert app.ui_theme=='dark'
            assert not errors,errors
        # Saving before the idle preview fires must still apply the last selection.
        dialog=SettingsDialog(app);editor=dialog.content
        editor.vars['color_mode'].set('light');assert editor.save();app.update()
        assert app.ui_theme=='light' and json.loads(CONFIG_FILE.read_text(encoding='utf-8'))['color_mode']=='light'
        disk=CONFIG_FILE.read_bytes();app.open_settings_dialog();app.update()
        with patch('theme_catalog.system_color_mode',return_value='dark'):
            editor=choose('color_mode','system')
            assert app.ui_theme=='dark' and app.settings['color_mode']=='light' and CONFIG_FILE.read_bytes()==disk
            click(editor.save_button)
            assert app.settings['color_mode']=='system' and app.ui_theme=='dark'
            assert json.loads(CONFIG_FILE.read_text(encoding='utf-8'))['color_mode']=='system'
        assert not errors,errors
        print('Real theme clicks before Save; both layouts, raw invalid drafts, rollback, Escape/X/discard, failed and successful Save, DB rename, engine isolation and immediate Save: OK')
    finally:app.engine.stop_engine();app.destroy()

if __name__=='__main__':main()
