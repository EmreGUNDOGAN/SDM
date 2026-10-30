"""A03–A06/A14–A17/A19, synthetic metadata + real local media, never user data."""
def main():
    import json,time,subprocess
    import tkinter as tk
    from pathlib import Path
    from unittest.mock import patch
    from gui import MainWindow
    from app_dialogs import BatchDialog,CapturePrompt,CompletionDialog
    from download_engine import SegmentInfo
    from download_window import DownloadDetailDialog
    from feature_ui import ToolsDialog,SpeedGraph,SpeedHistory
    from ui_overlays import MessageDialog
    from ui_messages import choose,messagebox
    from update_dialog import UpdateDialog
    from tools.window_capture import capture_client
    from utils import ensure_config_dir,save_settings
    from file_tools import tool_path,media_duration,NO_WINDOW
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    folder=ensure_config_dir()/'downloads';folder.mkdir(exist_ok=True)
    app.settings.update(download_dir=str(folder),auto_open_details=False,completion_popup=False,notifications_enabled=False,duplicate_warning=False)
    save_settings(app.settings)
    video=dict(kind='video',title='Synthetic video fixture',duration=120,audio_filesize=30000,
               qualities=[dict(height=1080,filesize=90000,extension='mkv'),dict(height=720,filesize=60000,extension='mkv')],audio=True)
    def inspect(url,force=False):
        if 'video' in url:return dict(video)
        if 'failed' in url:raise ValueError('Synthetic inspection failure')
        return dict(kind='file',filename='synthetic-file.zip',filesize=2048,supports_ranges=True)
    def wait(predicate,timeout=6):
        deadline=time.monotonic()+timeout
        while not predicate():
            assert time.monotonic()<deadline,'UI condition timeout'
            app.update();time.sleep(.01)
        app.update()
    def snapshot(window,name,mode):
        app.update();width=min(window.winfo_width(),window.winfo_screenwidth()-80);height=min(window.winfo_height(),window.winfo_screenheight()-100)
        window.geometry(f'{width}x{height}+20+20');app.update()
        image=capture_client(window);assert len(image.getcolors(32) or [])==0,'Preview lacks rendered content'
        image.save(Path('build')/f'phase3-{name}-{mode}.png')
    try:
        for mode in ('light','dark'):
            app.apply_settings(dict(app.settings,design='atlas',color_mode=mode));app.update()
            with patch('dialog_inspection.inspect_url',side_effect=inspect) as inspector:
                batch=BatchDialog(app,'https://example.invalid/file\nhttps://example.invalid/video\nhttps://example.invalid/failed')
                assert batch.buttons['start'].disabled
                wait(lambda:len(batch.items)==3 and not batch.inspecting)
                assert inspector.call_count==3 and all(url in batch.inspection_attempted for url in batch.items)
                item=batch.items['https://example.invalid/video'];assert item['quality'].get()=='1080'
                batch.show_section(item);section=item['section'];assert section.timeline is not None
                section.start.set('00:00:10');section.end.set('00:00:20');app.update()
                assert section.collect()['start']==10
                section.timeline.choose_handle('end');section.timeline.nudge(-1);app.update();assert section.end.get()=='00:00:19'
                section.end.set('00:00:05');app.update();assert batch.buttons['start'].disabled
                section.end.set('00:00:20');app.update();assert not batch.buttons['start'].disabled
                failed=batch.items['https://example.invalid/failed'];failed['selected'].set(False)
                snapshot(batch,'batch',mode)
                before=len(app.db.get_all_downloads());batch.submit(False);app.update()
                records=app.db.get_all_downloads();assert len(records)==before+2
                added=next(r for r in records if r['url']=='https://example.invalid/video' and json.loads(r['options_json']).get('section'))
                assert added['status']=='Kuyrukta' and json.loads(added['options_json'])['section']['end']==20
                # Extension page scan: links open in the same batch window for selection, nothing starts.
                links=['https://example.invalid/file','https://example.invalid/video']
                scan=app.browser_request(dict(kind='batch',urls=links,ticket='scan-ticket'),lambda *args:None)
                assert isinstance(scan,BatchDialog) and scan.links.get().split()==links
                wait(lambda:len(scan.items)==2 and not scan.inspecting);assert len(app.db.get_all_downloads())==before+2
                scan.close()
                # YouTube Music button: no dialog; album tracks numbered in list order with the chosen bitrate.
                album='https://music.youtube.com/playlist?list=OLAK5uy_synthetic'
                tracks=[f'https://music.youtube.com/watch?v=t{i}' for i in (1,2,3)]
                count=len(app.db.get_all_downloads());last=max([r['id'] for r in app.db.get_all_downloads()],default=0)
                # Real tasks are created but never reach the network in this fixture.
                started=patch('video_downloader.VideoDownloadTask.start');started.start()
                with patch('dialog_inspection.inspect_url',return_value=dict(kind='playlist',entries=[(u,'Track') for u in tracks])):
                    app.browser_request(dict(kind='music',url=album,bitrate=320,list=True,ticket='music-ticket'),lambda *args:None)
                    wait(lambda:len(app.db.get_all_downloads())==count+3)
                music=sorted((r for r in app.db.get_all_downloads() if r['url'] in tracks and r['id']>last),key=lambda r:r['url'])
                assert [json.loads(r['options_json'])['audio'] for r in music]==[dict(bitrate=320,album=True,track=i) for i in (1,2,3)]
                app.browser_request(dict(kind='music',url='https://music.youtube.com/watch?v=single',bitrate=128,list=False,ticket='song'),lambda *args:None)
                single=next(r for r in app.db.get_all_downloads() if r['url'].endswith('v=single') and r['id']>last)
                assert json.loads(single['options_json'])['audio']==dict(bitrate=128,album=True,track=None) and single['download_type']=='video'
                for record in music+[single]:app.cancel_download(record['id'])
                started.stop()
                decision=[]
                request=dict(kind='video',url='https://example.invalid/video',filename='Synthetic capture',height=720,filesize=60000,ticket='fixture-ticket')
                prompt=CapturePrompt(app,request,lambda token,result:decision.append((token,result)))
                wait(lambda:len(prompt.formats)==2)
                assert prompt.quality.get()=='720' and len(prompt.quality_cards)==3
                prompt.quality.set('audio');assert prompt.name.get().endswith('.mp3')
                app.update();assert prompt.audio_row.winfo_ismapped(),'MP3 shows its quality and album options'
                prompt.section_fields.enabled.set(True);prompt.section_fields.start.set('00:00:10');prompt.section_fields.end.set('00:03:00');app.update()
                assert prompt.buttons['queue'].disabled
                prompt.section_fields.end.set('00:00:20');app.update();assert not prompt.buttons['queue'].disabled
                snapshot(prompt,'capture',mode);prompt.buttons['cancel'].invoke();assert decision==[('fixture-ticket','cancel')]
                # The chosen MP3 options are stored with the download (music engine reads them).
                mp3=CapturePrompt(app,dict(request,ticket='mp3-ticket',filename='Synthetic song'),lambda token,result:decision.append((token,result)))
                wait(lambda:len(mp3.formats)==2);mp3.quality.set('audio');mp3.bitrate.set('320');mp3.album.set(True)
                with patch('video_downloader.VideoDownloadTask.start'):mp3.choose('queue')
                song=max((r for r in app.db.get_all_downloads() if r['filename'].startswith('Synthetic song')),key=lambda r:r['id'])
                assert json.loads(song['options_json'])['audio']==dict(bitrate=320,album=True),song['options_json']
                mp3=CapturePrompt(app,dict(request,ticket='video-ticket'),lambda token,result:None);wait(lambda:len(mp3.formats)==2)
                assert not mp3.audio_row.winfo_ismapped();mp3.choose('cancel')
            # Real task snapshot; configured maximum never stands in for observed parts.
            did=app.add_download_from_dialog('https://example.invalid/range','synthetic-range.bin',str(folder/f'range-{mode}.bin'),auto_start=False)
            task=app.engine.get_task(did);task.filesize=1000000;task.supports_ranges=True;task.current_speed=50000;task.eta=15;task.status='İndiriliyor'
            part=SegmentInfo(0,0,999999);part.downloaded_bytes=250000;part.connection_active=True;part.status='İndiriliyor';task.segments=[part]
            app.db.update_download_progress(did,250000,1000000);app.db.update_download_status(did,'İndiriliyor')
            history=app.speed_history[did]=SpeedHistory();history.sample(1,0,10000,True);history.sample(2,50000,50000,True)
            detail=DownloadDetailDialog(app,app.db.get_download(did));app.detail_windows[did]=detail;app.update()
            assert detail.content.snapshot['progress']==.25 and len(detail.content.parts.rows)==1
            assert detail.values['received'].get().startswith('244.14 KB') and detail.values['speed'].get()=='48.83 KB/s'
            assert detail.content.ring.value==.25
            snapshot(detail,'detail',mode);detail.cancel_button.invoke();app.update();assert did not in app.detail_windows
            graph=SpeedGraph(app,did);app.update();assert graph.chart.points and graph.stats['peak'].get()
            snapshot(graph,'graph',mode);graph.close()
            app.show_mini_hud();app.update();hud=app._mini_hud;assert hud.winfo_exists()
            snapshot(hud,'hud',mode);hud.close();assert hud._timer is None
            completion=CompletionDialog(app,dict(app.db.get_download(did),status='Tamamlandı'))
            snapshot(completion,'completion',mode)
            # The real two-sentence clean verdict once ran under the scan button.
            verdict='Taranan nesnelerde tehdit bulunmadı. Arşiv içeriğinin taranması Kaspersky ayarlarına bağlıdır.'
            with patch('antivirus.scan_file',return_value=(verdict,folder/'scan.log')):
                completion.scan();assert completion.scan_button.disabled
                wait(lambda:not completion.scan_button.disabled);app.update()
            assert completion.scan_status.get()=='Taranan nesnelerde tehdit bulunmadı.',completion.scan_status.get()
            assert completion.scan_detail.text=='Arşiv içeriğinin taranması Kaspersky ayarlarına bağlıdır.',completion.scan_detail.text
            edge=completion.scan_button.winfo_rootx()
            for line in (completion.scan_title,completion.scan_detail):
                assert line.winfo_rootx()+line.winfo_width()<=edge,(line.winfo_width(),edge)
            snapshot(completion,'completion-scanned',mode)
            completion.close()
            update=UpdateDialog(app,dict(version='0.5.1',notes='- Synthetic first change\n- Synthetic second change'))
            snapshot(update,'update',mode);update.close();assert not update.result
            # Named modal choices are exercised, not patched to always approve.
            def answer(key):
                window=next(w for w in app.winfo_children() if isinstance(w,MessageDialog))
                snapshot(window,'message',mode);window.actions[key].invoke()
            app.after(100,lambda:answer('cancel'))
            assert choose(app,'Synthetic deletion','Temporary files only',(('yes','Dosyaları sil','danger_solid'),('cancel','Vazgeç','ghost')),items=('fixture.bin',))=='cancel'
            tool=ToolsDialog(app);app.update();assert tool.winfo_exists()
            tool.mode.set('Video / ses kesme');app.update();assert tool.cut_fields.winfo_ismapped()
            tool.mode.set('Altyazı indirme');app.update();tool.choose_subtitles('https://example.invalid/video',str(folder),'srt',[('tr',False),('en',True)])
            assert len(tool.subtitle_host.winfo_children())==2
            snapshot(tool,'tools',mode);tool.close()
            assert not errors,errors
        # Exercise the GUI worker with real FFmpeg and only a synthetic local source.
        source=folder/'synthetic-source.wav';target=folder/'synthetic-output.mp3'
        subprocess.run([tool_path('ffmpeg'),'-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',str(source)],check=True,creationflags=NO_WINDOW)
        tool=ToolsDialog(app);tool.input.set(str(source));tool.format.set('mp3')
        wait(lambda:tool.timeline is not None,15);assert tool.timeline.duration>.9
        assert tool.source_card.winfo_ismapped() and not tool.source_box.winfo_ismapped()
        assert tool.quality_box.winfo_ismapped();tool.bitrate.set('128')
        with patch('feature_ui.filedialog.asksaveasfilename',return_value=str(target)),patch('feature_ui.reveal_file') as reveal:
            tool.run();wait(lambda:not tool.busy,15)
        assert target.is_file() and source.is_file() and .8<media_duration(target)<1.3,tool.status.get()
        # The footer promises the finished file opens selected in its folder.
        reveal.assert_called_once_with(target.resolve())
        assert tool.job_percent.text=='100%',tool.job_percent.text
        probe=subprocess.run([tool_path('ffprobe'),'-v','error','-select_streams','a:0','-show_entries','stream=bit_rate','-of','csv=p=0',str(target)],
                             capture_output=True,text=True,creationflags=NO_WINDOW)
        assert probe.stdout.strip()=='128000',probe.stdout  # the chosen Ses kalitesi reached FFmpeg
        tool.close();assert not errors,errors
        print('A03-A06/A14-A17/A19: automatic cards, decision safety, timeline validation, real task data, media worker, graph/HUD timers, explicit scan UI and light/dark previews: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
