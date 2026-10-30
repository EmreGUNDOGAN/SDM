"""Native Pano integration; invoked only with a disposable SDM_DATA_DIR."""
def main():
    import hashlib,json
    import time
    from pathlib import Path
    from unittest.mock import patch,Mock
    from gui import MainWindow
    from download_engine import SegmentInfo
    from tools.window_capture import capture_client
    from utils import ensure_config_dir
    import ui_surface,ui_indicators
    from layout_pano import PanoCount
    from ui_overlays import MenuButton,PopupMenu
    from theme_widgets import Button
    from ui_indicators import SpeedChart
    from tools.report_pano_previews import SOURCES,STATES
    from PIL import ImageColor

    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.settings.update(download_dir=str(folder),notifications_enabled=False,
        completion_popup=False,auto_open_details=False)
    measurements={}
    count_images={};menu_images={};chart_images={};original_photo=ui_surface.photo
    original_indicator_photo=ui_indicators.photo
    def record_photo(image,master):
        if isinstance(master,PanoCount):count_images[master]=image.convert('RGB')
        if isinstance(master,MenuButton):menu_images[master]=image.convert('RGB')
        if isinstance(master,SpeedChart):chart_images[master]=image.convert('RGB')
        return original_photo(image,master)
    ui_surface.photo=record_photo
    ui_indicators.photo=record_photo

    def settle():
        for _ in range(8):app.update();time.sleep(.025)
        assert not errors,errors

    def capture(name):
        settle();capture_client(app).save(Path('build')/f'pano-{name}.png')

    def visible_bounds(parent,children):
        for child in children:
            assert child.winfo_ismapped(),str(child)
            x=child.winfo_rootx()-parent.winfo_rootx();y=child.winfo_rooty()-parent.winfo_rooty()
            assert x>=0 and y>=0,(str(child),x,y)
            assert x+child.winfo_width()<=parent.winfo_width(),(str(child),'right')
            assert y+child.winfo_height()<=parent.winfo_height(),(str(child),'bottom')

    try:
        app.apply_settings(dict(app.settings,design='pano',color_mode='system'))
        wide=min(1440,app.winfo_screenwidth()-60);tall=min(900,app.winfo_screenheight()-80)
        app.geometry(f'{wide}x{tall}+20+20');settle()
        workspace=app._atlas_workspace
        workspace.chart.set(((0,1),(1,1)));settle()
        chart=chart_images[workspace.chart]
        assert chart.getpixel((chart.width//2,chart.height-5))!=ImageColor.getrgb(app.palette['panel']),'Pano area fill missing'
        assert app.theme_family=='pano' and app.ui_theme=='light'
        assert app.settings['color_mode']=='system'
        assert tuple(app.tree.cget('displaycolumns'))==('filename','progress','size','status','actions')
        assert app.empty_label.text=='Henüz indirme yok'
        capture('empty')
        active=app.add_download_from_dialog('https://example.invalid/pano-active','pano-live-fixture.bin',str(folder/'pano-live-fixture.bin'),auto_start=False)
        task=app.engine.get_task(active);task.status='İndiriliyor';task.filesize=1000000
        task.current_speed=16384;task.eta=11
        segment=SegmentInfo(0,0,999999);segment.downloaded_bytes=250000
        task.segments=[segment]
        app.db.update_download_progress(active,250000,1000000);app.db.update_download_status(active,'İndiriliyor')
        complete=app.db.add_download('https://example.invalid/pano-complete','pano-finished-fixture.pdf',str(folder/'pano-finished-fixture.pdf'),filesize=100,category='Belgeler',status='Tamamlandı')
        queued=app.db.add_download('https://example.invalid/pano-queued','pano-queued-fixture.bin',str(folder/'pano-queued-fixture.bin'),status='Kuyrukta')
        app.refresh_downloads();app.update_hud();settle()
        assert workspace.current_id==active
        assert workspace.current_percent.text=='25%'
        assert len(app.tree.get_children())==3
        count_errors=[]
        foreground=ImageColor.getrgb(app.palette['text'])
        for button,_ in workspace.summary_buttons.values():
            image=count_images[button]
            rows=[y for y in range(4,44) if any(sum(abs(a-b) for a,b in zip(image.getpixel((x,y)),foreground))<70 for x in range(5,image.width-5))]
            assert rows,'Count ink missing'
            error=abs((min(rows)+max(rows))/2-26);count_errors.append(error)
            assert error<=1.5,('Pano count not centred',button.caption,error)
        measurements['count_center_errors']=count_errors
        assert workspace.filters.winfo_manager()=='pack'
        # Header search remains search even for a valid URL.
        with patch.object(app,'open_add_dialog') as add:
            app.search_var.set('https://example.invalid/pano-complete');settle()
            add.assert_not_called();assert len(app.tree.get_children())==1
        app.search_var.set('');app.refresh_downloads();settle()
        app.tree.selection_set((f'download-{complete}',f'download-{queued}'));settle()
        assert not workspace.filters.winfo_manager()
        assert workspace.action_group.winfo_manager()=='pack'
        assert workspace.actions['folder'].disabled
        selection=app.tree.selection()
        with patch.object(app,'pause_download') as pause:
            workspace.current_pause.invoke();pause.assert_called_once_with(active)
        assert app.tree.selection()==selection
        app.tree.selection_remove(selection);settle()
        assert workspace.filters.winfo_manager()=='pack'
        workspace.select_status('Tamamlananlar');settle()
        assert app.tree.get_children()==(f'download-{complete}',)
        app.db.update_download_status(queued,'Duraklatıldı')
        workspace.select_status('Duraklatılanlar');settle()
        assert app.tree.get_children()==(f'download-{queued}',)
        workspace.select_status('Hatalı');settle();assert not app.tree.get_children()
        app.db.update_download_status(queued,'Kuyrukta')
        workspace.select_status('Tümü');settle()
        app.search_var.set('no-pano-fixture-matches');settle()
        assert app.empty_label.text=='Aramanızla eşleşen indirme bulunamadı'
        app.empty_clear.invoke();settle()
        assert len(app.tree.get_children())==3
        with patch.object(app,'start_queue') as start:
            workspace.queue_start_buttons[app.settings['queues'][0]['name']].invoke()
            start.assert_called_once_with(app.settings['queues'][0]['name'])
        workspace.scroll.yview_moveto(0);settle()
        visible_bounds(workspace.hero.content,[workspace.current_name.master.master,
            workspace.current_percent.master,workspace.current_progress,workspace.current_metrics['Hız'].master.master,
            workspace.current_details.master])
        for value in (workspace.current_name,workspace.current_subtitle,workspace.current_percent,*workspace.current_metrics.values()):
            assert value.winfo_height()>=value.winfo_reqheight(),('clipped text height',value)
            assert value.winfo_width()>=value.winfo_reqwidth(),('clipped text width',value)
        baselines=[value.winfo_rooty() for value in workspace.current_metrics.values()]
        assert max(baselines)-min(baselines)<=1.5,baselines
        measurements['metric_baseline_spread']=max(baselines)-min(baselines)
        assert workspace.disk_progress.winfo_ismapped(),'Disk usage bar clipped'
        measurements['wide']={'viewport':[app.winfo_width(),app.winfo_height()],
            'hero':[workspace.hero.winfo_width(),workspace.hero.winfo_height()],
            'list':[workspace.list_card.winfo_width(),workspace.list_card.winfo_height()]}
        capture('main')
        for width,height in ((1080,640),(wide,tall)):
            app.geometry(f'{width}x{height}+20+20');settle()
            assert workspace._layout==(width<1280)
            assert workspace.hero.grid_info()['columnspan']==2
            assert workspace.list_card.grid_info()['columnspan']==(2 if width<1280 else 3)
            # No two tiles overlap after a responsive reflow.
            cards=(workspace.hero,workspace.speed_card,workspace.summary_card,workspace.disk_card,workspace.list_card,workspace.navigation_card)
            for index,left in enumerate(cards):
                for right in cards[index+1:]:
                    overlap_x=min(left.winfo_x()+left.winfo_width(),right.winfo_x()+right.winfo_width())-max(left.winfo_x(),right.winfo_x())
                    overlap_y=min(left.winfo_y()+left.winfo_height(),right.winfo_y()+right.winfo_height())-max(left.winfo_y(),right.winfo_y())
                    assert overlap_x<=0 or overlap_y<=0,('overlapping tiles',left,right)
            if width==1080:
                assert workspace.hero.winfo_width()>=workspace.dashboard.winfo_width()-16,'Compact hero is not full width'
                assert workspace.list_card.winfo_width()>=workspace.dashboard.winfo_width()-16,'Compact list is not full width'
                capture('compact')
                measurements['compact']={'viewport':[app.winfo_width(),app.winfo_height()],
                    'hero':[workspace.hero.winfo_width(),workspace.hero.winfo_height()],
                    'list':[workspace.list_card.winfo_width(),workspace.list_card.winfo_height()]}
        workspace.scroll.yview_moveto(1);settle()
        app.tree.selection_set((f'download-{active}',f'download-{queued}'));settle()
        capture('selection')
        item=f'download-{active}';app.tree.see(item);settle()
        box=app.tree.bbox(item,'actions');assert box
        app.data_view.event_generate('<Button-1>',x=box[0]+box[2]//2,y=box[1]+box[3]//2);settle()
        assert len(app.tree.selection())==2,'Row menu lost the multi-selection'
        assert len(workspace.menu.items)==13
        assert workspace.menu.items[0]['button'].disabled
        capture_client(workspace.menu).save(Path('build/pano-menu.png'))
        workspace.menu.close_root();settle()
        app.tree.selection_remove(app.tree.selection());settle()
        before=str(app.data_view._image)
        for _ in range(3):app.refresh_downloads();settle()
        assert str(app.data_view._image)==before
        assert len(app.data_view.find_all())==1
        original=app.settings['visible_columns'][:]
        menu=workspace.column_menu();settle()
        speed=next(i for i,item in enumerate(menu.items) if item['button'].text=='Hız')
        menu.activate(speed);settle()
        assert 'speed' in app.settings['pano_visible_columns']
        assert app.settings['visible_columns']==original
        # P18 uses the shared popup's keyboard/focus behavior with Pano's card palette.
        import tkinter as tk
        variable=tk.StringVar(app,'normal')
        menu=PopupMenu(app,app.palette)
        radio=menu.add_item('Normal',variable=variable,value='normal')
        danger=menu.add_item('Sahte dosyayı kaldır',Mock(),danger=True)
        menu.popup(60,60);settle()
        assert menu.panel.radius==20
        assert menu.panel.content.cget('bg')==app.palette['bg']
        radio_image=menu_images[radio]
        assert radio_image.getpixel((1,radio_image.height-2))==ImageColor.getrgb(app.palette['card']),'Menu group is split between adjacent rows'
        assert radio_image.getpixel((radio_image.width//2,radio_image.height-4))==ImageColor.getrgb(app.palette['accent'])
        danger_image=menu_images[danger]
        assert danger_image.getpixel((danger_image.width//2,danger_image.height-4))==ImageColor.getrgb(app.palette['danger_bg'])
        capture_client(menu).save(Path('build/pano-radio-menu.png'))
        menu.close_root();settle()
        # P19 retains bounded stacking, hover timer pause and explicit action dispatch.
        for index in range(4):app.notify('Sahte Pano bildirimi',f'Deneme {index}',tone='success')
        settle();assert len(workspace.toast_manager.toasts)==3
        workspace.toast_manager.close()
        from ui_overlays import ToastManager
        workspace.toast_manager=ToastManager(app,app.palette,workspace.desktop_notify)
        action=Mock()
        toast=workspace.toast_manager.show('Sahte bildirim','Gerçek dosyalar değiştirilmez.',('Geri al',action),tone='success')
        settle();assert toast.pano_panel.radius==20
        toast.pause();assert toast._timer is None
        toast.resume();assert toast._timer is not None
        capture_client(toast).save(Path('build/pano-toast.png'))
        button=next(child for child in toast.pano_panel.content.winfo_children() if isinstance(child,Button))
        button.invoke();settle();action.assert_called_once()
        assert not workspace.toast_manager.toasts
        workspace.reset_columns();settle()
        assert tuple(app.tree.cget('displaycolumns'))==('filename','progress','size','status','actions')
        assert app.settings['visible_columns']==original
        assert not errors,errors
        measurements['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}
        measurements['previews']={state:hashlib.sha256((Path('build')/f'pano-{state}.png').read_bytes()).hexdigest() for state in STATES}
        Path('build/pano-layout.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
        print('Pano: live card, explicit pause target, URL search, selection actions, filters, stable rows and tile geometry: OK')
    finally:
        ui_surface.photo=original_photo
        ui_indicators.photo=original_indicator_photo
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
