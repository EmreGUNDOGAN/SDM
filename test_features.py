import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from capture_policy import should_capture,capture_enabled,normalize_domain
from download_cleanup import delete_download_files
from download_engine import DownloadTask
from preferences import export_settings,import_settings
from utils import DEFAULT_SETTINGS
from updater import GitHubUpdater,UpdateError,API,save_token,load_token


class FeatureTests(unittest.TestCase):
    def test_canva_origin_and_subdomains_are_excluded(self):
        for source in ['https://canva.com/design','https://www.canva.com/design','https://editor.canva.com/design']:
            self.assertFalse(should_capture('https://cdn.example.com/file.zip',source,DEFAULT_SETTINGS))
        self.assertTrue(should_capture('https://example.com/a.zip','https://notcanva.com',DEFAULT_SETTINGS))

    def test_pause_and_filetype_preferences(self):
        settings=dict(DEFAULT_SETTINGS,capture_paused_until=200,capture_extensions=['zip'])
        self.assertFalse(capture_enabled(settings,100));self.assertTrue(capture_enabled(settings,201))
        settings['capture_paused_until']=0
        self.assertFalse(should_capture('https://example.com/a.mp4','',settings))
        self.assertTrue(should_capture('https://example.com/a.zip','',settings))
        settings['capture_paused_until']=-1;self.assertFalse(capture_enabled(settings,9999999999))

    def test_distinct_downloads_never_reuse_old_parts(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'a.zip';old=DownloadTask(1,'https://example.com/a',target)
            new=DownloadTask(2,'https://example.com/a',target)
            old.get_part_file(0).write_bytes(b'partial')
            self.assertFalse(new.get_part_file(0).exists())
            self.assertTrue(DownloadTask(1,'https://example.com/a',target).get_part_file(0).exists())

    def test_delete_after_restart_removes_legacy_and_scoped_parts(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'a.zip'
            names=['a.zip','a.zip.part.0','a.zip.part.31','a.zip.sdm-8.part.0','a.zip.temp_final','a.zip.sdm-8.temp_final']
            for name in names:(Path(folder)/name).write_bytes(b'partial')
            other=Path(folder)/'a.zip.sdm-9.part.0';other.write_bytes(b'other')
            delete_download_files({'id':8,'filepath':str(target),'download_type':'direct'})
            self.assertTrue(all(not (Path(folder)/name).exists() for name in names));self.assertTrue(other.exists())

    def test_settings_backup_never_exports_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            export_settings(path,dict(DEFAULT_SETTINGS,github_token='secret',token='secret'))
            self.assertNotIn('secret',path.read_text())
            self.assertEqual(import_settings(path)['excluded_sites'],['canva.com'])
            path.write_text(json.dumps({'format':'sdm-settings-v1','settings':{'default_connections':-1}}))
            with self.assertRaises(ValueError):import_settings(path)

    @unittest.skipUnless(os.name=='nt','Windows only')
    def test_update_token_is_encrypted(self):
        with tempfile.TemporaryDirectory() as folder,patch('updater.ensure_config_dir',return_value=Path(folder)):
            save_token('test-token-123');self.assertEqual(load_token(),'test-token-123')
            self.assertNotIn(b'test-token-123',(Path(folder)/'github-update-token.bin').read_bytes())
            save_token('');self.assertEqual(load_token(),'')

    def test_updater_rejects_wrong_size_and_digest(self):
        from unittest.mock import MagicMock
        content=b'MZtest setup'
        asset={'id':1,'name':'SDM-Setup-9.0.0.exe','size':len(content),'digest':'sha256:'+hashlib.sha256(content).hexdigest()}
        response=MagicMock();response.__enter__.return_value=response;response.iter_content.return_value=[content]
        updater=GitHubUpdater(token='')
        with tempfile.TemporaryDirectory() as folder,patch('updater.ensure_config_dir',return_value=Path(folder)),patch.object(updater,'_get',return_value=response):
            target=updater.download({'version':'v9.0.0','asset':asset});self.assertEqual(target.read_bytes(),content)
            asset['digest']='sha256:'+'0'*64
            with self.assertRaises(UpdateError):updater.download({'version':'v9.0.0','asset':asset})
            self.assertFalse(target.with_suffix('.part').exists())

    def test_updater_never_sends_token_to_redirect(self):
        from unittest.mock import MagicMock
        session=MagicMock();first=MagicMock(status_code=302,headers={'Location':'https://release-assets.githubusercontent.com/x'})
        second=MagicMock(status_code=200);session.get.side_effect=[first,second]
        updater=GitHubUpdater(token='private-token',session=session)
        updater._get(API+'/releases/assets/1',True)
        self.assertIn('Authorization',session.get.call_args_list[0].kwargs['headers'])
        self.assertNotIn('Authorization',session.get.call_args_list[1].kwargs['headers'])


class ParallelVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=b'Video stream fixture\x00'*100000;cls.ranges=[];cls.busy=0;cls.peak=0;cls.lock=threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                import time
                raw=self.headers.get('Range')
                start,end=map(int,raw.split('=')[1].split('-')) if raw else (0,len(cls.data)-1)
                with cls.lock:
                    cls.ranges.append((start,end));cls.busy+=1;cls.peak=max(cls.peak,cls.busy)
                try:
                    time.sleep(.05)
                    self.send_response(206 if raw else 200)
                    self.send_header('Content-Length',str(end-start+1));self.send_header('Content-Range',f'bytes {start}-{end}/{len(cls.data)}');self.end_headers()
                    self.wfile.write(cls.data[start:end+1])
                finally:
                    with cls.lock:cls.busy-=1
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()

    def test_yt_dlp_http_download_uses_parallel_sdm_engine(self):
        from yt_dlp import YoutubeDL
        from video_downloader import VideoDownloadTask
        from video_http import install_video_http_downloader
        install_video_http_downloader()
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'stream.mp4';owner=VideoDownloadTask(1,'unused',folder,connections=4)
            events=[]
            with YoutubeDL({'quiet':True,'outtmpl':str(target),'sdm_task':owner,'progress_hooks':[lambda event:events.append(event['status'])]}) as ydl:
                ydl.process_info({'id':'fixture','title':'fixture','url':f'http://127.0.0.1:{self.server.server_port}/stream.mp4','ext':'mp4','format_id':'fixture'})
            self.assertEqual(target.read_bytes(),self.data)
            self.assertGreaterEqual(self.peak,2);self.assertIn('finished',events)
            self.assertGreaterEqual(len([r for r in self.ranges if r!=(0,0)]),4)


if __name__=='__main__':unittest.main()
