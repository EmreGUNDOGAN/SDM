"""Real FFmpeg range download against an isolated local HTTP server."""
def main():
    from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
    from pathlib import Path
    import subprocess,tempfile,threading
    from video_section import download_section
    from file_tools import tool_path,media_duration
    from video_downloader import VideoDownloadTask
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);source=root/'source.mp4'
        subprocess.run([tool_path('ffmpeg'),'-v','error','-f','lavfi','-i','testsrc=size=160x90:rate=25','-f','lavfi','-i','sine=frequency=440','-t','8','-c:v','libx264','-pix_fmt','yuv420p','-g','25','-c:a','aac','-movflags','+faststart',str(source)],check=True)
        data=source.read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                value=self.headers.get('Range');start=0;end=len(data)-1
                if value:
                    start_text,end_text=value.removeprefix('bytes=').split('-');start=int(start_text or 0);end=min(int(end_text) if end_text else end,len(data)-1)
                self.send_response(206 if value else 200)
                self.send_header('Content-Type','video/mp4');self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
                if value:self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
                self.end_headers()
                try:self.wfile.write(data[start:end+1])
                except (ConnectionError,OSError):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        info={'title':'Fixture','duration':8,'url':f'http://127.0.0.1:{server.server_port}/source.mp4','protocol':'http','vcodec':'h264','acodec':'aac'}
        try:
            for exact in (False,True):
                out=root/str(exact);out.mkdir()
                task=VideoDownloadTask(1,info['url'],out,section={'start':2,'end':4,'exact':exact})
                result=download_section(task,dict(info),out);path=Path(result['requested_downloads'][0]['filepath'])
                duration=media_duration(path)
                assert 1.8<duration<3.2,(exact,duration)
                if exact:assert abs(duration-2)<.2,duration
            out=root/'cancel';out.mkdir();task=VideoDownloadTask(2,info['url'],out,section={'start':2,'end':4,'exact':True});task._cancel_flag.set()
            try:download_section(task,dict(info),out)
            except RuntimeError:pass
            else:raise AssertionError('Cancel must stop FFmpeg')
            print('Real HTTP/FFmpeg fast + exact section durations and cancellation: OK')
        finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
