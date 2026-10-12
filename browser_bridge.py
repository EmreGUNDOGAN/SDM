"""Authenticated, loopback-only browser bridge. No browser cookie access."""
import hmac
import json
import os
import queue
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from utils import ensure_config_dir, load_settings

PORT = int(os.environ.get('SDM_BRIDGE_PORT', '49282'))
EXTENSION_ID = 'eipmgfnkhpeaefhjpbgkccckcacafjkj'
ORIGIN = 'chrome-extension://' + EXTENSION_ID


def get_token():
    path = ensure_config_dir() / 'browser-token.txt'
    try:
        with path.open('x', encoding='ascii') as stream:
            stream.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    return path.read_text(encoding='ascii').strip()


def validate_url(url):
    if not isinstance(url, str) or len(url) > 8192:
        raise ValueError('Geçersiz video adresi')
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError('Geçersiz video adresi')
    host = (parsed.hostname or '').lower()
    # Supported page URLs only. Local network and arbitrary file paths excluded.
    domains = ('youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
               'tiktok.com', 'instagram.com', 'x.com', 'twitter.com',
               'facebook.com', 'twitch.tv', 'soundcloud.com')
    if not any(host == d or host.endswith('.' + d) for d in domains):
        raise ValueError('Bu site henüz SDM tarayıcı entegrasyonunda desteklenmiyor')
    return url


class BrowserBridge:
    def __init__(self):
        self.pending = queue.Queue(maxsize=32)
        self.token = get_token()
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def permitted(self):
                return (self.headers.get('Host') == f'127.0.0.1:{PORT}'
                        and self.headers.get('Origin') == ORIGIN)

            def send_json(self, status, data):
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                if self.permitted():
                    self.send_header('Access-Control-Allow-Origin', ORIGIN)
                    self.send_header('Vary', 'Origin')
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                if not self.permitted():
                    return self.send_json(403, {'error': 'Erişim reddedildi'})
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin', ORIGIN)
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()

            def do_POST(self):
                if not self.permitted() or not hmac.compare_digest(
                        self.headers.get('Authorization', ''), 'Bearer ' + bridge.token):
                    return self.send_json(403, {'error': 'Erişim reddedildi'})
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 16384:
                        raise ValueError('Geçersiz istek boyutu')
                    self.connection.settimeout(10)
                    data = json.loads(self.rfile.read(size))
                    if self.path == '/ping':
                        return self.send_json(200, {'ok': True, 'version': '0.3.0'})
                    if self.path == '/settings':
                        return self.send_json(200, {'capture':load_settings().get('browser_capture',True)})
                    if self.path == '/file':
                        if not load_settings().get('browser_capture',True):
                            return self.send_json(409,{'error':'Tarayıcıdan yakalama kapalı'})
                        from browser_files import prepare_transfer
                        request=prepare_transfer(data.get('url'))
                        bridge.pending.put_nowait(request)
                        return self.send_json(202,{'ok':True})
                    url = validate_url(data.get('url'))
                    if self.path == '/formats':
                        from video_downloader import fetch_video_formats
                        return self.send_json(200, fetch_video_formats(url))
                    if self.path == '/download':
                        height = data.get('height')
                        audio = data.get('audio', False)
                        if not isinstance(audio, bool) or (not audio and
                                (type(height) is not int or not 1 <= height <= 16384)):
                            raise ValueError('Geçersiz kalite seçimi')
                        bridge.pending.put_nowait({'kind':'video','url': url, 'height': height, 'audio': audio})
                        return self.send_json(202, {'ok': True})
                    self.send_json(404, {'error': 'Bilinmeyen işlem'})
                except (ValueError, TypeError, queue.Full):
                    self.send_json(400, {'error': 'Geçersiz veya desteklenmeyen istek'})
                except Exception:
                    self.send_json(502, {'error': 'Video bilgisi alınamadı. Site erişimi veya oturum gerekebilir.'})

        self.server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
        self.server.daemon_threads = True

    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
