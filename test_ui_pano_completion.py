"""P06 layout and preserved completion behavior in disposable profiles only."""
def main():
    import hashlib,json,time
    from pathlib import Path
    from unittest.mock import patch
    from gui import MainWindow
    from completion_dialog import CompletionDialog
    from theme_catalog import THEMES
    from theme_widgets import Button
    from ui_controls import CheckBox
    from ui_surface import TextLabel
    from feature_ui import SpeedHistory
    from tools.window_capture import capture_client
    from tools.report_dialog_previews import P06_SOURCES
    from utils import ensure_config_dir

    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    name='p06-completion-fixture-with-a-long-filename-for-two-measured-lines.mp4'
    path=folder/name;path.write_bytes(b'P06 synthetic fixture\n'*80)
    did=app.db.add_download('https://example.invalid/p06',name,str(path),filesize=path.stat().st_size,category='Video',status='Tamamlandı')
    record=app.db.get_download(did)
    history=app.speed_history[did]=SpeedHistory()
    history.active_seconds=365;history.bytes=path.stat().st_size
    measurements={}

    def settle():
        for _ in range(6):app.update();time.sleep(.02)
        assert not errors,errors

    def descendants(parent):
        for child in parent.winfo_children():
            yield child;yield from descendants(child)

    try:
        for theme in THEMES:
            design,mode=theme.split('_')
            app.apply_settings(dict(app.settings,design=design,color_mode=mode,completion_popup=True,
                notifications_enabled=False,download_dir=str(folder)))
            with patch('antivirus.scan_file',return_value=('Taranan nesnelerde tehdit bulunmadı. Ek tarama ayrıntısı.',folder/'synthetic-scan.log')) as scanner:
                window=CompletionDialog(app,record);window.geometry('560x500+40+40');settle()
                scanner.assert_not_called()
                if design=='pano':
                    assert len(window.stat_cards)==3 and len(window.name_lines)==2
                    assert window.name_lines[0].text.endswith('-')
                    assert ''.join(line.text for line in window.name_lines)==name
                    widths=[card.winfo_width() for card in window.stat_cards]
                    assert max(widths)-min(widths)<=1,widths
                    assert len({card.winfo_y() for card in window.stat_cards})==1
                    for item in [*window.name_lines,window.scan_title,window.scan_detail]:
                        assert item.winfo_height()>=item.winfo_reqheight(),('clipped P06 text',item)
                    values=[list(child for child in descendants(card) if isinstance(child,TextLabel))[-1] for card in window.stat_cards]
                    assert '6 dk 05 sn' in [child.text for child in values]
                    value_y=[child.winfo_rooty() for child in values]
                    assert len(set(value_y))==1,value_y
                    assert window.scan_title.master.cget('bg')==app.palette['card']
                    assert window.file_card.winfo_rootx()==window.scan_title.master.master.master.winfo_rootx(), 'File/scan card left edges differ'
                    capture_client(window).save(Path('build/p06-pano.png'))
                    measurements['stat_width_spread']=max(widths)-min(widths)
                    measurements['stat_value_y_spread']=max(value_y)-min(value_y)
                    measurements['card_edge_delta']=abs(window.file_card.winfo_rootx()-window.scan_title.master.master.master.winfo_rootx())
                else:assert not window.stat_cards
                window.scan_button.invoke();assert window.scan_button.disabled
                deadline=time.monotonic()+3
                while window.scan_button.disabled:
                    assert time.monotonic()<deadline,'Explicit scan callback timed out'
                    app.update();time.sleep(.01)
                settle();scanner.assert_called_once_with(record['filepath'])
                assert window.scan_status.get()=='Taranan nesnelerde tehdit bulunmadı.'
                assert window.scan_detail.text=='Ek tarama ayrıntısı.'
                edge=window.scan_button.winfo_rootx()
                for line in (window.scan_title,window.scan_detail):assert line.winfo_rootx()+line.winfo_width()<=edge
                if design=='pano':capture_client(window).save(Path('build/p06-pano-scanned.png'))
                checkbox=next(child for child in descendants(window.actionbar) if isinstance(child,CheckBox))
                checkbox.invoke();settle()
                assert app.settings['completion_popup'] is False
                assert json.loads((ensure_config_dir()/'config.json').read_text(encoding='utf-8'))['completion_popup'] is False
                buttons=[child for child in descendants(window.body) if isinstance(child,Button)]
                play=next(child for child in buttons if child.text=='Oynat')
                with patch('completion_dialog.os.startfile') as launch:
                    play.invoke();settle();launch.assert_called_once_with(record['filepath'])
                    launch.reset_mock()
                    next(child for child in buttons if child.text=='Klasörde göster').invoke();settle()
                    launch.assert_called_once_with(str(path.parent))
                assert window.winfo_exists(),'Opening a file changed the existing dialog lifetime'
                close=next(child for child in descendants(window.actionbar) if isinstance(child,Button) and child.text=='Kapat')
                close.invoke();settle()
                assert not window.winfo_exists()
                if design=='pano':
                    alternate=CompletionDialog(app,dict(record,filename=name.replace('-','_')));settle()
                    assert alternate.name_lines[0].text.endswith('_')
                    assert ''.join(line.text for line in alternate.name_lines)==name.replace('-','_')
                    alternate.close();settle()
        assert not errors,errors
        measurements['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in P06_SOURCES}
        measurements['previews']={state:hashlib.sha256(Path(f'build/p06-{state}.png').read_bytes()).hexdigest() for state in ('pano','pano-scanned')}
        Path('build/p06-layout.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
        print('P06: three equal cards, two measured filename lines, explicit scan, preserved opt-out/save/open, six appearances: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
