"""A01/A02/A18 on real Tk widgets, only through the disposable-profile runner."""
def main():
    import os
    import time
    import tkinter as tk
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import patch
    from PIL import ImageColor
    from gui import MainWindow
    from download_engine import SegmentInfo
    from tools.window_capture import capture_client
    from atlas_view import DEFAULT_COLUMNS
    from utils import ensure_config_dir,save_settings
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.settings.update(auto_open_details=False,completion_popup=False,notifications_enabled=False,download_dir=str(folder))
    app.settings['queues'].append(dict(app.settings['queues'][0],name='Gece denemesi'))
    save_settings(app.settings)
    wide=min(int(os.environ.get('SDM_ATLAS_VIEWPORT_WIDTH','1440')),app.winfo_screenwidth()-100)
    tall=min(int(os.environ.get('SDM_ATLAS_VIEWPORT_HEIGHT','900')),app.winfo_screenheight()-100)
    small=min(1080,wide)
    # CI's 1024px desktop is smaller than the product's 1080px minimum. Only the
    # test process lowers that minimum, exercising an additional narrow viewport.
    app.minsize(min(1080,wide),min(640,tall))
    did=app.add_download_from_dialog('https://example.invalid/transfer','fixture-range.zip',str(folder/'fixture-range.zip'),connections=32,auto_start=False)
    task=app.engine.get_task(did);task.filesize=1000000;task.supports_ranges=True
    first=SegmentInfo(0,0,499999);first.downloaded_bytes=150000;first.connection_active=True;first.status='İndiriliyor'
    second=SegmentInfo(1,500000,999999);second.downloaded_bytes=50000;second.status='Duraklatıldı'
    task.segments=[first,second];task.status='İndiriliyor';task.current_speed=12345;task.eta=65
    app.db.update_download_progress(did,200000,1000000);app.db.update_download_status(did,'İndiriliyor')
    fixtures=[]
    for name,category,status in (('fixture-note.pdf','Belgeler','Tamamlandı'),('fixture-picture.png','Resimler','İptal Edildi'),('fixture-audio.mp3','Müzik','Duraklatıldı'),('fixture-video.mp4','Video','Hata'),('fixture-program.exe','Programlar','Kuyrukta'),('fixture-text.txt','Belgeler','Bekliyor')):
        key=app.db.add_download('https://example.invalid/'+name,name,str(folder/name),filesize=1000000,category=category,status=status)
        fixtures.append(key)
    app.db.set_queue(fixtures[-2],'Gece denemesi')
    def wait(predicate):
        deadline=time.monotonic()+3
        while not predicate():
            assert time.monotonic()<deadline,'Tk condition timed out'
            app.update();time.sleep(.01)
        app.update()
    def choose(key):
        app.tree.selection_set('download-'+str(key));app.tree.focus('download-'+str(key));app.tree.focus_set();app.update()
    def shot(mode,state,target=None):
        target=target or app;app.update();image=capture_client(target)
        if target is app:
            assert image.getpixel((10,10))==ImageColor.getrgb(app.palette['side'])
            assert image.getpixel((250,10))==ImageColor.getrgb(app.palette['bg'])
        image.save(Path('build')/f'phase2-atlas-{mode}-{state}.png')
    try:
        for mode in ('light','dark'):
            app.current_category='Tümü';app.current_status_filter='Tümü';app.current_queue_filter=None
            app.apply_settings(dict(app.settings,design='atlas',color_mode=mode));app.geometry(f'{wide}x{tall}+20+20');app.update()
            workspace=app._atlas_workspace;assert workspace.alive
            assert len(app.tree.get_children())==7,(mode,app.current_category,app.current_status_filter,len(app.tree.get_children()))
            assert app.status_buttons['Tümü'].count=='7'
            assert list(workspace.bottom_buttons)==['Araçlar','İstatistik','Masaüstü HUD','Ayarlar']
            assert tuple(app.tree.cget('displaycolumns'))==DEFAULT_COLUMNS
            assert not workspace.details.winfo_ismapped()
            choose(did);wait(lambda:workspace.details.winfo_ismapped())
            assert workspace.details.snapshot['active_count']==1
            assert len(workspace.details.snapshot['rows'])==2
            assert abs(workspace.details.snapshot['progress']-.2)<1e-9
            assert workspace.details.snapshot['received']==200000
            assert app.tree.winfo_rootx()+app.tree.winfo_width()<=workspace.details.winfo_rootx()
            assert workspace.actions['resume'].disabled and not workspace.actions['pause'].disabled
            app.focus_force();workspace.focus_search();app.update();assert app.focus_get() is app.search_control.entry
            with patch.object(app,'delete_selected') as remove:
                app.search_control.entry.event_generate('<Delete>');app.update();remove.assert_not_called()
            app.search_var.set('example.invalid/fixture-note');app.update();assert len(app.tree.get_children())==1
            app.search_var.set('');app.update();choose(did)
            # Repeated refreshes must keep actual row identity, focus and selection.
            row=app.tree.selection()[0];app.tree.focus(row)
            image_before=str(app.data_view._image)
            for _ in range(3):app.refresh_downloads();app.update()
            assert app.tree.selection()==(row,) and app.tree.focus()==row
            assert str(app.data_view._image)==image_before and len(app.data_view.find_all())==1
            shot(mode,'main')
            app.select_status_filter('Hatalı');app.update();assert len(app.tree.get_children())==2
            app.select_category('Video');app.update();assert len(app.tree.get_children())==1
            assert 'Video' in app.page_title.get() and 'Hatalı' in app.page_title.get()
            app.select_category('Belgeler');app.update();assert not app.tree.get_children()
            assert app.empty_label.text=='Bu görünümde henüz indirme yok'
            app.select_status_filter('Tümü');app.select_category('Tümü');app.update()
            workspace.select_queue('Gece denemesi');app.update();assert len(app.tree.get_children())==1
            app.select_category('Tümü');app.update();choose(did)
            # Right click on a member of a multi-selection must retain the group.
            app.tree.selection_set(('download-'+str(did),'download-'+str(fixtures[0])));app.update()
            box=app.tree.bbox('download-'+str(did));event=SimpleNamespace(x=20,y=box[1]+10,x_root=app.tree.winfo_rootx()+20,y_root=app.tree.winfo_rooty()+box[1]+10,state=0)
            app.data_view.context(event);app.update()
            assert len(app.tree.selection())==2 and workspace.details.snapshot['title']=='2 öğe seçili'
            menu=workspace.menu;assert len(menu.items)==13
            assert menu.items[0]['button'].disabled and menu.items[10]['button'].disabled
            shot(mode,'menu',menu);menu.close_root();app.update();shot(mode,'multi')
            choose(fixtures[0]);assert workspace.actions['resume'].disabled and workspace.actions['pause'].disabled
            assert workspace.capabilities()['verify'] and workspace.capabilities()['open']
            menu=workspace.column_menu();app.update()
            filename=next(item for item in menu.items if item['button'].text=='Dosya Adı')
            assert filename['button'].disabled and filename['variable'].get()
            downloaded=next(i for i,item in enumerate(menu.items) if item['button'].text=='İndirilen')
            menu.activate(downloaded);app.update();assert 'downloaded' in app.tree.cget('displaycolumns')
            workspace.reset_columns();assert tuple(app.tree.cget('displaycolumns'))==DEFAULT_COLUMNS
            workspace.extension_help();app.update()
            from modern_settings import SettingsDialog
            dialog=next(child for child in reversed(app.winfo_children()) if isinstance(child,SettingsDialog))
            assert dialog.tabs['Tarayıcı'].master.select()==str(dialog.tabs['Tarayıcı']);dialog.destroy()
            menu=workspace.queue_menu();app.update();menu.activate(len(menu.items)-1);app.update()
            dialog=next(child for child in reversed(app.winfo_children()) if isinstance(child,SettingsDialog))
            assert dialog.tabs['Kuyruk'].master.select()==str(dialog.tabs['Kuyruk']);dialog.destroy()
            menu=workspace.queue_menu();app.update();assert menu.child_menu is None
            menu.event_generate('<Down>');app.update();assert menu.active==1 and menu.child_menu is None
            menu.event_generate('<Right>');app.update()
            assert menu.child_menu and menu.child_menu.items[0]['button'].text=='Başlat'
            menu.child_menu.event_generate('<Left>');app.update();assert not menu.child_menu.winfo_exists()
            menu.event_generate('<Right>');app.update()
            with patch.object(app,'start_queue') as start:
                menu.child_menu.activate(0);app.update();start.assert_called_once_with('Gece denemesi')
            # Preview the minimum layout with a selected row and no control overlap.
            app.geometry(f'{small}x640+20+20');app.update();choose(did)
            buttons=list(workspace.actions.values())+[workspace.queue_button,app.relax_button,workspace.columns_button]
            for button in buttons:
                assert button.winfo_ismapped()
                assert app.winfo_rootx()<=button.winfo_rootx()<button.winfo_rootx()+button.winfo_width()<=app.winfo_rootx()+app.winfo_width()
            bounds=sorted((button.winfo_rootx(),button.winfo_rootx()+button.winfo_width()) for button in buttons)
            assert all(left[1]<=right[0] for left,right in zip(bounds,bounds[1:])),bounds
            shot(mode,'compact')
            # Exercise scroll preservation with more rows than fit, then restore
            # the small synthetic dataset used by the remaining acceptance cases.
            filler=[]
            for index in range(24):
                name=f'scroll-fixture-{index}.bin'
                filler.append(app.db.add_download('https://example.invalid/'+name,name,str(folder/name),status='Kuyrukta'))
            app.refresh_downloads();app.update();app.tree.yview_moveto(.5);app.tree.xview_moveto(.25);app.update()
            scroll=(app.tree.yview()[0],app.tree.xview()[0]);app.refresh_downloads();app.update()
            assert scroll==(app.tree.yview()[0],app.tree.xview()[0]),(scroll,app.tree.yview(),app.tree.xview())
            for key in filler:app.db.delete_download(key)
            app.refresh_downloads();app.update()
            app.search_var.set('not-a-fixture-0f129');app.update()
            assert app.empty_label.text=='Aramanızla eşleşen indirme bulunamadı' and app.empty_clear.winfo_ismapped()
            assert not workspace.toolbar.winfo_ismapped() and not workspace.details.winfo_ismapped()
            app.empty_clear.invoke();app.update();assert len(app.tree.get_children())==7
            with patch.object(app,'open_add_dialog') as add,patch.object(app,'clipboard_get',return_value='https://example.invalid/paste'):
                workspace.paste();add.assert_called_once_with('https://example.invalid/paste')
            for i in range(4):app.notify('Sahte bildirim',str(i))
            app.update();assert len(workspace.toast_manager.toasts)==3
            workspace.toast_manager.close()
            with patch('gui.messagebox.showerror') as error,patch('tkinter.simpledialog.askstring',return_value='wrong'):
                app.show_hash('fixture.txt','correct');error.assert_called_once()
            assert not errors,errors
            # Empty-all and empty-category are distinct from empty search.
            if mode=='dark':
                for record in app.db.get_all_downloads():app.db.delete_download(record['id'])
            else:
                # Hide all records using an empty category for the empty preview;
                # the true-empty branch is exercised after clearing dark's DB.
                app.select_category('Diğer')
            app.geometry(f'{wide}x{tall}+20+20');app.refresh_downloads();app.update()
            if mode=='dark':assert app.empty_label.text=='Henüz indirme yok'
            shot(mode,'empty')
        assert not errors,errors
        print('Atlas A01/A02/A18: filters/counts, actual parts, stable rows, panel/multi-selection, keyboard, menus, persisted columns, bounded previews and toast cleanup: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
