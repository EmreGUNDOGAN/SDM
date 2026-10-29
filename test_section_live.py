"""Real FFmpeg range downloads against an isolated, optionally throttled local HTTP server."""
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path


def packets(ffprobe,path,select):
    rows=subprocess.run([ffprobe,'-v','error','-select_streams',select,'-show_entries','packet=pts_time','-of','csv=p=0',str(path)],capture_output=True,text=True).stdout.split()
    values=[v.split(',')[0] for v in rows]
    return [float(v) for v in values if v not in ('','N/A')]


def assert_continuous(times,step,label):
    assert times,label
    times=sorted(times)  # packets arrive in decode order; B-frames reorder presentation times
    gaps=[b-a for a,b in zip(times,times[1:])]
    assert all(g>0 for g in gaps),(label,'timestamps repeat or run backwards at a part seam')
    assert max(gaps)<step*1.6,(label,'frames are missing at a part seam',max(gaps))


def frame(ffmpeg,path,at):
    return subprocess.run([ffmpeg,'-v','error','-ss',str(at),'-i',str(path),'-frames:v','1','-vf','scale=160:90,format=gray','-f','rawvideo','-'],capture_output=True,check=True).stdout


def difference(a,b):
    return sum(abs(x-y) for x,y in zip(a,b))/max(1,len(a))


def main():
    from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
    from video_section import download_section,STATE
    from file_tools import tool_path,media_duration
    from video_downloader import VideoDownloadTask
    ffmpeg,ffprobe=tool_path('ffmpeg'),tool_path('ffprobe')
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);source=root/'source.mp4';video=root/'video.mp4';audio=root/'audio.mka'
        subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','testsrc=size=160x90:rate=25','-f','lavfi','-i','sine=frequency=440','-t','8','-c:v','libx264','-pix_fmt','yuv420p','-g','25','-c:a','aac','-movflags','+faststart',str(source)],check=True)
        # YouTube-like DASH: separate video (keyframe every 2 s) and audio whose
        # Matroska clusters/cues are 10 s apart, so a stream-copy seek lands ~10 s early.
        subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','testsrc=size=640x360:rate=25','-t','30','-c:v','libx264','-pix_fmt','yuv420p','-g','50','-keyint_min','50','-sc_threshold','0','-an','-movflags','+faststart',str(video)],check=True)
        subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=330','-t','30','-c:a','aac','-cluster_time_limit','10000','-cluster_size_limit','50000000',str(audio)],check=True)
        files={'/source.mp4':source.read_bytes(),'/video.mp4':video.read_bytes(),'/audio.mka':audio.read_bytes()}
        throttle={'delay':0.0}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                data=files[self.path];value=self.headers.get('Range');start=0;end=len(data)-1
                if value:
                    start_text,end_text=value.removeprefix('bytes=').split('-');start=int(start_text or 0);end=min(int(end_text) if end_text else end,len(data)-1)
                self.send_response(206 if value else 200)
                self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
                if value:self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
                self.end_headers()
                try:
                    for offset in range(start,end+1,4096):
                        self.wfile.write(data[offset:min(end+1,offset+4096)])
                        if throttle['delay']:time.sleep(throttle['delay'])
                except (ConnectionError,OSError):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        base=f'http://127.0.0.1:{server.server_port}'
        info={'title':'Fixture','duration':8,'url':base+'/source.mp4','protocol':'http','vcodec':'h264','acodec':'aac'}
        dash={'title':'Dash','duration':30,'requested_formats':[
            {'url':base+'/video.mp4','protocol':'http','vcodec':'h264','acodec':'none','format_id':'v','filesize':len(files['/video.mp4'])},
            {'url':base+'/audio.mka','protocol':'http','vcodec':'none','acodec':'aac','format_id':'a','filesize':len(files['/audio.mka'])}]}
        def run(name,source_info,section,audio_only=False,pause_at=None):
            out=root/name;out.mkdir();seen=[]
            task=VideoDownloadTask(1,base,out,section=section,is_audio_only=audio_only)
            task.progress_callback=lambda did,got,total,speed,eta,status:seen.append((got,total))
            if pause_at is not None:
                throttle['delay']=.1
                def pause():
                    while not any(total and got/total>=pause_at for got,total in seen):time.sleep(.05)
                    task._paused=True;task._cancel_flag.set()
                threading.Thread(target=pause,daemon=True).start()
                try:download_section(task,dict(source_info),out)
                except RuntimeError:pass
                else:raise AssertionError('Pause must stop the section download')
                throttle['delay']=0.0
                state=json.loads((out/STATE).read_text(encoding='utf-8'))
                assert len(state['parts'])==1 and state['parts'][0]['duration']>.5,('a paused part must be kept for resume',state)
                assert state['parts'][0]['next']<section['end']-1,('pause must stop before the section end so the seam is tested',state)
                task._paused=False;task._cancel_flag.clear()
            result=download_section(task,dict(source_info),out)
            assert not (out/STATE).exists() and not list(out.glob('section-part-*')),'parts must be cleaned after joining'
            return Path(result['requested_downloads'][0]['filepath']),seen
        try:
            for exact in (False,True):
                path,_=run(f'single-{exact}',info,{'start':2,'end':4,'exact':exact})
                duration=media_duration(path)
                assert 1.8<duration<3.2,(exact,duration)
                if exact:assert abs(duration-2)<.2,duration
            print('Single-file fast + exact section durations: OK')

            path,seen=run('dash-fast',dash,{'start':12,'end':20,'exact':False})
            first_video,first_audio=packets(ffprobe,path,'v:0')[0],packets(ffprobe,path,'a:0')[0]
            assert first_video<.25 and abs(first_audio)<.1,('fast cut must not start with audio-only seconds',first_video,first_audio)
            assert 7.8<media_duration(path)<10.2,media_duration(path)
            assert seen and all(total>0 for _,total in seen[2:]),('progress needs a known total',seen[:5])
            shares=[got/total for got,total in seen if total]
            assert all(b>=a-1e-9 for a,b in zip(shares,shares[1:])),('progress must not step back',shares)
            print('DASH fast cut starts on the video keyframe with real progress: OK')

            for name,section,step,audio_only in [('fast',{'start':4,'end':24,'exact':False},.04,False),('exact',{'start':5,'end':24,'exact':True},.04,False),('mp3',{'start':4,'end':24,'exact':False},None,True)]:
                path,_=run('resume-'+name,dash,section,audio_only=audio_only,pause_at=.35)
                length=section['end']-section['start'];duration=media_duration(path)
                assert abs(duration-length)<(2.2 if name=='fast' else .3),(name,duration)
                if step:assert_continuous(packets(ffprobe,path,'v:0'),step,name)
                if name=='exact':
                    first=frame(ffmpeg,path,0)
                    nearest=min((difference(first,frame(ffmpeg,video,section['start']+shift)),shift) for shift in (-1,-.5,-.04,0,.04,.5,1))[1]
                    assert nearest==0,('exact cut must start on the requested frame',nearest)
                assert_continuous(packets(ffprobe,path,'a:0'),.08,name+' audio')
            print('Pause and resume continue from the kept part without gaps or repeats (fast, exact, MP3): OK')

            out=root/'cancel';out.mkdir();task=VideoDownloadTask(2,info['url'],out,section={'start':2,'end':4,'exact':True});task._cancel_flag.set()
            try:download_section(task,dict(info),out)
            except RuntimeError:pass
            else:raise AssertionError('Cancel must stop FFmpeg')
            assert not list(out.glob('section-part-*')),'cancel must not keep parts'
            print('Real HTTP/FFmpeg section downloads and cancellation: OK')
        finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
