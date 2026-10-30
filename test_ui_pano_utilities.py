"""P16/P17: measured speed history and update decisions; disposable profile only."""


def main():
    import hashlib,json,time
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import patch
    from PIL import ImageColor
    from gui import MainWindow
    from feature_windows import SpeedGraph
    from update_dialog import UpdateDialog
    from app_version import VERSION
    from theme_widgets import Button
    from ui_surface import TextLabel
    from tools.window_capture import capture_client
    from tools.report_dialog_previews import UTILITY_SOURCES,UTILITY_STATES
    from utils import ensure_config_dir
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.apply_settings(dict(app.settings,design='pano',color_mode='light',download_dir=str(folder)))
    did=app.db.add_download('https://example.invalid/p16','synthetic-p16.bin',str(folder/'synthetic-p16.bin'),status='Kuyrukta')
    points=((0,1048576),(100,2097152),(180,3145728),(260,2097152),(380,1048576))
    app.speed_history[did]=SimpleNamespace(points=points,average=2097152,active_seconds=380)
    data={}

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def snapshot(window,state):
        window.geometry('+30+30');settle();capture_client(window).save(Path(f'build/pano-utility-{state}.png'))

    try:
        graph=SpeedGraph(app,did);settle();assert len(graph.stat_cards)==4
        assert graph.chart.points==points[1:] and graph.chart.average==2097152
        assert graph.stats['now'].get()=='1,00 MB/sn' and graph.stats['peak'].get()=='3,00 MB/sn'
        widths=[card.winfo_width() for card in graph.stat_cards];data['stat_width_delta']=max(widths)-min(widths)
        ys=[card.winfo_rooty() for card in graph.stat_cards];data['stat_y_delta']=max(ys)-min(ys)
        assert data['stat_width_delta']<=1 and data['stat_y_delta']==0
        snapshot(graph,'graph')
        image=capture_client(graph).convert('RGB');orange=ImageColor.getrgb(app.palette['start'])
        left=graph.chart.winfo_rootx()-graph.winfo_rootx();top=graph.chart.winfo_rooty()-graph.winfo_rooty()
        area=image.crop((left,top,left+graph.chart.winfo_width(),top+graph.chart.winfo_height()))
        assert sum(sum(abs(a-b) for a,b in zip(pixel,orange))<35 for pixel in area.getdata())>30,'P16 average line is not orange'
        graph.span.set('60');graph.tick();settle();assert graph.chart.points==points[-1:]
        graph.span.set('all');graph.tick();settle();assert graph.chart.points==points
        graph.geometry('560x650+30+30');settle()
        assert len({card.winfo_rooty() for card in graph.stat_cards})==2
        snapshot(graph,'graph-compact');graph.close();settle();assert not graph._owned_timers
        update=dict(version='v1.0.1',notes='- Synthetic verified change\n- Synthetic second note',notes_url='https://example.invalid/release')
        with patch.object(app.engine,'get_active_count',return_value=2):
            window=UpdateDialog(app,update);settle();assert len(window.step_cards)==3
            widths=[card.winfo_width() for card in window.step_cards];data['step_width_delta']=max(widths)-min(widths)
            assert data['step_width_delta']<=1
            assert window.hero.content.cget('bg')==app.palette['accent']
            assert any(isinstance(child,TextLabel) and VERSION in child.text and '1.0.1' in child.text
                for box in window.hero.content.winfo_children() for child in box.winfo_children())
            snapshot(window,'update-active')
            def buttons(parent):
                for child in parent.winfo_children():
                    if isinstance(child,Button):yield child
                    yield from buttons(child)
            controls={button.text:button for button in buttons(window)}
            assert controls['Şimdi güncelle'].kind=='start'
            with patch('update_dialog.webbrowser.open') as open_notes:
                controls['Tüm sürüm notları'].invoke();open_notes.assert_called_once_with(update['notes_url'])
            controls['Daha sonra'].invoke();settle();assert not window.result
        with patch.object(app.engine,'get_active_count',return_value=0):
            window=UpdateDialog(app,dict(version='v1.0.1'));settle();snapshot(window,'update-empty')
            window.accept();settle();assert window.result and not window.winfo_exists()
        data['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in UTILITY_SOURCES}
        data['previews']={state:hashlib.sha256(Path(f'build/pano-utility-{state}.png').read_bytes()).hexdigest() for state in UTILITY_STATES}
        Path('build/pano-utility-layout.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        print('P16/P17: real history/span/mean, four equal cards, compact rows, three update steps, notes and accept/cancel: OK')
    finally:app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
