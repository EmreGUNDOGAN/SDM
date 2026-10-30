"""F03/F04 Yörünge layout and retained capture decisions, synthetic profile and metadata."""


def main():
    import time
    from pathlib import Path
    from unittest.mock import patch
    from gui import MainWindow
    from batch_dialog import BatchDialog
    from capture_dialog import CapturePrompt
    from tools.window_capture import capture_client
    from utils import ensure_config_dir
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.apply_settings(dict(app.settings,design='yorunge',color_mode='dark',download_dir=str(folder)))
    video=dict(kind='video',title='Synthetic F04 video',duration=120,audio_filesize=30000,
        qualities=[dict(height=1080,filesize=90000),dict(height=720,filesize=60000)],audio=True)

    def settle():
        for _ in range(5):app.update();time.sleep(.02)
        assert not errors,errors

    def wait(predicate):
        deadline=time.monotonic()+5
        while not predicate():
            assert not errors,errors
            assert time.monotonic()<deadline,'Yörünge dialog UI timeout'
            app.update();time.sleep(.01)
        settle()

    def snapshot(window,state):
        window.geometry('+30+30');settle();capture_client(window).save(Path(f'build/yorunge-dialog-{state}.png'))

    def inspect(url,force=False):
        if url.endswith('/video'):return dict(video)
        return dict(kind='file',filename='synthetic-f03.bin',filesize=2048,supports_ranges=True)

    try:
        with patch('dialog_inspection.inspect_url',side_effect=inspect):
            batch=BatchDialog(app);settle();snapshot(batch,'batch-empty')
            assert batch.kicker_label.text=='// YENİ AKTARIM' and not batch.description_label.winfo_ismapped()
            batch.links.set('https://example.invalid/file\nhttps://example.invalid/video')
            wait(lambda:len(batch.items)==2 and not batch.inspecting)
            snapshot(batch,'batch')
            assert batch.status.get()=='// ALGILANAN HEDEFLER · 02' and batch.total.get().startswith('2 SEÇİLİ · ~')
            assert batch.found_card.brackets and not any(item['card'].brackets for item in batch.items.values())
            assert all(item['card'].stripe==app.palette['accent'] for item in batch.items.values())
            # Unselected targets lose the stripe; F03's square corners stay square.
            item=batch.items['https://example.invalid/file'];item['selected'].set(False);settle()
            assert item['card'].stripe is None and batch.total.get().startswith('1 SEÇİLİ')
            assert {card.radius for card in (batch.links_card,batch.folder_card,batch.queue_card,item['card'])}=={0}
            item['selected'].set(True);settle()
            batch.geometry('560x800+30+30');settle();snapshot(batch,'batch-compact');batch.close();settle()
            request=dict(kind='video',url='https://example.invalid/video',filename='Synthetic F04 capture',height=720,filesize=60000,ticket='f04')
            prompt=CapturePrompt(app,request,lambda token,result:None)
            wait(lambda:len(prompt.formats)==2);snapshot(prompt,'capture-video')
            assert not prompt.header.winfo_ismapped() and prompt.summary_card.brackets and not prompt.quality_card.brackets
            prompt.quality.set('audio');settle();snapshot(prompt,'capture-audio');prompt.close();settle()
        print('F03/F04: kicker header, target panel, selection stripes, square panels, captured-video panel: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
