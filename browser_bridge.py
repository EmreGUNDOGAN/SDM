"""Authenticated, loopback-only browser bridge. No browser cookie access."""
import hmac
import json
import os
import queue
import re
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from utils import ensure_config_dir, load_settings, save_settings
from capture_policy import should_capture, capture_enabled, normalize_domain
from app_version import VERSION

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
        self.decisions = {}
        self.decision_lock = threading.Lock()
        self.client_lock=threading.Lock();self.clients={}
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
                    if not isinstance(data,dict):raise ValueError('Geçersiz istek')
                    bridge.record_client(data.get('client'))
                    if self.path == '/ping':
                        return self.send_json(200, {'ok': True, 'version': VERSION})
                    if self.path == '/settings':
                        settings = load_settings()
                        return self.send_json(200, {'capture':capture_enabled(settings),
                            'excluded_sites':settings.get('excluded_sites',['canva.com']),
                            'capture_extensions':settings.get('capture_extensions',[])})
                    if self.path == '/decision':
                        with bridge.decision_lock:
                            decision = bridge.decisions.get(data.get('ticket'))
                            if not decision:
                                return self.send_json(404, {'error':'İstek bulunamadı'})
                            return self.send_json(200, {'action':decision['action']})
                    if self.path == '/capture-control':
                        settings = load_settings()
                        if 'minutes' in data:
                            minutes = data['minutes']
                            if type(minutes) is not int or minutes not in (0,15,60,-1):
                                raise ValueError('Geçersiz süre')
                            settings['capture_paused_until'] = -1 if minutes == -1 else time.time()+minutes*60 if minutes else 0
                        if data.get('exclude'):
                            domain = normalize_domain(data['exclude'])
                            settings['excluded_sites'] = sorted(set(settings.get('excluded_sites',[]) + [domain]))
                        if not save_settings(settings):
                            raise ValueError('Ayarlar kaydedilemedi')
                        return self.send_json(200,{'ok':True})
                    if self.path == '/file':
                        if not should_capture(data.get('url'),data.get('source_url'),load_settings(),data.get('filename','')):
                            return self.send_json(409,{'error':'Tarayıcıdan yakalama kapalı'})
                        from browser_files import prepare_transfer
                        request=prepare_transfer(data.get('url'))
                        ticket = bridge.enqueue(request)
                        return self.send_json(202,{'ok':True,'ticket':ticket})
                    url = validate_url(data.get('url'))
                    if self.path == '/formats':
                        from video_downloader import fetch_video_formats
                        return self.send_json(200, fetch_video_formats(url))
                    if self.path == '/download':
                        if not should_capture(url,url,load_settings(),'video.mp3' if data.get('audio') else 'video.mp4'):
                            return self.send_json(409,{'error':'Bu sitede SDM yakalaması kapalı'})
                        height = data.get('height')
                        audio = data.get('audio', False)
                        if not isinstance(audio, bool) or (not audio and
                                (type(height) is not int or not 1 <= height <= 16384)):
                            raise ValueError('Geçersiz kalite seçimi')
                        ticket = bridge.enqueue({'kind':'video','url':url,'height':height,'audio':audio,
                            'filename':str(data.get('title','Video'))[:240],'filesize':data.get('filesize',0)})
                        return self.send_json(202, {'ok': True,'ticket':ticket})
                    self.send_json(404, {'error': 'Bilinmeyen işlem'})
                except (ValueError, TypeError, queue.Full):
                    self.send_json(400, {'error': 'Geçersiz veya desteklenmeyen istek'})
                except Exception:
                    self.send_json(502, {'error': 'Video bilgisi alınamadı. Site erişimi veya oturum gerekebilir.'})

        self.server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
        self.server.daemon_threads = True

    def record_client(self,client):
        if not isinstance(client,dict):return
        browser=client.get('browser');version=client.get('version')
        if browser not in ('Chrome','Opera','Edge') or not isinstance(version,str) or len(version)>32 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}',version):return
        with self.client_lock:self.clients[browser]=dict(version=version,seen=time.monotonic())

    def client_snapshot(self):
        with self.client_lock:return {name:dict(value) for name,value in self.clients.items()}

    def enqueue(self, request):
        with self.decision_lock:
            now = time.time()
            self.decisions = {k:v for k,v in self.decisions.items() if now-v['created'] < 1800}
            if len(self.decisions) >= 64:
                raise queue.Full()
            ticket = uuid.uuid4().hex
            request['ticket'] = ticket
            self.pending.put_nowait(request)
            self.decisions[ticket] = {'action':'pending','created':now}
            return ticket

    def decide(self, ticket, action):
        if action not in ('start','queue','cancel','browser'):
            raise ValueError('Invalid decision')
        with self.decision_lock:
            if ticket in self.decisions:
                self.decisions[ticket]['action'] = action

    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
