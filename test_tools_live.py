"""Explicit integration check: real FFmpeg, Tk views, scan and HTTP link check."""
def main():
    import os
    if not os.environ.get('SDM_DATA_DIR'):raise RuntimeError('Isolated SDM_DATA_DIR is required')
    from pathlib import Path
    import subprocess
    import tempfile
    import threading
    from file_tools import tool_path,process_media,media_duration,NO_WINDOW
    from utils import ensure_config_dir
    from antivirus import scan_file
    from gui import MainWindow
    from feature_ui import ToolsDialog,SpeedGraph
    from modern_settings import SettingsDialog
    with tempfile.TemporaryDirectory(dir=ensure_config_dir()) as temporary:
        root=Path(temporary);source=root/'source.wav'
        subprocess.run([tool_path('ffmpeg'),'-v','error','-f','lavfi','-i','sine=frequency=1000:duration=3',str(source)],check=True,creationflags=NO_WINDOW)
        cut=root/'cut.mp3';events=[];process_media(source,cut,'cut','00:01','00:02',progress=events.append)
        assert .9<=media_duration(cut)<=1.2 and source.exists() and events[-1]==100
        event=threading.Event();event.set()
        try:process_media(source,root/'cancel.wav','convert',cancel=event)
        except ValueError:pass
        else:raise AssertionError('Cancellation was ignored')
        assert not (root/'cancel.wav').exists()
        print('Real FFmpeg cut / MP3 / cancellation and source preservation: OK')
        text=root/'harmless.txt';text.write_text('SDM harmless integration fixture')
        result,report=scan_file(text);assert 'tehdit bulunmadı' in result and report.is_file()
        print('Installed Kaspersky explicit harmless-file scan and report verification: OK')
    app=MainWindow();app.engine.stop_engine();app.settings['duplicate_warning']=False
    try:
        settings=SettingsDialog(app);app.update();settings.queue_editor.add();settings.queue_editor.name.set('Gece videoları');settings.queue_editor.enabled.set(True)
        values=settings.collect();assert len(values['queues'])==2 and values['queues'][1]['name']=='Gece videoları';settings.destroy()
        app.toggle_relax();assert app.settings['relax_mode'];app.toggle_relax();assert not app.settings['relax_mode']
        app.show_mini_hud();app.update();assert app._mini_hud.winfo_exists();app._mini_hud.close()
        tools=ToolsDialog(app);app.update();assert tools.winfo_exists();tools.close()
        from feature_ui import SpeedHistory
        app.speed_history[999]=SpeedHistory();app.speed_history[999].sample(1,0,0,True);app.speed_history[999].sample(2,100,100,True)
        graph=SpeedGraph(app,999);app.update();assert graph.canvas.find_all();graph.destroy()
        print('Calendar/named queue editor, relax toggle, mini HUD, tools view and real-sample graph: OK')
    finally:app.destroy()

if __name__=='__main__':main()
