"""P14 five tools, adaptive output cards and real conversion in a fake profile."""


def main():
    import hashlib,json,subprocess,time
    from pathlib import Path
    from unittest.mock import patch
    from PIL import ImageColor
    from gui import MainWindow
    from feature_ui import ToolsDialog
    from feature_windows import TOOLS
    from file_tools import tool_path,media_duration,NO_WINDOW
    from tools.window_capture import capture_client
    from tools.report_pano_tools import SOURCES,STATES
    from utils import ensure_config_dir
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.apply_settings(dict(app.settings,design='pano',color_mode='light',download_dir=str(folder)))
    data={}

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def wait(predicate):
        deadline=time.monotonic()+10
        while not predicate():
            assert not errors,errors
            assert time.monotonic()<deadline,'P14 UI timeout'
            app.update();time.sleep(.01)
        settle()

    def snapshot(window,state):
        window.geometry('+30+30');settle();capture_client(window).save(Path(f'build/pano-tools-{state}.png'))

    try:
        window=ToolsDialog(app);settle();buttons=list(window.mode_buttons.values())
        assert len(buttons)==5 and len({button.winfo_rooty() for button in buttons})==1
        widths=[button.winfo_width() for button in buttons];data['tool_width_delta']=max(widths)-min(widths)
        assert data['tool_width_delta']<=1
        image=capture_client(window).convert('RGB');selected=buttons[0]
        x=selected.winfo_rootx()-window.winfo_rootx()+selected.winfo_width()-10;y=selected.winfo_rooty()-window.winfo_rooty()+selected.winfo_height()//2
        assert image.getpixel((x,y))==ImageColor.getrgb(app.palette['accent']),'Selected P14 tool is not filled accent'
        snapshot(window,'empty')
        source=folder/'synthetic-p14-source.wav';target=folder/'synthetic-p14-output.mp3'
        subprocess.run([tool_path('ffmpeg'),'-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',str(source)],check=True,creationflags=NO_WINDOW)
        window.input.set(str(source));window.format.set('mp3');window.bitrate.set('256')
        wait(lambda:window.timeline is not None)
        assert window.source_card.winfo_ismapped() and not window.source_box.winfo_ismapped()
        assert window.quality_box.winfo_ismapped() and window.quality_box.master.winfo_rootx()>window.format_host.winfo_rootx()
        snapshot(window,'media')
        for mode,_,_,_ in TOOLS:
            window.mode.set(mode);settle();assert window.mode.get()==mode
            assert window.cut_fields.winfo_ismapped()==(mode=='Video / ses kesme')
            assert window.format_host.winfo_ismapped()==(mode in ('Biçim dönüştürme','Video / ses kesme'))
            if mode=='Altyazı indirme':
                window.choose_subtitles('https://example.invalid/p14',str(folder),'srt',[('tr',False),('en',True)])
                assert len(window.subtitle_host.winfo_children())==2
        window.mode.set('Bağlantı kontrolü');settle();snapshot(window,'links')
        window.geometry('560x800+30+30');settle();snapshot(window,'compact')
        assert len({button.winfo_rooty() for button in buttons})==3
        for button in buttons:
            assert button.winfo_rootx()+button.winfo_width()<=window.winfo_rootx()+window.winfo_width()
        window.mode.set('Biçim dönüştürme');window.format.set('mp3');window.geometry('900x1000+30+30');settle()
        with patch('feature_ui.filedialog.asksaveasfilename',return_value=str(target)),patch('feature_ui.reveal_file') as reveal:
            window.run();wait(lambda:not window.busy)
            reveal.assert_called_once_with(target.resolve())
        assert source.is_file() and target.is_file() and .8<media_duration(target)<1.3
        assert window.job_percent.text=='100%'
        probe=subprocess.run([tool_path('ffprobe'),'-v','error','-select_streams','a:0','-show_entries','stream=bit_rate','-of','csv=p=0',str(target)],capture_output=True,text=True,creationflags=NO_WINDOW)
        assert probe.stdout.strip()=='256000',probe.stdout
        snapshot(window,'completed');window.close();settle()
        data['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}
        data['previews']={state:hashlib.sha256(Path(f'build/pano-tools-{state}.png').read_bytes()).hexdigest() for state in STATES}
        Path('build/pano-tools-layout.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        print('P14: five equal accent tools, wide/compact cards, media/cut/links/folders/subtitles, real 256 kbps MP3 and reveal: OK')
    finally:app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
