import json
import hashlib
import os
import socket
import threading
from pathlib import Path
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

import requests
import browser_bridge
from video_downloader import format_options
from stream_media import StreamDRMError, StreamValidationError, StreamSession, page_headers, public_addresses, stream_spec


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.path_patch = patch('browser_bridge.ensure_config_dir', return_value=Path(cls.folder.name))
        cls.path_patch.start()
        cls.port_patch=patch('browser_bridge.PORT',0);cls.port_patch.start()
        cls.bridge = browser_bridge.BrowserBridge()
        browser_bridge.PORT=cls.bridge.server.server_port
        cls.bridge.start()

    @classmethod
    def tearDownClass(cls):
        cls.bridge.stop()
        cls.path_patch.stop()
        cls.port_patch.stop()
        cls.folder.cleanup()

    def request(self, path='/download', headers=None, body=None):
        headers = headers or {'Origin': browser_bridge.ORIGIN,
                              'Authorization': 'Bearer ' + self.bridge.token}
        return requests.post(f'http://127.0.0.1:{browser_bridge.PORT}{path}',
                             headers=headers, json=body or {
                                 'url': 'https://www.youtube.com/watch?v=example',
                                 'height': 1080, 'audio': False}, timeout=5)

    def test_no_auth_is_denied(self):
        self.assertEqual(self.request(headers={'Origin': browser_bridge.ORIGIN}).status_code, 403)

    def test_web_page_origin_is_denied(self):
        self.assertEqual(self.request(headers={'Origin': 'https://www.youtube.com',
                         'Authorization': 'Bearer ' + self.bridge.token}).status_code, 403)

    def test_queued_quality_is_preserved(self):
        self.assertEqual(self.request().status_code, 202)
        self.assertEqual(self.bridge.pending.get_nowait()['height'], 1080)

    def test_mp3_is_queued(self):
        self.assertEqual(self.request(body={'url': 'https://youtu.be/example',
                         'height': None, 'audio': True}).status_code, 202)
        self.assertTrue(self.bridge.pending.get_nowait()['audio'])

    def test_page_scan_batch_opens_selection(self):
        urls=['https://cdn.example.com/a.mp3','https://cdn.example.com/a.mp3','http://192.168.1.1/router.bin',
              'http://localhost/x.zip','https://files.example.org/b.zip']
        reply=self.request('/batch',body={'urls':urls})
        self.assertEqual((reply.status_code,reply.json()['count']),(202,2))
        queued=self.bridge.pending.get_nowait()
        # Duplicates and local addresses never reach the batch window.
        self.assertEqual((queued['kind'],queued['urls']),('batch',['https://cdn.example.com/a.mp3','https://files.example.org/b.zip']))
        self.assertEqual(self.bridge.decisions[queued['ticket']]['action'],'start')

    def test_music_button_queues_without_dialog(self):
        reply=self.request('/music',body={'url':'https://music.youtube.com/playlist?list=OLAK5uy_x','bitrate':320,'list':True})
        self.assertEqual(reply.status_code,202)
        queued=self.bridge.pending.get_nowait()
        self.assertEqual((queued['kind'],queued['bitrate'],queued['list']),('music',320,True))
        self.assertEqual(self.bridge.decisions[queued['ticket']]['action'],'start')
        for body in ({'url':'https://music.youtube.com/watch?v=x','bitrate':64},{'url':'https://music.youtube.com/watch?v=x','bitrate':'320'},
                     {'url':'https://music.youtube.com/watch?v=x','bitrate':192,'list':'yes'},{'url':'https://www.youtube.com/watch?v=x','bitrate':192}):
            with self.subTest(body=body):self.assertEqual(self.request('/music',body=body).status_code,400)

    def test_page_scan_batch_limits(self):
        for urls in ([],['https://e.example/x.zip']*(browser_bridge.BATCH_LIMIT+1),['file:///C:/x.zip'],
                     ['https://user:pw@e.example/x.zip'],['http://127.0.0.1/x.zip'],'https://e.example/x.zip'):
            with self.subTest(urls=str(urls)[:60]):
                self.assertEqual(self.request('/batch',body={'urls':urls}).status_code,400)
        self.assertEqual(self.request('/download',body={'url':'https://youtu.be/x','audio':True,'pad':'x'*20000}).status_code,400)

    def test_local_and_spoofed_urls_are_denied(self):
        for url in ['http://127.0.0.1/test', 'file:///C:/test',
                    'https://youtube.com.evil.example/video', 'https://user:pass@youtube.com/video']:
            with self.subTest(url=url):
                self.assertEqual(self.request(body={'url': url, 'height': 720}).status_code, 400)

    def test_real_formats_and_drm_filter(self):
        info = {'title': 'Test', 'formats': [
            {'height': 1080, 'vcodec': 'avc1', 'acodec': 'none'},
            {'height': 1080, 'vcodec': 'vp9', 'acodec': 'none'},
            {'height': 720, 'vcodec': 'avc1', 'acodec': 'aac'},
            {'height': 2160, 'vcodec': 'avc1', 'has_drm': True}]}
        options = format_options(info)
        self.assertEqual([q['height'] for q in options['qualities']], [1080, 720])
        self.assertTrue(options['audio'])

    def test_authenticated_client_status_and_invalid_metadata(self):
        self.assertEqual(self.request('/ping',body={'client':{'browser':'Chrome','version':'0.5.0'}}).status_code,200)
        self.assertEqual(self.bridge.client_snapshot()['Chrome']['version'],'0.5.0')
        self.request('/ping',body={'client':{'browser':'Chrome','version':'untrusted\nvalue'}})
        self.assertEqual(self.bridge.client_snapshot()['Chrome']['version'],'0.5.0')
        self.assertEqual(self.request('/ping',headers={'Origin':browser_bridge.ORIGIN},body={'client':{'browser':'Opera','version':'0.5.0'}}).status_code,403)
        self.assertNotIn('Opera',self.bridge.client_snapshot())

    def test_formats_endpoint(self):
        with patch('video_downloader.fetch_video_formats', return_value={
                'title': 'Test', 'qualities': [{'height': 720, 'label': '720p'}], 'audio': True}):
            response = self.request('/formats')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['qualities'][0]['height'], 720)
            self.assertEqual(response.json()['design'], 'atlas')

    def test_design_reaches_extension(self):
        # The video button styles itself from this (P07 Pano / F07 Yörünge).
        for design in ('pano', 'yorunge'):
            with self.subTest(design=design), patch('browser_bridge.load_settings', return_value={'design': design}):
                self.assertEqual(self.request('/settings', body={}).json()['design'], design)

    def stream_request(self, path='/stream-formats', **fields):
        body=dict(media_url='https://cdn.example/master.m3u8',page_url='https://site.example/watch',
                  kind='hls',title='Fixture',height=720,audio=False,filesize=0)
        body.update(fields)
        return self.request(path,body=body)

    def test_stream_security_envelope(self):
        for route in ('/stream-formats','/stream-download'):
            for headers in ({'Origin':browser_bridge.ORIGIN},
                    {'Origin':'https://site.example','Authorization':'Bearer '+self.bridge.token},
                    {'Origin':browser_bridge.ORIGIN,'Authorization':'Bearer '+self.bridge.token,'Host':'localhost'}):
                with self.subTest(route=route,headers=list(headers)):
                    self.assertEqual(self.request(route,headers=headers).status_code,403)
            self.assertEqual(self.stream_request(route,title='x'*20000).status_code,400)
        self.assertEqual(self.stream_request(title='x'*241).status_code,400)

    def test_stream_invalid_urls_and_fields(self):
        for field in ('media_url','page_url'):
            for value in ('file:///C:/fixture','ftp://cdn.example/a','https://u:p@cdn.example/a',
                          'https://@cdn.example/a','https://cdn.example:0/a','https://cdn.example:bad/a',
                          'https://cdn.example/\r\nCookie:x','https://cdn.example/'+'x'*8192,None):
                with self.subTest(field=field,value=str(value)[:50]):
                    self.assertEqual(self.stream_request(**{field:value}).status_code,400)
        for fields in (dict(kind='blob'),dict(kind=None),dict(title=123),dict(height=True),dict(height=-1),
                       dict(height=16385),dict(audio='yes'),dict(filesize=-1),dict(filesize=True)):
            with self.subTest(fields=fields):
                self.assertEqual(self.stream_request('/stream-download',**fields).status_code,400)

    def test_stream_private_addresses_are_denied_before_connection(self):
        for host in ('localhost','a.localhost','127.0.0.1','127.1','2130706433','0x7f000001',
                     '10.1.2.3','172.16.0.1','192.168.1.1','169.254.169.254','100.64.0.1',
                     '0.2.3.4','224.0.0.1','[::1]','[fc00::1]','[fe80::1]','[ff02::1]',
                     '[::ffff:127.0.0.1]','[64:ff9b::7f00:1]'):
            with self.subTest(host=host),patch('stream_media._socket') as connect:
                self.assertEqual(self.stream_request(media_url=f'http://{host}/a.m3u8').status_code,400)
                connect.assert_not_called()

    def test_stream_exclusions_cover_page_and_media(self):
        for settings in ({'excluded_sites':['site.example']},{'excluded_sites':['cdn.example']},
                         {'browser_capture':False},{'capture_extensions':['zip']}):
            for route in ('/stream-formats','/stream-download'):
                with self.subTest(settings=settings,route=route),patch('browser_bridge.load_settings',return_value=settings),patch('browser_bridge.fetch_stream_formats') as fetch:
                    reply=self.stream_request(route)
                    self.assertEqual((reply.status_code,reply.json()['error']),(409,'Bu sitede SDM yakalaması kapalı'))
                    fetch.assert_not_called()

    def test_stream_drm_and_access_errors(self):
        for route in ('/stream-formats','/stream-download'):
            with patch('browser_bridge.fetch_stream_formats',side_effect=StreamDRMError()):
                reply=self.stream_request(route)
                self.assertEqual((reply.status_code,reply.json()['error']),(400,'Bu video korumalı (DRM); indirilemez.'))
            with patch('browser_bridge.fetch_stream_formats',side_effect=RuntimeError('fixture access denied')):
                self.assertEqual(self.stream_request(route).status_code,502)

    def test_stream_ticket_preserves_only_allowed_headers_and_client(self):
        with patch('browser_bridge.fetch_stream_formats',return_value={'title':'Fixture','qualities':[],'audio':False}):
            reply=self.stream_request('/stream-download',kind='file',media_url='https://cdn.example/a.mp4',height=0,
                headers={'Cookie':'do-not-forward','Authorization':'do-not-forward'},
                client={'browser':'Edge','version':'1.1.0'})
        self.assertEqual(reply.status_code,202)
        queued=self.bridge.pending.get_nowait()
        self.assertEqual(queued['headers'],page_headers('https://site.example/watch'))
        self.assertEqual(queued['stream'],{'kind':'file','page_url':'https://site.example/watch'})
        self.assertEqual(queued['height'],0)
        ticket=reply.json()['ticket']
        self.assertEqual(self.request('/decision',body={'ticket':ticket}).json()['action'],'pending')
        self.bridge.decide(ticket,'queue')
        self.assertEqual(self.request('/decision',body={'ticket':ticket}).json()['action'],'queue')
        self.assertEqual(self.bridge.client_snapshot()['Edge']['version'],'1.1.0')


class StreamTransportTests(unittest.TestCase):
    def test_no_formats_stays_empty(self):
        from stream_media import fetch_stream_formats
        for kind in ('file','hls','dash'):
            with self.subTest(kind=kind),patch('stream_media.StreamYoutubeDL.extract_info',return_value={'title':'Empty','formats':[]}):
                self.assertEqual(fetch_stream_formats('https://cdn.example/empty','https://site.example/watch',kind)['qualities'],[])

    def test_stream_queue_dialog_forwards_headers_and_keeps_chosen_filename(self):
        from capture_dialog import CapturePrompt
        with tempfile.TemporaryDirectory() as folder:
            calls=[]
            spec,headers=stream_spec('https://cdn.example/a.mp4','https://site.example/watch','file')
            value=lambda v:SimpleNamespace(get=lambda:v)
            dialog=SimpleNamespace(_done=False,validate=lambda:True,name=value('Chosen.mkv'),folder=value(folder),
                quality=value('0'),section_fields=None,selected_size=0,
                request={'url':'https://cdn.example/a.mp4','kind':'video','stream':spec,'headers':headers,'ticket':'fixture'},
                parent=SimpleNamespace(add_download_from_dialog=lambda *args,**kwargs:calls.append(kwargs) or 1),
                decision=lambda *a:None,destroy=lambda:None,error=SimpleNamespace(set=lambda v:self.fail(v)))
            CapturePrompt.choose(dialog,'queue')
            self.assertEqual((calls[0]['stream'],calls[0]['headers'],calls[0]['selected_height']),(spec,headers,0))
            self.assertTrue(calls[0]['from_browser']);self.assertFalse(calls[0]['auto_start'])

    def test_only_canonical_page_origin_and_referer_are_accepted(self):
        self.assertEqual(page_headers('https://EXAMPLE.com:443/a'),
            {'Referer':'https://EXAMPLE.com:443/a','Origin':'https://example.com'})
        for extra in ('Cookie','Authorization','User-Agent'):
            with self.subTest(extra=extra),self.assertRaises(StreamValidationError):
                StreamSession(dict(page_headers('https://site.example/a'),**{extra:'synthetic'}))

    def test_every_dns_answer_is_checked_and_no_connection_on_rebinding(self):
        for addresses in (['93.184.215.14','10.0.0.1'],['10.0.0.1'],['::1']):
            answers=[(socket.AF_INET6 if ':' in ip else socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in addresses]
            with self.subTest(addresses=addresses),patch('stream_media.socket.getaddrinfo',return_value=answers),patch('stream_media._socket') as connect:
                with self.assertRaises(StreamValidationError):
                    StreamSession(page_headers('https://site.example/watch')).get('https://cdn.example/video')
                connect.assert_not_called()

    def test_validated_sockaddr_is_used_without_second_resolution(self):
        # A synthetic socket checks pinning; real HTTP behavior is checked below.
        answers=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.215.14',80))]
        with patch('stream_media.socket.getaddrinfo',return_value=answers) as dns,patch('stream_media._socket') as sock,patch('stream_media.http.client.HTTPConnection') as connection:
            raw=connection.return_value.getresponse.return_value
            raw.getheaders.return_value=[('Content-Length','0')];raw.status=200;raw.reason='OK'
            response=StreamSession(page_headers('https://site.example/watch')).get('http://cdn.example/video',stream=True)
            self.assertEqual(dns.call_count,1)
            sock.return_value.connect.assert_called_once_with(('93.184.215.14',80))
            response.close()

    def test_loopback_exception_requires_test_mode_data_dir_and_exact_port(self):
        env={'SDM_TEST_STREAM_ORIGIN':'http://127.0.0.1:54321','SDM_TEST_MODE':'1','SDM_DATA_DIR':'disposable'}
        with patch.dict(os.environ,env):
            public_addresses('http://127.0.0.1:54321/a')
            for url in ('http://127.0.0.1:54322/a','http://localhost:54321/a','http://127.0.0.2:54321/a'):
                with self.assertRaises(StreamValidationError):public_addresses(url)
            with patch.dict(os.environ,{'SDM_TEST_MODE':'0'}):
                with self.assertRaises(StreamValidationError):public_addresses('http://127.0.0.1:54321/a')

    def test_drm_filter_and_native_hls_guard(self):
        from stream_media import checked_info
        from video_fragments import GuardedHlsFD
        with self.assertRaises(StreamDRMError):checked_info({'formats':[{'has_drm':True}]},'dash')
        info={'formats':[{'protocol':'http_dash_segments','height':720},
                         {'has_drm':True,'protocol':'http_dash_segments','height':1080}]}
        self.assertEqual(len(checked_info(info,'dash')['formats']),1)
        with self.assertRaises(StreamDRMError):
            GuardedHlsFD.can_download('#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI="skd://fixture"',{})
        with self.assertRaises(StreamValidationError):
            GuardedHlsFD.can_download('#EXTM3U\n',{'is_live':True})


class RealStreamTests(unittest.TestCase):
    """Real HTTP manifests/fragments, response status and SHA-256; no real profile."""
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory();cls.seen=[]
        cls.fragment=b'Captured stream fixture\x00'*4096
        cls.file=b'Range stream fixture\x00'*100000
        cls.page='https://site.example/watch/1'
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                cls.seen.append((self.path,dict(self.headers)))
                if self.headers.get('Referer')!=cls.page or self.headers.get('Origin')!='https://site.example':
                    self.send_response(403);self.send_header('Content-Length','0');self.end_headers();return
                if self.path=='/redirect':
                    self.send_response(302);self.send_header('Location','/master.m3u8');self.send_header('Set-Cookie','fixture=secret');self.send_header('Content-Length','0');self.end_headers();return
                if self.path=='/private':
                    self.send_response(302);self.send_header('Location','http://127.0.0.2/private');self.send_header('Content-Length','0');self.end_headers();return
                if self.path=='/master.m3u8':
                    content=b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=1280x720,CODECS="avc1.64001f,mp4a.40.2"\n/list.m3u8\n';mime='application/vnd.apple.mpegurl'
                elif self.path in ('/video.mpd','/drm.mpd'):
                    protection='<ContentProtection schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"/>' if self.path=='/drm.mpd' else ''
                    content=('<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT4S" minBufferTime="PT1S">'
                        '<Period duration="PT4S"><AdaptationSet mimeType="video/mp4" codecs="avc1.64001f" contentType="video">'+protection+
                        '<Representation id="v720" bandwidth="800000" width="1280" height="720"><SegmentList timescale="1" duration="1">'
                        '<Initialization sourceURL="/init.m4s"/>'+''.join(f'<SegmentURL media="/dash{i}.m4s"/>' for i in range(4))+
                        '</SegmentList></Representation></AdaptationSet></Period></MPD>').encode();mime='application/dash+xml'
                elif self.path in ('/list.m3u8','/bad.m3u8','/drm.m3u8','/key.m3u8'):
                    segments='http://127.0.0.2/forbidden.ts' if self.path=='/bad.m3u8' else '/frag.ts'
                    key=('#EXT-X-KEY:METHOD=SAMPLE-AES,URI="skd://fixture",KEYFORMAT="com.apple.streamingkeydelivery"\n'
                         if self.path=='/drm.m3u8' else '#EXT-X-KEY:METHOD=AES-128,URI="http://127.0.0.2/key",IV=0x00000000000000000000000000000000\n'
                         if self.path=='/key.m3u8' else '')
                    content=('#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n'+key+''.join(f'#EXTINF:1,\n{segments}\n' for _ in range(4))+'#EXT-X-ENDLIST\n').encode();mime='application/vnd.apple.mpegurl'
                elif self.path=='/video.mp4':content=cls.file;mime='video/mp4'
                else:content=cls.fragment;mime='video/mp2t'
                start,end=0,len(content)-1;range_header=self.headers.get('Range')
                if range_header:
                    left,right=range_header.split('=')[1].split('-');start=int(left);end=min(int(right) if right else end,end)
                self.send_response(206 if range_header else 200);self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
                self.send_header('Set-Cookie','fixture=secret')
                if range_header:self.send_header('Content-Range',f'bytes {start}-{end}/{len(content)}')
                self.end_headers()
                try:self.wfile.write(content[start:end+1])
                except (BrokenPipeError,ConnectionError):pass
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.env=patch.dict(os.environ,{'SDM_TEST_MODE':'1','SDM_TEST_STREAM_ORIGIN':cls.base,'SDM_DATA_DIR':cls.folder.name});cls.env.start()
        cls.config=patch('browser_bridge.ensure_config_dir',return_value=Path(cls.folder.name));cls.config.start()
        cls.port=patch('browser_bridge.PORT',0);cls.port.start()
        cls.bridge=browser_bridge.BrowserBridge();browser_bridge.PORT=cls.bridge.server.server_port;cls.bridge.start()

    @classmethod
    def tearDownClass(cls):
        cls.bridge.stop();cls.server.shutdown();cls.server.server_close()
        cls.port.stop();cls.config.stop();cls.env.stop();cls.folder.cleanup()

    def request(self,route,source,kind='hls',**extra):
        body=dict(media_url=self.base+source,page_url=self.page,kind=kind,title='Safe fixture',height=720,audio=False,filesize=0);body.update(extra)
        return requests.post(f'http://127.0.0.1:{browser_bridge.PORT}'+route,json=body,
            headers={'Origin':browser_bridge.ORIGIN,'Authorization':'Bearer '+self.bridge.token},timeout=15)

    def run_task(self,route,kind='hls',height=720):
        from video_downloader import VideoDownloadTask
        reply=self.request('/stream-download',route,kind,height=height)
        self.assertEqual(reply.status_code,202,reply.text)
        request=self.bridge.pending.get_nowait()
        task=VideoDownloadTask(44,request['url'],self.folder.name,selected_height=request['height'],
            output_name='fixture',stream=request['stream'],http_headers=request['headers'],connections=3)
        task._run()
        return task

    def test_real_hls_bridge_download_and_no_cookie_on_redirect_or_fragments(self):
        denied=requests.get(self.base+'/master.m3u8',timeout=5)
        self.assertEqual(denied.status_code,403)
        self.seen.clear()
        reply=self.request('/stream-formats','/redirect')
        self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual([q['height'] for q in reply.json()['qualities']],[720])
        task=self.run_task('/redirect')
        self.assertEqual(task.status,'Tamamlandı',task.error_message)
        self.assertEqual(hashlib.sha256(Path(task.target_filepath).read_bytes()).digest(),hashlib.sha256(self.fragment*4).digest())
        details=task.transfer_details.snapshot()
        self.assertEqual(details[0]['method'],'HLS parçaları')
        self.assertEqual(len(details[0]['rows']),4)
        self.assertTrue(any(path=='/frag.ts' for path,_ in self.seen))
        for _,headers in self.seen:
            headers={k.lower():v for k,v in headers.items()}
            self.assertEqual(headers.get('referer'),self.page)
            self.assertEqual(headers.get('origin'),'https://site.example')
            self.assertNotIn('cookie',headers);self.assertNotIn('authorization',headers)
            self.assertTrue(set(headers)<= {'host','referer','origin','accept-encoding','connection','range'})

    def test_real_file_original_quality_and_range_download(self):
        reply=self.request('/stream-formats','/video.mp4','file',height=0)
        self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual((reply.json()['qualities'][0]['height'],reply.json()['qualities'][0]['label']),(0,'Orijinal'))
        task=self.run_task('/video.mp4','file',0)
        self.assertEqual(task.status,'Tamamlandı',task.error_message)
        self.assertEqual(hashlib.sha256(Path(task.target_filepath).read_bytes()).digest(),hashlib.sha256(self.file).digest())
        self.assertTrue(any('Range' in headers for path,headers in self.seen if path=='/video.mp4'))

    def test_redirect_and_manifest_segment_cannot_reach_private_host(self):
        reply=self.request('/stream-formats','/private')
        self.assertEqual(reply.status_code,400,reply.text)
        with patch('stream_media.public_addresses',wraps=public_addresses) as addresses:
            task=self.run_task('/bad.m3u8',height=0)
        self.assertEqual(task.status,'Hata')
        self.assertTrue(any(call.args[0]=='http://127.0.0.2/forbidden.ts' for call in addresses.call_args_list))

    def test_real_dash_metadata_download_and_drm_rejection(self):
        reply=self.request('/stream-formats','/video.mpd','dash')
        self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual([q['height'] for q in reply.json()['qualities']],[720])
        task=self.run_task('/video.mpd','dash')
        self.assertEqual(task.status,'Tamamlandı',task.error_message)
        self.assertEqual(hashlib.sha256(Path(task.target_filepath).read_bytes()).digest(),hashlib.sha256(self.fragment*5).digest())
        for route in ('/stream-formats','/stream-download'):
            reply=self.request(route,'/drm.mpd','dash')
            self.assertEqual((reply.status_code,reply.json()['error']),(400,'Bu video korumalı (DRM); indirilemez.'))

    def test_hls_drm_and_private_aes_key_are_blocked(self):
        for route in ('/stream-formats','/stream-download'):
            reply=self.request(route,'/drm.m3u8',height=0)
            self.assertEqual((reply.status_code,reply.json()['error']),(400,'Bu video korumalı (DRM); indirilemez.'))
        with patch('stream_media.public_addresses',wraps=public_addresses) as addresses:
            task=self.run_task('/key.m3u8',height=0)
        self.assertEqual(task.status,'Hata')
        self.assertTrue(any(call.args[0]=='http://127.0.0.2/key' for call in addresses.call_args_list))

    def test_response_cookies_and_explicit_auth_are_not_forwarded(self):
        self.seen.clear()
        with StreamSession(page_headers(self.page)) as session:
            session.cookies.set('fixture','must-not-send')
            with session.get(self.base+'/redirect',headers={'Cookie':'must-not-send','Authorization':'Basic synthetic'},stream=True) as response:
                self.assertEqual(response.status_code,200)
                self.assertNotIn('Set-Cookie',response.headers)
        self.assertEqual(len(self.seen),2)
        self.assertTrue(all('Cookie' not in headers and 'Authorization' not in headers for _,headers in self.seen))

    def test_queue_persists_headers_and_recreates_guarded_task(self):
        from database import DownloadDatabase
        from gui import MainWindow
        from utils import DEFAULT_SETTINGS
        with tempfile.TemporaryDirectory() as folder,patch.object(DownloadDatabase,'_instance',None):
            db=DownloadDatabase(Path(folder)/'fixture.db')
            host=SimpleNamespace(db=db,settings=dict(DEFAULT_SETTINGS,disk_check=False,auto_open_details=False),
                check_duplicate=lambda *a:False,video_tasks={},engine=SimpleNamespace(get_task=lambda did:None),
                _session_baselines={},_session_received={},refresh_downloads=lambda:None,
                _on_download_progress=lambda *a:None,_on_download_status_change=lambda *a:None,
                _on_metadata_updated=lambda *a:None)
            spec,headers=stream_spec(self.base+'/video.mp4',self.page,'file')
            did=MainWindow.add_download_from_dialog(host,self.base+'/video.mp4','queued.mp4',str(Path(folder)/'queued.mp4'),
                is_video=True,auto_start=False,from_browser=True,selected_height=0,headers=headers,stream=spec)
            record=db.get_download(did)
            self.assertEqual(record['status'],'Kuyrukta')
            self.assertEqual(json.loads(record['headers']),headers)
            self.assertEqual(json.loads(record['options_json'])['stream'],spec)
            self.assertEqual(json.loads(record['options_json'])['output_name'],'queued.mp4')
            del host.video_tasks[did]  # Simulate application restart; restore from SQLite.
            self.assertTrue(MainWindow.resume_download(host,did))
            restored=host.video_tasks[did]
            self.assertEqual(restored.http_headers,headers)
            restored._run()
            self.assertEqual(restored.status,'Tamamlandı',restored.error_message)
            self.assertEqual(Path(restored.target_filepath).name,'queued.mp4')
            self.assertEqual(hashlib.sha256(Path(restored.target_filepath).read_bytes()).digest(),hashlib.sha256(self.file).digest())


if __name__ == '__main__':
    unittest.main()
