"""Settings save/cancel/restore and queues, using only the runner's fake profile."""
def main():
    import copy,json
    from pathlib import Path
    from unittest.mock import patch
    from gui import MainWindow
    from modern_settings import SettingsDialog
    from preferences import export_settings
    from utils import ensure_config_dir,CONFIG_FILE
    from tools.window_capture import capture_client
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    try:
        for design in ('atlas','odak'):
            for mode in ('light','dark'):
                app.apply_settings(dict(app.settings,design=design,color_mode=mode));app.update()
                before=copy.deepcopy(app.settings);disk=CONFIG_FILE.read_bytes()
                dialog=SettingsDialog(app);editor=dialog.content;app.update()
                assert len(editor.tabs)==6 and editor.change_count.get()==0
                editor.vars['default_connections'].set('0');app.update()
                assert editor.save_button.disabled and editor.inputs['default_connections'].error
                editor.vars['default_connections'].set('16');editor.vars['language'].set('en');app.update()
                assert not editor.save_button.disabled and editor.change_count.get()==2
                assert app.settings==before and CONFIG_FILE.read_bytes()==disk
                editor.queue_editor.add();editor.queue_editor.name.set('Synthetic night queue')
                editor.queue_editor.enabled.set(True);editor.queue_editor.quick_date(1)
                values=editor.collect();assert len(values['queues'])==2 and values['queues'][1]['once']
                assert app.settings['queues']==before['queues']
                editor.chips.input.variable.set('.zip');editor.chips.add_from_entry();assert editor.collect()['capture_extensions']==['zip']
                editor.new_site.set('https://example.com/path');editor.add_site();assert 'example.com' in editor.collect()['excluded_sites']
                backup=ensure_config_dir()/'synthetic-backup.json';export_settings(backup,dict(before,default_connections=12,github_token='synthetic-omitted'))
                data=json.loads(backup.read_text(encoding='utf-8'));assert 'github_token' not in data['settings']
                with patch('modern_settings.filedialog.askopenfilename',return_value=str(backup)):editor.restore()
                assert editor.vars['default_connections'].get()=='12' and app.settings==before and CONFIG_FILE.read_bytes()==disk
                editor.revert();assert editor.change_count.get()==0 and editor.collect()==editor.baseline
                editor.queue_editor.add();removed=editor.queue_editor.name.get();editor.queue_editor.remove()
                assert editor.queue_editor.renames[removed]==editor.baseline['queues'][0]['name']
                assert editor.collect()==editor.baseline
                for index,section in enumerate(editor.tabs):
                    editor.show_section(section);app.update();assert editor.deck.select()==str(editor.tabs[section])
                    dialog.geometry(f'{min(960,app.winfo_screenwidth()-80)}x{min(760,app.winfo_screenheight()-100)}+20+20');app.update()
                    capture_client(dialog).save(Path('build')/f'phase4-{design}-{mode}-{index}.png')
                dialog.destroy();app.update();assert app.settings==before and CONFIG_FILE.read_bytes()==disk
                assert not errors,errors
        # Actual save updates the fake config and engine; queue rename reaches DB.
        did=app.add_download_from_dialog('https://example.invalid/file','fixture.bin',str(ensure_config_dir()/'fixture.bin'),auto_start=False)
        dialog=SettingsDialog(app);editor=dialog.content;old=app.settings['queues'][0]['name']
        editor.queue_editor.name.set('Synthetic renamed queue');editor.vars['default_connections'].set('12')
        with patch('modern_settings.save_settings',return_value=False):assert not editor.save()
        assert app.settings['queues'][0]['name']==old
        assert editor.save();app.update()
        assert app.engine.default_connections==12 and app.db.get_download(did)['queue_name']=='Synthetic renamed queue'
        assert json.loads(CONFIG_FILE.read_text(encoding='utf-8'))['default_connections']==12
        assert not errors,errors
        print('24 settings previews; bounds, dirty counts, isolated queue edits, backup restore without applying, cancel, failed save, real save and DB queue rename: OK')
    finally:app.engine.stop_engine();app.destroy()

if __name__=='__main__':main()
