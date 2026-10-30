"""F14/F16/F17 Yörünge tools, speed graph and update windows on synthetic data."""


def main():
    import time
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import patch
    from gui import MainWindow
    from feature_ui import ToolsDialog
    from feature_windows import SpeedGraph
    from update_dialog import UpdateDialog
    from tools.window_capture import capture_client
    from utils import ensure_config_dir
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.apply_settings(dict(app.settings,design='yorunge',color_mode='dark',download_dir=str(folder)))
    did=app.db.add_download('https://example.invalid/f16','synthetic-f16.bin',str(folder/'synthetic-f16.bin'),status='Kuyrukta')
    points=((0,1048576),(100,2097152),(180,3145728),(260,2097152),(380,1048576))
    app.speed_history[did]=SimpleNamespace(points=points,average=2097152,active_seconds=380)

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def snapshot(window,state):
        window.geometry('+30+30');settle();capture_client(window).save(Path(f'build/yorunge-utility-{state}.png'))

    try:
        window=ToolsDialog(app);settle();buttons=list(window.mode_buttons.values())
        assert [button.number for button in buttons]==[1,2,3,4,5] and len({button.winfo_rooty() for button in buttons})==1
        widths=[button.winfo_width() for button in buttons];assert max(widths)-min(widths)<=1
        assert window.kicker_label.text=='// MODÜLLER' and not window.description_label.winfo_ismapped()
        assert window.output_step.title.text=='// ÇIKTI BİÇİMİ' and window.progress.cells==40
        window.mode.set('Bağlantı kontrolü');settle();assert window.output_step.title.text=='// ÇIKTI'
        window.mode.set('Biçim dönüştürme');settle();snapshot(window,'tools');window.close();settle()
        graph=SpeedGraph(app,did);settle();assert graph.title_label.text=='synthetic-f16.bin'
        assert [card.stripe for card in graph.stat_cards]==[app.palette[key] for key in ('accent','violet','success','warning')]
        assert graph.chart_card.brackets and not any(card.brackets for card in graph.stat_cards)
        snapshot(graph,'graph');image=capture_client(graph).convert('RGB')
        left=graph.chart.winfo_rootx()-graph.winfo_rootx();top=graph.chart.winfo_rooty()-graph.winfo_rooty()
        area=image.crop((left,top,left+graph.chart.winfo_width(),top+graph.chart.winfo_height()))
        # The 1 px dashed line antialiases; count violet-hued pixels, which the cyan chart never has.
        assert sum(r>g+15 and b>g+30 for r,g,b in area.getdata())>100,'F16 average line is not violet'
        graph.close();settle()
        update=dict(version='v1.0.1',notes='- Synthetic verified change\n- Synthetic second note',notes_url='https://example.invalid/release')
        with patch.object(app.engine,'get_active_count',return_value=2):
            window=UpdateDialog(app,update);settle();assert len(window.step_cards)==3 and not window.header.winfo_ismapped()
            assert window.hero.brackets and window.hero.content.cget('bg')==app.palette['accent_soft']
            snapshot(window,'update');window.accept();settle();assert window.result
        print('F14/F16/F17: numbered tool modules, mono captions, stripe metrics, violet average, version panel and install order: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
