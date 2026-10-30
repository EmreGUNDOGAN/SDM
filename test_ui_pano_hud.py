"""P15 live HUD in a disposable profile; no real downloads or installed app."""


def main():
    import hashlib,json,time
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import patch,Mock
    import ttkbootstrap as tb
    from feature_windows import MiniHUD
    from theme_catalog import palette
    from ui_surface import TextLabel
    from theme_widgets import Button
    from ui_tokens import HUD_TEXT_SIZES
    from tools.window_capture import capture_client
    from tools.report_pano_previews import HUD_SOURCES
    from utils import ensure_config_dir,load_settings
    app=tb.Window();app.withdraw();errors=[]
    app.palette=palette('pano_light');app.settings=load_settings();app._mini_hud=None
    app.db=SimpleNamespace(get_all_downloads=Mock());app.engine=SimpleNamespace(get_total_speed=Mock())
    app.pause_download=Mock()
    def show_hud():app._mini_hud=MiniHUD(app)
    app.show_mini_hud=show_hud
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.settings.update(design='pano',color_mode='light',download_dir=str(folder))
    rows=[dict(id=1,status='İndiriliyor',filename='synthetic-first.bin',filesize=1000000,downloaded_bytes=250000),
          dict(id=2,status='Dönüştürülüyor',filename='synthetic-second.mp3',filesize=3000000,downloaded_bytes=750000),
          dict(id=3,status='Bekliyor',filename='synthetic-waiting.bin',filesize=999,downloaded_bytes=0)]
    app.video_tasks={1:SimpleNamespace(status='İndiriliyor',current_speed=50000)}
    measurements={}

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def labels(parent):
        for child in parent.winfo_children():
            if isinstance(child,TextLabel):yield child
            yield from labels(child)

    def refresh(hud):
        hud.after_cancel(hud._timer);hud._timer=None;hud.tick();settle()

    def check_speed(hud):
        assert hud.speed.winfo_width()>=hud.speed.winfo_reqwidth(),'Clipped HUD speed'
        assert hud.speed.winfo_rootx()+hud.speed.winfo_width()<=hud.speed_host.winfo_rootx()+hud.speed_host.winfo_width()
        assert hud.speed.winfo_rootx()+hud.speed.winfo_width()<=hud.spark.winfo_rootx() or hud.speed.winfo_rooty()+hud.speed.winfo_height()<=hud.spark.winfo_rooty(),'HUD speed overlaps chart'

    def check_region(hud):
        import ctypes
        from ctypes import wintypes
        user=ctypes.WinDLL('user32');gdi=ctypes.WinDLL('gdi32')
        gdi.CreateRectRgn.argtypes=[ctypes.c_int]*4;gdi.CreateRectRgn.restype=wintypes.HANDLE
        gdi.PtInRegion.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_int];gdi.PtInRegion.restype=wintypes.BOOL
        gdi.DeleteObject.argtypes=[wintypes.HANDLE]
        user.GetWindowRgn.argtypes=[wintypes.HWND,wintypes.HANDLE];user.GetWindowRgn.restype=ctypes.c_int
        region=gdi.CreateRectRgn(0,0,0,0);assert region
        try:
            assert user.GetWindowRgn(int(hud.tk.call('wm','frame',hud._w),0),region)==3
            assert not gdi.PtInRegion(region,0,0) and gdi.PtInRegion(region,22,0)
            assert gdi.PtInRegion(region,170,hud.winfo_height()-1),'HUD region stale after resize'
        finally:gdi.DeleteObject(region)

    try:
        with patch.object(app.db,'get_all_downloads',return_value=rows),patch.object(app.engine,'get_total_speed',return_value=50000) as speed:
            heights=[]
            for key,scale in HUD_TEXT_SIZES.items():
                app.settings['hud_text_size']=key;app.show_mini_hud();settle();hud=app._mini_hud
                assert hud.pano and len(hud.tiles)==3 and not hasattr(hud,'file_rows')
                assert hud.winfo_width()==340 and hud.attributes('-topmost')
                check_region(hud)
                assert hud.speed.size==round(22*scale) and hud.eta.size==round(17*scale)
                assert hud.speed.text=='97,66 KB/sn' and hud.percent.text=='25%' and hud.count.text=='2 etkin'
                assert hud.total_bar.value==.25 and hud.eta.text=='~30 sn'
                assert all(card.content.cget('bg')==app.palette['card'] for card in hud.tiles)
                assert abs(hud.tiles[1].winfo_width()-hud.tiles[2].winfo_width())<=1
                for card in hud.tiles:
                    right=card.winfo_rootx()+card.winfo_width()
                    for text in labels(card):
                        assert text.winfo_width()>=text.winfo_reqwidth(),('clipped HUD label',key,text.text)
                        assert text.winfo_rootx()+text.winfo_width()<=right,('HUD label overflow',key,text.text)
                check_speed(hud);heights.append(hud.winfo_height())
                measurements[key]=dict(height=hud.winfo_height(),card_width_delta=abs(hud.tiles[1].winfo_width()-hud.tiles[2].winfo_width()),
                    value_y_delta=abs(hud.percent.winfo_rooty()-hud.eta.winfo_rooty()))
                assert measurements[key]['value_y_delta']==0
                hud.geometry('+40+40');settle();capture_client(hud).save(Path(f'build/pano-hud-{key}.png'))
                speed.return_value=900*1024**2;refresh(hud);check_speed(hud)
                speed.return_value=50000;rows[1]['filesize']=0;refresh(hud)
                assert hud.percent.text=='—' and hud.total_bar.value is None and hud.eta.text=='Bilinmiyor'
                rows[1]['filesize']=3000000
                foot=hud.winfo_children()[-1];buttons={child.text:child for child in foot.winfo_children() if isinstance(child,Button)}
                for button in buttons.values():
                    assert button.winfo_ismapped() and button.winfo_rooty()+button.winfo_height()<=hud.winfo_rooty()+hud.winfo_height(),'HUD footer clipped'
                with patch.object(app,'pause_download') as pause:
                    buttons['Tümünü duraklat'].invoke();assert [call.args[0] for call in pause.call_args_list]==[1,2,3]
                hud.drag_start(SimpleNamespace(widget=buttons['Tümünü duraklat'],x_root=40,y_root=40));assert hud._drag is None
                hud.drag_start(SimpleNamespace(widget=hud.speed,x_root=40,y_root=40))
                hud.drag_move(SimpleNamespace(x_root=70,y_root=65));settle();hud.drag_end(None)
                expected=[hud.winfo_x(),hud.winfo_y()]
                assert app.settings['hud_position']==expected
                assert json.loads((ensure_config_dir()/'config.json').read_text(encoding='utf-8'))['hud_position']==expected
                with patch.object(app,'deiconify') as show,patch.object(app,'lift') as lift:
                    buttons['SDM’yi aç'].invoke();show.assert_called_once();lift.assert_called_once()
                hud.close();settle();assert hud._timer is None and app._mini_hud is None
                app.show_mini_hud();settle();hud=app._mini_hud;assert [hud.winfo_x(),hud.winfo_y()]==expected
                hud.close();settle()
            assert heights==sorted(heights) and heights[0]<heights[-1],heights
            rows.clear();app.video_tasks.clear();speed.return_value=0
            app.settings['hud_text_size']='normal';app.show_mini_hud();settle();hud=app._mini_hud
            assert hud.percent.text=='—' and hud.count.text=='0 etkin' and hud.total_bar.value==0 and hud.eta.text=='—'
            hud.geometry('+40+40');settle();capture_client(hud).save(Path('build/pano-hud-empty.png'));hud.close();settle()
        measurements['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in HUD_SOURCES}
        measurements['previews']={state:hashlib.sha256(Path(f'build/pano-hud-{state}.png').read_bytes()).hexdigest() for state in (*HUD_TEXT_SIZES,'empty')}
        Path('build/pano-hud-layout.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
        print('P15: three cards/no file list, three text sizes, weighted progress, unknown/empty, pause/show/drag/save/reopen/close: OK')
    finally:
        if app._mini_hud:app._mini_hud.close()
        app.video_tasks.clear();app.destroy()


if __name__=='__main__':main()
