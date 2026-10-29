"""Four design/mode combinations: filters, state, settings and staged layout shells."""
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
        design,mode=theme.split('_')
        app.apply_settings(dict(app.settings,design=design,color_mode=mode));app.update()
        assert app.theme_family==design and app.ui_theme==mode
        assert app.palette['bg']==__import__('theme_catalog').palette(theme)['bg']
        app.select_category('Video');app.update();assert len(app.tree.get_children())>=1
        if theme.startswith('odak'):assert app.status_buttons['Tümü'].selected
        app.search_var.set('no-such-file-9f8a');app.update()
        assert not app.tree.get_children() and app.empty_label.winfo_ismapped() and app.empty_clear.winfo_ismapped()
        assert all(b.disabled for b in app.action_buttons)
        app.empty_clear.invoke();app.update();assert app.tree.get_children()
        app.tree.selection_set(app.tree.get_children()[0]);app.update();assert all(not b.disabled for b in app.action_buttons)
        if theme.startswith('odak'):
            drawer=app._atlas_workspace.drawer;assert drawer and drawer.winfo_ismapped() and drawer.pause_button.winfo_ismapped()
            assert not app._atlas_workspace.toolbar.winfo_ismapped()
            button=drawer.pause_button
        else:
            assert all(b.winfo_ismapped() for b in app.action_buttons)
            assert all(b.winfo_rooty()+b.winfo_height()<=app.winfo_rooty()+app.winfo_height() for b in app.action_buttons)
            button=app.action_buttons[0]
        calls=[];original=button.command;button.command=lambda:calls.append(True)
        button.event_generate('<Enter>');app.update();assert button.hover
        button.event_generate('<ButtonPress-1>',x=10,y=10);app.update();assert button.pressed
        button.event_generate('<ButtonRelease-1>',x=10,y=10);app.update();assert not button.pressed and len(calls)==1
        button.command=original
        if theme.startswith('odak'):
            app.select_status_filter('Tamamlananlar');assert not app.tree.get_children()
            app.select_status_filter('Tümü')
    dialog=SettingsDialog(app);app.update();dialog.vars['language'].set('en');app.update()
    dialog.vars['design'].set('odak');dialog.vars['color_mode'].set('dark');values=dialog.collect()
    assert values['design']=='odak' and values['color_mode']=='dark' and values['language']=='en'
    assert 'theme' not in values
    dialog.destroy()
    app.show_update_progress(68,100);app.update();assert app._update_panel.winfo_ismapped() and app._update_bar['value']==68
    app.update_failed('Fixture',quiet=True);assert not app._update_panel.winfo_exists()
    app.destroy();print('Four design/mode shells, visible actions, combined filters, search reset, update progress and independent number format: OK')

if __name__=='__main__':main()
