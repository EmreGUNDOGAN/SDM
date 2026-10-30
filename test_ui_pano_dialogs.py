"""P03/P04 layout and retained capture decisions, synthetic profile and metadata."""


def main():
    import hashlib,json,time
    from pathlib import Path
    from unittest.mock import patch
    from PIL import Image,ImageColor
    from gui import MainWindow
    from batch_dialog import BatchDialog
    from capture_dialog import CapturePrompt
    from tools.window_capture import capture_client
    from tools.report_pano_dialogs import SOURCES,STATES
    from utils import ensure_config_dir
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.apply_settings(dict(app.settings,design='pano',color_mode='light',download_dir=str(folder)))
    video=dict(kind='video',title='Synthetic P04 video',duration=120,audio_filesize=30000,
        qualities=[dict(height=1080,filesize=90000),dict(height=720,filesize=60000)],audio=True)
    data={}

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def wait(predicate):
        deadline=time.monotonic()+5
        while not predicate():
            assert not errors,errors
            assert time.monotonic()<deadline,('Pano dialog UI timeout',[(type(w).__name__,getattr(w,'items',None)) for w in app.winfo_children() if isinstance(w,BatchDialog)])
            app.update();time.sleep(.01)
        settle()

    def snapshot(window,state):
        window.geometry('+30+30');settle();capture_client(window).save(Path(f'build/pano-dialog-{state}.png'))

    def inspect(url,force=False):
        if url.endswith('/video'):return dict(video)
        return dict(kind='file',filename='synthetic-p03.bin',filesize=2048,supports_ranges=True)

    try:
        with patch('dialog_inspection.inspect_url',side_effect=inspect):
            batch=BatchDialog(app);settle();assert batch.buttons['start'].disabled
            snapshot(batch,'batch-empty')
            batch.links.set('https://example.invalid/file\nhttps://example.invalid/video')
            wait(lambda:len(batch.items)==2 and not batch.inspecting)
            assert batch.buttons['start'].kind=='start'
            assert batch.folder_card.winfo_y()==batch.queue_card.winfo_y()
            data['save_width_delta']=abs(batch.folder_card.winfo_width()-batch.queue_card.winfo_width())
            assert data['save_width_delta']<=1
            assert all(item['card'].content.cget('bg')==app.palette['well'] for item in batch.items.values())
            snapshot(batch,'batch')
            batch.urls.focus_force();settle();assert batch.links_card.focused
            # Focus surrounds the whole link card; the original thin border cannot pass.
            snapshot(batch,'batch-focus')
            box=capture_client(batch);x=batch.links_card.winfo_rootx()-batch.winfo_rootx()+batch.links_card.winfo_width()//2
            y=batch.links_card.winfo_rooty()-batch.winfo_rooty()
            accent=ImageColor.getrgb(app.palette['accent'])
            fill=ImageColor.getrgb(app.palette['card'])
            # Antialiasing blends the stroke at the pixel edges; both central
            # rows must still contain at least 90% of the accent colour.
            data['focus_coverage']=[min((background-pixel)/(background-foreground) for pixel,background,foreground in
                zip(box.getpixel((x,y+offset))[:3],fill,accent)) for offset in (1,2)]
            assert all(.9<=coverage<=1 for coverage in data['focus_coverage']),('P03 focus border thinner than 2 px',data['focus_coverage'])
            batch.buttons['queue'].focus_force();settle();assert not batch.links_card.focused
            item=batch.items['https://example.invalid/video'];item['mode'].set('audio');batch.item_changed(item)
            batch.bitrate.set('320');batch.album.set(True);batch.show_section(item)
            item['section'].start.set('00:00:10');item['section'].end.set('00:03:00');settle();assert batch.buttons['queue'].disabled
            item['section'].end.set('00:00:20');settle();assert not batch.buttons['queue'].disabled
            batch.geometry('560x800+30+30');settle();snapshot(batch,'batch-compact')
            for button in batch.buttons.values():
                assert button.winfo_ismapped() and button.winfo_rootx()+button.winfo_width()<=batch.winfo_rootx()+batch.winfo_width()
            batch.submit(False);settle()
            record=next(row for row in app.db.get_all_downloads() if row['url'].endswith('/video'))
            options=json.loads(record['options_json'])
            assert options['audio']==dict(bitrate=320,album=True) and options['section']['start']==10 and record['status']=='Kuyrukta'
            decisions=[]
            request=dict(kind='video',url='https://example.invalid/video',filename='Synthetic P04 capture',height=720,filesize=60000,ticket='p04')
            prompt=CapturePrompt(app,request,lambda token,result:decisions.append((token,result)))
            wait(lambda:len(prompt.formats)==2)
            assert prompt.quality.get()=='720' and prompt.buttons['start'].kind=='start'
            assert not prompt.audio_row.winfo_ismapped();snapshot(prompt,'capture-video')
            cards=prompt.quality_cards;data['quality_y_delta']=max(card.winfo_rooty() for card in cards)-min(card.winfo_rooty() for card in cards)
            assert data['quality_y_delta']==0
            prompt.quality.set('audio');settle();assert prompt.audio_row.winfo_ismapped()
            prompt.bitrate.set('128');prompt.album.set(True);snapshot(prompt,'capture-audio')
            prompt.choose('queue');settle();assert decisions==[('p04','queue')]
            record=next(row for row in app.db.get_all_downloads() if row['filename']=='Synthetic P04 capture.mp3')
            assert json.loads(record['options_json'])['audio']==dict(bitrate=128,album=True)
            plain=CapturePrompt(app,dict(kind='file',url='https://example.invalid/file',filename='synthetic-plain.zip',ticket='file'),lambda token,result:decisions.append((token,result)))
            settle();assert plain.quality_host is None and plain.section_fields is None
            snapshot(plain,'capture-file');plain.close();settle();assert decisions[-1]==('file','cancel')
        data['sources']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}
        data['previews']={state:hashlib.sha256(Path(f'build/pano-dialog-{state}.png').read_bytes()).hexdigest() for state in STATES}
        Path('build/pano-dialog-layout.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        print('P03/P04: focused card, equal save cards, media/file layouts, selected qualities, sections, MP3 options and queue/cancel: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
