import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from yt_dlp import YoutubeDL
from video_downloader import VideoDownloadTask,format_options
from video_http import install_video_http_downloader
from transfer_details import TransferDetails

class DetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=b'Download range fixture\x00'*100000;cls.fragment=b'Fragment fixture\x00'*4096;cls.requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path=='/list.m3u8':
                    text='#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n'+''.join(f'#EXTINF:1,\n/frag{i}.ts\n' for i in range(12))+'#EXT-X-ENDLIST\n'
                    content=text.encode();self.send_response(200);self.send_header('Content-Type','application/vnd.apple.mpegurl');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content);return
                data=cls.fragment if self.path.startswith('/frag') else cls.data
                raw=self.headers.get('Range') if self.path!='/single' else None
                start,end=map(int,raw.split('=')[1].split('-')) if raw else (0,len(data)-1)
                cls.requests.append((self.path,start,end))
                if self.path=='/bounded' and end-start+1>65536:
                    self.send_response(403);self.end_headers();return
                self.send_response(206 if raw else 200);self.send_header('Content-Length',str(end-start+1))
                if raw:self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
                self.end_headers()
                try:
                    for offset in range(start,end+1,8192):time.sleep(.002);self.wfile.write(data[offset:min(end+1,offset+8192)])
                except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=cls.server.serve_forever,daemon=True).start();install_video_http_downloader()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def download(self,route,extension='mp4',protocol='http',options=None):
        with tempfile.TemporaryDirectory() as folder:
            owner=VideoDownloadTask(9,'unused',folder,connections=4);path=Path(folder)/('output.'+extension)
            with YoutubeDL(dict(quiet=True,noprogress=True,outtmpl=str(path),sdm_task=owner,concurrent_fragment_downloads=4)) as ydl:
                ydl.process_info(dict(id='fixture',title='fixture',url=f'http://127.0.0.1:{self.server.server_port}{route}',ext=extension,protocol=protocol,format_id='fixture',vcodec='h264',acodec='none',downloader_options=options or {}))
            return path.read_bytes(),owner.transfer_details.snapshot()
    def test_bounded_parallel_ranges_and_actual_connection_counts(self):
        content,streams=self.download('/bounded',options={'http_chunk_size':65536})
        self.assertEqual(content,self.data);stream=streams[0]
        self.assertEqual(stream['method'],'HTTP Range');self.assertEqual(len(stream['rows']),4)
        self.assertEqual(sum(r['received'] for r in stream['rows']),len(self.data))
        self.assertGreaterEqual(stream['peak'],2);self.assertEqual(stream['active_count'],0)
        self.assertTrue(all(end-start+1<=65536 for url,start,end in self.requests if url=='/bounded'))
    def test_native_fallback_reports_one_instead_of_configured_four(self):
        content,streams=self.download('/single')
        self.assertEqual(content,self.data);self.assertEqual(streams[0]['method'],'Tek HTTP bağlantısı')
        self.assertEqual(streams[0]['peak'],1);self.assertEqual(len(streams[0]['rows']),1)
        self.assertIn('Range',streams[0]['reason'])
    def test_real_hls_fragments_have_separate_byte_counters(self):
        content,streams=self.download('/list.m3u8','ts','m3u8_native')
        self.assertEqual(content,self.fragment*12);stream=streams[0]
        self.assertEqual(stream['method'],'HLS parçaları');self.assertEqual(len(stream['rows']),12)
        self.assertTrue(all(r['received']==len(self.fragment) and r['state']=='Tamamlandı' for r in stream['rows']))
        self.assertGreaterEqual(stream['peak'],2);self.assertEqual(stream['active_count'],0)
    def test_fragment_history_is_bounded_and_unknown_is_not_zero(self):
        details=TransferDetails();details.begin('hls','HLS parçaları','Video')
        self.assertIsNone(details.snapshot()[0]['active_count'])
        for i in range(1000):details.progress('hls',str(i),i,100,100,False,'Tamamlandı')
        stream=details.snapshot()[0];self.assertLessEqual(len(stream['rows']),80);self.assertEqual(stream['completed'],1000)
    def test_bitrate_size_is_marked_estimated(self):
        data=format_options({'title':'video','duration':100,'formats':[{'height':720,'vcodec':'h264','acodec':'none','tbr':800,'ext':'mp4'},{'vcodec':'none','acodec':'aac','tbr':128}]})
        self.assertEqual(data['qualities'][0]['filesize'],11600000);self.assertTrue(data['qualities'][0]['estimated'])

if __name__=='__main__':unittest.main()
