import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests
import browser_bridge
from video_downloader import format_options


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


if __name__ == '__main__':
    unittest.main()
