"""B01–B07 native interactions with synthetic data in a disposable profile."""
def main():
    import time
    from pathlib import Path
    from gui import MainWindow
    from utils import ensure_config_dir,save_settings
    from tools.window_capture import capture_client
    from ui_overlays import MessageDialog
    app=MainWindow();app.engine.stop_engine();errors=[];app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.settings.update(download_dir=str(folder),duplicate_warning=False,auto_open_details=False,completion_popup=False,notifications_enabled=False)
    save_settings(app.settings)
    ids=[]
    for i in range(24):
        name=f'Synthetic {i:02}.mkv' if i%2 else f'Synthetic {i:02}.zip'
        did=app.add_download_from_dialog(f'https://example.invalid/{i}',name,str(folder/name),auto_start=False,expected_size=1000000)
        task=app.engine.get_task(did);task.status=('Kuyrukta','Duraklatıldı','Tamamlandı','Hata')[i%4];app.db.update_download_status(did,task.status);ids.append(did)
    width=min(1440,app.winfo_screenwidth()-100);height=min(900,app.winfo_screenheight()-100)
    app.minsize(min(1080,width),min(640,height))
    def shot(name,mode,window=None):
        app.update();capture_client(window or app).save(Path('build')/f'phase5-odak-{mode}-{name}.png')
    def answer(key):
        dialog=next(w for w in app.winfo_children() if isinstance(w,MessageDialog));dialog.actions[key].invoke()
    try:
        for mode in ('light','dark'):
            app.apply_settings(dict(app.settings,design='odak',color_mode=mode,language='tr'));app.geometry(f'{width}x{height}+20+20');app.select_category('Tümü');app.select_status_filter('Tümü');app.update()
            w=app._atlas_workspace;assert w.rail.winfo_width()==68 and len(app.tree.get_children())==24
            assert app.data_view._image.height()==app.data_view.winfo_height() and app.data_view._image.width()==app.data_view.winfo_width()
            assert list(w.rail_buttons)==['downloads','queues','video','tools','stats','hud','settings']
            shot('main',mode)
            w.sort.set('name');app.refresh_downloads();app.update()
            assert [int(app.tree.item(item,'values')[0]) for item in app.tree.get_children()]==ids
            app.tree.yview_moveto(.4);app.update();before=app.tree.yview();image=app.data_view._image;rows=app.tree.get_children()
            app.refresh_downloads();app.update();assert app.tree.yview()==before and app.tree.get_children()==rows and app.data_view._image is image
            # Establish the closed-drawer baseline before comparing list widths.
            # A pre-existing selection on the shared desktop may already open it.
            app.tree.selection_remove(app.tree.selection());app.update()
            assert w.drawer is None,'Selection reset must close the previous drawer'
            app.tree.yview_moveto(0);app.update();item=app.tree.get_children()[0];box=app.tree.bbox(item);old_width=app.data_view.winfo_width()
            app.data_view.event_generate('<Button-1>',x=100,y=box[1]+32);app.update()
            assert w.drawer and w.drawer.download_id==ids[0],'Click must open the first download'
            assert w.drawer.winfo_width()==460,('Drawer width',w.drawer.winfo_width())
            assert app.data_view.winfo_width()<old_width,('List must shrink',old_width,app.data_view.winfo_width())
            assert app.detail_windows[ids[0]] is w.drawer;shot('drawer',mode)
            # Synthetic key events require a focused Tk app on a shared desktop.
            app.focus_force();app.update();assert app.focus_get() is app
            app.event_generate('<Escape>');app.update();assert w.drawer is None
            app.tree.selection_remove(app.tree.selection());app.update()
            app.show_download_details(ids[0]);app.update_action_states();app.update()
            assert app.tree.selection()==('download-'+str(ids[0]),) and w.drawer and ids[0] in app.detail_windows
            app.show_selected_details();app.update();assert w.drawer and w.drawer.download_id==ids[0]
            app.tree.selection_set(app.tree.get_children()[:3]);app.update();assert w.drawer is None and w.toolbar.winfo_ismapped()
            assert all(b.winfo_ismapped() for b in app.action_buttons);shot('multi',mode)
            # Native Ctrl/Shift semantics on the card overlay, then A18 menu.
            app.tree.selection_remove(app.tree.selection());app.update();box=app.tree.bbox(item)
            app.data_view.event_generate('<Button-1>',x=100,y=box[1]+32);app.update()
            next_item=app.tree.get_children()[1];box=app.tree.bbox(next_item)
            app.data_view.event_generate('<Button-1>',x=100,y=box[1]+32,state=4);app.update();assert len(app.tree.selection())==2
            third=app.tree.get_children()[2];box=app.tree.bbox(third)
            app.data_view.event_generate('<Button-1>',x=100,y=box[1]+32,state=1);app.update();assert len(app.tree.selection())==3
            w.navigate('queues');app.update();menu=w.menu
            assert menu.winfo_rootx()>=w.rail.winfo_rootx()+68 and abs(menu.winfo_rooty()-w.rail_buttons['queues'].winfo_rooty())<5
            shot('queue',mode,menu);menu.close_root()
            w.navigate('settings');app.update();editor=w.settings_page;assert editor and editor.embedded
            original=app.settings['language'];editor.vars['language'].set('en');app.update();assert editor.change_count.get()==1
            app.after(100,lambda:answer('cancel'));w.navigate('downloads');assert w.settings_page is editor and app.settings['language']==original
            shot('settings',mode)
            app.after(100,lambda:answer('discard'));w.navigate('downloads');app.update();assert w.settings_page is None and app.settings['language']==original
            w.navigate('settings');w.settings_page.vars['language'].set('en')
            app.after(100,lambda:answer('save'));w.navigate('downloads');app.update();assert app.settings['language']=='en' and not w.alive
            w=app._atlas_workspace;assert w.settings_page is None
            app.search_var.set('no-match-synthetic');app.update();assert not app.tree.get_children() and app.empty_clear.winfo_ismapped();shot('empty',mode)
            app.empty_clear.invoke();app.update();assert len(app.tree.get_children())==24
            w.navigate('hud');app.update();assert app._mini_hud and app._mini_hud.winfo_exists()
            w.navigate('hud');app.update();assert app._mini_hud is None
            assert not errors,errors
        print('Odak rail/cards, stable rows/scroll/image, sort, click/drawer, Ctrl/Shift multi, adjacent queue menu, actual Save/Discard/Cancel guard, HUD toggle and 12 native previews: OK')
    finally:app.engine.stop_engine();app.destroy()

if __name__=='__main__':main()
