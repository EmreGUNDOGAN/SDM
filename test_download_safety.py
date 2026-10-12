import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from download_engine import DownloadTask

DATA = b'SDM test payload' * 10000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        start, end = map(int, self.headers['Range'].split('=')[1].split('-'))
        body = DATA[start:end + 1]
        self.send_response(200 if self.path == '/ignored' else 206)
        self.send_header('Content-Range', f'bytes {start}-{end}/{len(DATA)}')
        if self.path == '/short' and (start != 0 or end != 0):
            body = body[:-1]
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DownloadSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def download(self, route):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result.bin'
            task = DownloadTask(1, f'http://127.0.0.1:{self.server.server_port}/{route}', target, 4)
            if route == 'ignored':
                task.filesize = len(DATA)
                task.supports_ranges = True
            with patch('download_engine.time.sleep'):
                task._run()
            return task.status, target.read_bytes() if target.exists() else None

    def test_parallel_download_is_exact(self):
        self.assertEqual(self.download('valid'), ('Tamamlandı', DATA))

    def test_ignored_range_never_publishes_file(self):
        self.assertEqual(self.download('ignored'), ('Hata', None))

    def test_truncated_response_never_publishes_file(self):
        self.assertEqual(self.download('short'), ('Hata', None))
