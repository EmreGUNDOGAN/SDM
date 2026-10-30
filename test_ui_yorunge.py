"""F01/F02/F18/F19 native integration, only in a disposable profile."""


def main():
    import hashlib,json,time
    from pathlib import Path
    from unittest.mock import patch
    from types import SimpleNamespace
    from gui import MainWindow
    from download_engine import SegmentInfo
    from tools.window_capture import capture_client
    from utils import ensure_config_dir
    from tools.report_yorunge_previews import SOURCES,STATES
    import ui_indicators
    from yorunge_indicators import SpeedGauge
    from PIL import ImageColor
    instruments={};original_photo=ui_indicators.photo
    def record_photo(image,master):
        if isinstance(master,SpeedGauge):instruments[master]=image.convert('RGB')
        return original_photo(image,master)
    ui_indicators.photo=record_photo
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.settings.update(download_dir=str(folder),notifications_enabled=False,completion_popup=False,auto_open_details=False)
    measurements={}
    def settle():
        for _ in range(6):app.update();time.sleep(.025)
        assert not errors,errors
    def capture(name):
        settle();image=capture_client(app);image.save(Path('build')/f'yorunge-{name}.png');return image
    try:
        app.apply_settings(dict(app.settings,design='yorunge',color_mode='system'))
        app.geometry('1440x900+20+20');settle();view=app._atlas_workspace
        assert app.theme_family=='yorunge' and app.ui_theme=='dark' and app.settings['color_mode']=='system'
        assert type(view).__name__=='YorungeWorkspace'
        centre=app.search_control.winfo_rooty()+app.search_control.winfo_height()/2
        measurements['header_center_errors']=[abs(widget.winfo_rooty()+widget.winfo_height()/2-centre) for widget in (view.new_button,app.capture_label,app.search_control)]
        assert max(measurements['header_center_errors'])<=.5,measurements
        assert app.empty_label.text=='Henüz indirme yok' and view.system.winfo_ismapped()
        capture('empty')
        active=app.add_download_from_dialog('https://example.invalid/orbit-live','orbit-live-fixture.bin',str(folder/'orbit-live-fixture.bin'),auto_start=False)
        task=app.engine.get_task(active);task.status='İndiriliyor';task.filesize=1000000;task.current_speed=2621440;task.eta=11
        segment=SegmentInfo(0,0,999999);segment.downloaded_bytes=250000;task.segments=[segment]
        app.db.update_download_progress(active,250000,1000000);app.db.update_download_status(active,'İndiriliyor')
        paused=app.db.add_download('https://example.invalid/orbit-paused','orbit-paused-fixture.pdf',str(folder/'orbit-paused-fixture.pdf'),category='Belgeler',status='Duraklatıldı')
        complete=app.db.add_download('https://example.invalid/orbit-complete','orbit-complete-fixture.pdf',str(folder/'orbit-complete-fixture.pdf'),filesize=100,category='Belgeler',status='Tamamlandı')
        app.refresh_downloads();app.update_hud();settle()
        app.tree.selection_set(f'download-{active}');settle()
        assert view.target_snapshot['progress']==.25 and view.target_snapshot['id']==active
        assert view.primary.text=='Duraklat' and not view.primary.disabled
        with patch.object(app,'pause_selected') as action:
            view.update_selection();view.primary.invoke();action.assert_called_once()
        assert view.metrics['AKTİF'].text.startswith('1 / ')
        picture=capture_client(app);cell=app.tree.bbox(f'download-{active}','progress')
        x,y,w,h=cell;left=app.tree.winfo_rootx()-app.winfo_rootx()+x;middle=app.tree.winfo_rooty()-app.winfo_rooty()+y+h//2
        color=ImageColor.getrgb(app.palette['accent']);runs=0;inside=False
        for xx in range(left,left+w):
            matched=sum(abs(a-b) for a,b in zip(picture.getpixel((xx,middle))[:3],color))<50
            if matched and not inside:runs+=1
            inside=matched
        assert runs==5,('25% must have five separate lit cells',runs)
        measurements['active_progress_cells']=runs
        capture('main')
        app.tree.selection_set(f'download-{paused}');settle();assert view.primary.text=='Devam'
        app.tree.selection_set(f'download-{complete}');settle();assert view.primary.text=='Aç'
        app.tree.selection_set((f'download-{active}',f'download-{paused}'));settle()
        assert view.action_group.winfo_ismapped() and not view.actions['pause'].disabled and view.actions['folder'].disabled
        capture('selection')
        view.select_status('Tamamlananlar');settle();assert app.tree.get_children()==(f'download-{complete}',)
        view.select_status('Tümü');app.select_category('Belgeler');settle();assert len(app.tree.get_children())==2
        app.select_category('Tümü')
        with patch.object(app,'open_add_dialog') as add:
            app.search_var.set('https://example.invalid/orbit-complete');settle();add.assert_not_called()
        assert app.tree.get_children()==(f'download-{complete}',)
        app.search_var.set('no-orbit-match');settle();assert app.empty_label.text=='Aramanızla eşleşen indirme bulunamadı'
        app.empty_clear.invoke();settle();assert len(app.tree.get_children())==3
        app.tree.selection_set(f'download-{active}');settle()
        menu=view.context_menu(SimpleNamespace(x_root=500,y_root=350));settle()
        capture_client(menu).save('build/yorunge-menu.png');menu.close_root();settle()
        menu=view.queue_menu();settle();assert menu.items;menu.close_root();settle()
        with patch.object(app,'open_stats') as stats:
            view.bottom_buttons['İstatistik'].configure(command=app.open_stats);view.bottom_buttons['İstatistik'].invoke();stats.assert_called_once()
        for width,height in ((1080,640),(1440,900)):
            app.geometry(f'{width}x{height}+20+20');settle()
            assert view._compact==(width<1280)
            assert bool(view.right.winfo_ismapped())==(width>=1280)
            for widget in (view.gauge,view.chart_box):
                assert widget.winfo_y()+widget.winfo_height()<=view.telemetry.content.winfo_height(),('Telemetry clipped',widget)
            measurements['compact' if width==1080 else 'wide']=dict(viewport=[app.winfo_width(),app.winfo_height()],
                telemetry=[view.telemetry.winfo_width(),view.telemetry.winfo_height()],list=[view.list_card.winfo_width(),view.list_card.winfo_height()],right_visible=bool(view.right.winfo_ismapped()))
            if width==1080:
                assert view.action_group.winfo_ismapped(),'Compact selection actions lost'
                assert view.chart_box.grid_info()['row']==1
                view.scroll.yview_moveto(0);settle();picture=capture('compact-telemetry')
                footer=app.lbl_status_summary.master
                y=footer.winfo_rooty()-app.winfo_rooty()+footer.winfo_height()//2
                assert picture.getpixel((app.winfo_width()//2,y))[:3]==ImageColor.getrgb(app.palette['side']),'Off-screen actions cover the status footer'
                view.actions['pause'].focus_force();settle()
                button=view.actions['pause'];canvas=view.scroll._canvas
                assert app.focus_get() is button and canvas.winfo_rooty()<=button.winfo_rooty() and button.winfo_rooty()+button.winfo_height()<=canvas.winfo_rooty()+canvas.winfo_height(),'Compact action focus outside viewport'
                view.scroll.yview_moveto(1);settle();capture('compact')
            else:assert view.chart_box.grid_info()['row']==0
        view.scroll.yview_moveto(0);settle()
        view.gauge.set(60*1048576,60*1048576);assert view.gauge.limit==100
        image=instruments[view.gauge];w,h=image.size;desired=min(w/2-20,h-48)+14-38
        foreground=ImageColor.getrgb(app.palette['text'])
        rows=[y for y in range(max(0,int(desired-26)),min(h,int(desired+26))) if any(sum(abs(a-b) for a,b in zip(image.getpixel((x,y)),foreground))<45 for x in range(w//2-70,w//2+70))]
        assert rows,'Gauge number ink missing'
        measurements['gauge_center_error']=abs((min(rows)+max(rows))/2-desired)
        assert measurements['gauge_center_error']<=1.5,measurements
        toast=app.notify('Sentetik doğrulama','Geçici profil bildirimi',tone='success');settle();toast.pause()
        capture_client(toast).save('build/yorunge-toast.png');toast.close()
        measurements['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}
        measurements['previews']={state:hashlib.sha256(Path(f'build/yorunge-{state}.png').read_bytes()).hexdigest() for state in STATES}
        Path('build/yorunge-layout.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
        assert not errors,errors
        print('Yörünge: selection/actions/filters/search/stats, wide/compact telemetry, real task fraction, menus and toast: OK')
    finally:ui_indicators.photo=original_photo;app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
