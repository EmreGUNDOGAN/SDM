"""F15 Yörünge HUD: one bracketed panel, 30 tiles, no file list, three text sizes."""


def main():
    import time
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import patch,Mock
    import ttkbootstrap as tb
    from feature_windows import MiniHUD
    from theme_catalog import palette
    from ui_tokens import HUD_TEXT_SIZES
    from tools.window_capture import capture_client
    from utils import ensure_config_dir,load_settings
    app=tb.Window();app.withdraw();errors=[]
    app.palette=palette('yorunge_dark');app.settings=load_settings();app._mini_hud=None
    app.db=SimpleNamespace(get_all_downloads=Mock());app.engine=SimpleNamespace(get_total_speed=Mock())
    app.pause_download=Mock()
    def show_hud():app._mini_hud=MiniHUD(app)
    app.show_mini_hud=show_hud
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.settings.update(design='yorunge',color_mode='dark',download_dir=str(folder))
    rows=[dict(id=1,status='İndiriliyor',filename='synthetic-first.bin',filesize=1000000,downloaded_bytes=250000),
          dict(id=2,status='Dönüştürülüyor',filename='synthetic-second.mp3',filesize=3000000,downloaded_bytes=750000),
          dict(id=3,status='Bekliyor',filename='synthetic-waiting.bin',filesize=999,downloaded_bytes=0)]
    app.video_tasks={1:SimpleNamespace(status='İndiriliyor',current_speed=50000)}

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def refresh(hud):
        hud.after_cancel(hud._timer);hud._timer=None;hud.tick();settle()

    try:
        with patch.object(app.db,'get_all_downloads',return_value=rows),patch.object(app.engine,'get_total_speed',return_value=50000) as speed:
            for key,scale in HUD_TEXT_SIZES.items():
                app.settings['hud_text_size']=key;app.show_mini_hud();settle();hud=app._mini_hud
                assert hud.orbit and not hud.pano and len(hud.tiles)==1 and not hasattr(hud,'file_rows')
                assert hud.winfo_width()==340 and hud.attributes('-topmost') and hud.tiles[0].brackets
                assert hud.total_bar.cells==30 and hud.total_bar.value==.25
                assert hud.speed.text=='97,66 KB/sn' and hud.percent.text=='25%' and hud.eta.text=='~30 sn' and hud.count.text=='● 2 AKTİF'
                assert hud.speed.size==round(22*scale)
                panel=hud.tiles[0];right=panel.winfo_rootx()+panel.winfo_width()
                for item in (hud.speed,hud.percent,hud.eta,hud.count):
                    assert item.winfo_width()>=item.winfo_reqwidth() and item.winfo_rootx()+item.winfo_width()<=right,('F15 label overflow',key,item.text)
                assert hud.winfo_height()>=hud.winfo_reqheight(),('F15 clipped',key,hud.winfo_height(),hud.winfo_reqheight(),hud.tiles[0].winfo_height(),hud.tiles[0].winfo_reqheight(),hud.tiles[0].content.winfo_reqheight())
                hud.geometry('+40+40');settle();capture_client(hud).save(Path(f'build/yorunge-hud-{key}.png'))
                speed.return_value=900*1024**2;refresh(hud)
                assert hud.speed.winfo_rootx()+hud.speed.winfo_width()<=hud.spark.winfo_rootx() or hud.speed.winfo_rooty()+hud.speed.winfo_height()<=hud.spark.winfo_rooty(),'F15 speed overlaps chart'
                speed.return_value=50000;rows[1]['filesize']=0;refresh(hud)
                assert hud.percent.text=='—' and hud.total_bar.value is None and hud.eta.text=='Bilinmiyor'
                rows[1]['filesize']=3000000;hud.close();settle()
        print('F15: one bracketed panel, 30 tiles, no file list, three text sizes, unknown size, large speed: OK')
    finally:
        app.destroy()


if __name__=='__main__':main()
