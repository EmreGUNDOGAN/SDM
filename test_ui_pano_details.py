"""P05 measured transfer data, wide/compact/unknown/completed; disposable profile."""


def main():
    import hashlib,json,time
    from pathlib import Path
    from unittest.mock import patch
    from PIL import ImageColor
    from gui import MainWindow
    from download_window import DownloadDetailDialog
    from download_engine import SegmentInfo
    from feature_ui import SpeedHistory
    from ui_surface import TextLabel
    from tools.window_capture import capture_client
    from tools.report_pano_details import SOURCES,STATES
    from utils import ensure_config_dir
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.apply_settings(dict(app.settings,design='pano',color_mode='light',language='tr',download_dir=str(folder)))
    name='synthetic-p05-long-header-to-measure-the-actual-space-before-status.bin'
    did=app.add_download_from_dialog('https://example.invalid/p05',name,str(folder/name),auto_start=False)
    task=app.engine.get_task(did);task.filesize=1000000;task.supports_ranges=True;task.current_speed=50000;task.eta=15;task.status='İndiriliyor'
    segment=SegmentInfo(0,0,999999);segment.downloaded_bytes=250000;segment.connection_active=True;segment.status='İndiriliyor';task.segments=[segment]
    app.db.update_download_progress(did,250000,1000000);app.db.update_download_status(did,'İndiriliyor')
    history=app.speed_history[did]=SpeedHistory();history.sample(1,0,10000,True);history.sample(2,50000,50000,True)
    data={}

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def snapshot(window,state):
        window.geometry('+30+30');settle();capture_client(window).save(Path(f'build/pano-details-{state}.png'))

    try:
        window=DownloadDetailDialog(app,app.db.get_download(did));app.detail_windows[did]=window;settle();content=window.content
        assert content.snapshot['progress']==.25 and content.ring.value==.25
        assert content.mean.get()=='48,83 KB/sn' and content.highest.get()=='48,83 KB/sn'
        assert content.active_connections.get()=='1' and content.values['connections'].get().startswith('1 aktif bağlantı')
        assert len(content.parts.rows)==1 and content.parts.rows[0][2]==(.25,)
        widths=[card.winfo_width() for card in content.metric_cards]
        data['metric_width_delta']=max(widths)-min(widths)
        data['metric_y_delta']=abs(content.metric_cards[0].winfo_rooty()-content.metric_cards[1].winfo_rooty())
        assert data['metric_width_delta']<=1 and data['metric_y_delta']==0
        assert content.progress_card.winfo_rooty()==content.speed_card.winfo_rooty()
        snapshot(window,'wide');image=capture_client(window).convert('RGB')
        x=content.ring.winfo_rootx()-window.winfo_rootx()+content.ring.winfo_width()-10
        y=content.ring.winfo_rooty()-window.winfo_rooty()+content.ring.winfo_height()-12
        expected=ImageColor.getrgb(app.palette['track'])
        assert sum(abs(a-b) for a,b in zip(image.getpixel((x,y)),expected))<25,'P05 horizontal progress track missing'
        with patch.object(app,'pause_download') as pause:
            window.pause_button.invoke();pause.assert_called_once_with(did)
        with patch.object(content,'clipboard_clear') as clear,patch.object(content,'clipboard_append') as copy:
            content.copy_url();clear.assert_called_once();copy.assert_called_once_with('https://example.invalid/p05')
        with patch('download_window.os.startfile') as open_folder:
            content.open_folder();open_folder.assert_called_once_with(str(folder))
        window.geometry('660x780+30+30');settle();snapshot(window,'compact')
        assert content.progress_card.winfo_rooty()<content.speed_card.winfo_rooty()<content.metric_cards[0].winfo_rooty()
        overflow=0
        for row in content.technical_card.content.winfo_children():
            if row.winfo_height()!=44:continue
            for child in row.winfo_children():
                if isinstance(child,TextLabel):overflow=max(overflow,child.winfo_rootx()+child.winfo_width()-row.winfo_rootx()-row.winfo_width())
        assert overflow<=0;data['technical_overflow']=overflow
        task.filesize=0;content.refresh();settle();assert content.ring.value is None
        window.geometry('880x900+30+30');settle();snapshot(window,'unknown')
        task.filesize=1000000;task.status='Tamamlandı';app.db.update_download_progress(did,1000000,1000000);app.db.update_download_status(did,'Tamamlandı')
        window.update_values();settle();assert content.ring.value==1 and window.pause_button.disabled
        assert window.cancel_button.text=='Kapat';snapshot(window,'completed')
        window.cancel_button.invoke();settle();assert did not in app.detail_windows and content.ring._timer is None
        data['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}
        data['previews']={state:hashlib.sha256(Path(f'build/pano-details-{state}.png').read_bytes()).hexdigest() for state in STATES}
        Path('build/pano-details-layout.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        print('P05: measured fraction/parts/connections, horizontal percent, equal metrics, compact rows, unknown/completed, pause/copy/open/close: OK')
    finally:app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
