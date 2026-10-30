"""F05 Yörünge detail window: Pano grid, mono captions, stripe metrics, synthetic task."""


def main():
    import time
    from pathlib import Path
    from unittest.mock import patch
    from PIL import ImageColor
    from gui import MainWindow
    from download_window import DownloadDetailDialog
    from download_engine import SegmentInfo
    from feature_ui import SpeedHistory
    from ui_surface import TextLabel
    from tools.window_capture import capture_client
    from utils import ensure_config_dir
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.apply_settings(dict(app.settings,design='yorunge',color_mode='dark',language='tr',download_dir=str(folder)))
    name='synthetic-f05-long-header-to-measure-the-actual-space-before-status.bin'
    did=app.add_download_from_dialog('https://example.invalid/f05',name,str(folder/name),auto_start=False)
    task=app.engine.get_task(did);task.filesize=1000000;task.supports_ranges=True;task.current_speed=50000;task.eta=15;task.status='İndiriliyor'
    segment=SegmentInfo(0,0,999999);segment.downloaded_bytes=250000;segment.connection_active=True;segment.status='İndiriliyor';task.segments=[segment]
    app.db.update_download_progress(did,250000,1000000);app.db.update_download_status(did,'İndiriliyor')
    history=app.speed_history[did]=SpeedHistory();history.sample(1,0,10000,True);history.sample(2,50000,50000,True)

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def snapshot(window,state):
        window.geometry('+30+30');settle();capture_client(window).save(Path(f'build/yorunge-details-{state}.png'))

    try:
        window=DownloadDetailDialog(app,app.db.get_download(did));app.detail_windows[did]=window;settle();content=window.content
        assert content.snapshot['progress']==.25 and content.ring.value==.25
        assert content.mean.get()=='48,83 KB/sn' and content.active_connections.get()=='1'
        widths=[card.winfo_width() for card in content.metric_cards]
        assert max(widths)-min(widths)<=1 and content.metric_cards[0].winfo_rooty()==content.metric_cards[1].winfo_rooty()
        assert content.progress_card.winfo_rooty()==content.speed_card.winfo_rooty()
        snapshot(window,'wide');image=capture_client(window).convert('RGB')
        # Metric boxes carry their F05 stripe: violet average, green peak.
        for card,key in zip(content.metric_cards,('violet','success')):
            x=card.winfo_rootx()-window.winfo_rootx()+1;y=card.winfo_rooty()-window.winfo_rooty()+card.winfo_height()//2
            assert sum(abs(a-b) for a,b in zip(image.getpixel((x,y)),ImageColor.getrgb(app.palette[key])))<30,('F05 metric stripe',key)
        # Only the progress panel is featured; the speed panel has no bracket.
        x=content.speed_card.winfo_rootx()-window.winfo_rootx()+6;y=content.speed_card.winfo_rooty()-window.winfo_rooty()
        assert sum(abs(a-b) for a,b in zip(image.getpixel((x,y)),ImageColor.getrgb(app.palette['accent'])))>60,'F05 speed panel bracket'
        with patch.object(app,'pause_download') as pause:
            window.pause_button.invoke();pause.assert_called_once_with(did)
        window.geometry('660x780+30+30');settle();snapshot(window,'compact')
        assert content.progress_card.winfo_rooty()<content.speed_card.winfo_rooty()<content.metric_cards[0].winfo_rooty()
        overflow=0
        for row in content.technical_card.content.winfo_children():
            if row.winfo_height()!=44:continue
            for child in row.winfo_children():
                if isinstance(child,TextLabel):overflow=max(overflow,child.winfo_rootx()+child.winfo_width()-row.winfo_rootx()-row.winfo_width())
        assert overflow<=0,'F05 technical row overflow'
        task.filesize=1000000;task.status='Tamamlandı';app.db.update_download_progress(did,1000000,1000000);app.db.update_download_status(did,'Tamamlandı')
        window.geometry('880x780+30+30');window.update_values();settle();assert content.ring.value==1 and window.pause_button.disabled
        snapshot(window,'completed')
        print('F05: Pano grid, stripe metrics, single featured panel, compact rows, completed state: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
