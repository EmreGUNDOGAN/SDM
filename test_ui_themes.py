"""Six real layouts, filters, interactive state and persisted theme names."""
def main():
    import json
    from pathlib import Path
    from gui import MainWindow
    from modern_settings import SettingsDialog
    from theme_catalog import THEMES,theme_name
    app=MainWindow();app.engine.stop_engine();app.geometry('1080x640')
    app.settings['duplicate_warning']=False
    did=app.add_download_from_dialog('https://example.com/video','video.mkv',str(Path('build')/'video.mkv'),is_video=True,auto_start=False,section={'start':7200,'end':10800,'exact':False})
    assert json.loads(app.db.get_download(did)['options_json'])['section']['start']==7200
    for theme in THEMES:
        app.apply_settings(dict(app.settings,theme=theme));app.update()
        app.select_category('Video');app.update();assert len(app.tree.get_children())>=1
        if theme.startswith('orbit'):assert app.status_buttons['Tümü'].selected
        app.search_var.set('no-such-file-9f8a');app.update()
        assert not app.tree.get_children() and app.empty_label.winfo_ismapped() and app.empty_clear.winfo_ismapped()
        assert all(b.disabled for b in app.action_buttons)
        app.empty_clear.invoke();app.update();assert app.tree.get_children()
        app.tree.selection_set(app.tree.get_children()[0]);app.update();assert all(not b.disabled for b in app.action_buttons)
        assert all(b.winfo_ismapped() for b in app.action_buttons)
        assert all(b.winfo_rooty()+b.winfo_height()<=app.winfo_rooty()+app.winfo_height() for b in app.action_buttons)
        button=app.action_buttons[0];calls=[];original=button.command;button.command=lambda:calls.append(True)
        button.event_generate('<Enter>');app.update();assert button.hover
        button.event_generate('<ButtonPress-1>',x=10,y=10);app.update();assert button.pressed
        button.event_generate('<ButtonRelease-1>',x=10,y=10);app.update();assert not button.pressed and len(calls)==1
        button.command=original
        if theme.startswith('orbit'):
            app.select_status_filter('Tamamlananlar');assert not app.tree.get_children()
            app.select_status_filter('Tümü')
    dialog=SettingsDialog(app);app.update();dialog.vars['language'].set('en');app.update()
    dialog.theme_choice.set(theme_name('orbit_dark','en'));values=dialog.collect()
    assert values['theme']=='orbit_dark' and values['language']=='en'
    dialog.destroy()
    app.show_update_progress(68,100);app.update();assert app._update_panel.winfo_ismapped() and app._update_bar['value']==68
    app.update_failed('Fixture',quiet=True);assert not app._update_panel.winfo_exists()
    app.destroy();print('Six theme layouts, visible actions, combined filters, search reset, update progress and bilingual persisted names: OK')

if __name__=='__main__':main()
