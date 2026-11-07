"""Untrusted captured media: public HTTP(S), pinned DNS, no cookies or proxy.

The same transport owns yt-dlp manifests/keys/fragments and SDM Range requests.
Only Referer/Origin come from the capture; Range and identity encoding are local
transport headers. Redirects open a new, independently checked connection.
"""
import http.client
import ipaddress
import os
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from urllib3.response import HTTPResponse
from yt_dlp import YoutubeDL
from yt_dlp.networking.common import Response
from yt_dlp.networking.exceptions import HTTPError, TransportError

_socket = socket.socket

class StreamValidationError(ValueError):
    pass


class StreamDRMError(StreamValidationError):
    def __init__(self):
        super().__init__('Bu video korumalı (DRM); indirilemez.')


def http_url(value):
    if (not isinstance(value, str) or not 0 < len(value) <= 8192
            or any(ord(c) <= 32 or ord(c) == 127 for c in value) or '\\' in value):
        raise StreamValidationError('Geçersiz medya adresi')
    try:
        parsed = urlsplit(value)
        port = parsed.port
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or '%' in parsed.hostname or port == 0):
            raise ValueError()
        parsed.hostname.encode('idna')
        if re.fullmatch(r'(?:0[xX][0-9a-fA-F]+|[0-9]+)(?:\.(?:0[xX][0-9a-fA-F]+|[0-9]+))*', parsed.hostname):
            # Windows and browsers disagree on short, octal and integer IPv4.
            # Accept only canonical IP spelling before any resolver sees it.
            ipaddress.IPv4Address(parsed.hostname)
    except (ValueError, UnicodeError):
        raise StreamValidationError('Geçersiz medya adresi') from None
    return parsed


def page_headers(page_url):
    page = http_url(page_url)
    host = page.hostname.encode('idna').decode()
    if ':' in host:host = '[' + host + ']'
    if page.port and page.port != (443 if page.scheme == 'https' else 80):host += ':' + str(page.port)
    return {'Referer': page_url, 'Origin': page.scheme + '://' + host}


def stream_spec(media_url, page_url, kind):
    http_url(media_url)
    if kind not in ('hls', 'dash', 'file'):
        raise StreamValidationError('Geçersiz medya türü')
    return {'kind': kind, 'page_url': page_url}, page_headers(page_url)


def public_addresses(url):
    parsed = http_url(url)
    host = parsed.hostname.rstrip('.').lower()
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    # Exact loopback fixture origin, explicitly opt-in and never enabled by UI.
    test_origin = os.environ.get('SDM_TEST_STREAM_ORIGIN', '')
    test = (os.environ.get('SDM_TEST_MODE') == '1' and bool(os.environ.get('SDM_DATA_DIR'))
            and parsed.scheme == 'http' and host == '127.0.0.1' and port >= 1024
            and f'http://127.0.0.1:{port}' == test_origin)
    if host == 'localhost' or host.endswith('.localhost'):
        raise StreamValidationError('Yerel ağ medya adresi reddedildi')
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise StreamValidationError('Medya adresi çözülemedi')
    for family, socktype, proto, _, address in addresses:
        ip = ipaddress.ip_address(address[0])
        mapped = getattr(ip, 'ipv4_mapped', None)
        if not test and (not ip.is_global or ip.is_multicast
                         or (mapped and not mapped.is_global)
                         or getattr(ip, 'sixtofour', None) or getattr(ip, 'teredo', None)
                         or ip in ipaddress.ip_network('64:ff9b::/96')):
            raise StreamValidationError('Yerel ağ medya adresi reddedildi')
    return parsed, addresses


class StreamSession(requests.Session):
    """Requests interface used by DownloadTask, without ambient auth/cookies."""
    def __init__(self, headers):
        super().__init__()
        self.trust_env = False
        # Reconstruct rather than trusting stored or extractor-supplied headers.
        self.media_headers = page_headers(headers.get('Referer'))
        if headers != self.media_headers:
            raise StreamValidationError('Geçersiz medya başlıkları')

    def send(self, request, **kwargs):
        if request.method not in ('GET', 'HEAD') or request.body:
            raise StreamValidationError('Desteklenmeyen medya isteği')
        timeout = kwargs.get('timeout') or 20
        if isinstance(timeout, tuple):timeout = max(timeout)
        url = request.url
        for redirect in range(11):
            parsed, addresses = public_addresses(url)
            connection = http.client.HTTPConnection(parsed.hostname,
                parsed.port or (443 if parsed.scheme == 'https' else 80), timeout=timeout)
            sock = None
            try:
                # Connect to the validated numeric sockaddr, never resolve a
                # second time: a rebinding answer cannot change the destination.
                for family, socktype, proto, _, address in addresses:
                    try:
                        sock = _socket(family, socktype, proto)
                        sock.settimeout(timeout);sock.connect(address)
                        break
                    except OSError:
                        if sock:sock.close()
                        sock = None
                if sock is None:raise OSError('Medya sunucusuna bağlanılamadı')
                if parsed.scheme == 'https':
                    context = ssl.create_default_context(cafile=requests.certs.where())
                    sock = context.wrap_socket(sock, server_hostname=parsed.hostname.encode('idna').decode())
                connection.sock = sock
                headers = dict(self.media_headers, **{'Accept-Encoding': 'identity', 'Connection': 'close'})
                if request.headers.get('Range'):headers['Range'] = request.headers['Range']
                target = urlunsplit(('', '', parsed.path or '/', parsed.query, ''))
                connection.request(request.method, target, headers=headers)
                raw = connection.getresponse()
                # Never expose Set-Cookie to either requests or yt-dlp.
                response_headers = {k:v for k,v in raw.getheaders() if k.lower() != 'set-cookie'}
                response = requests.Response()
                response.status_code = raw.status;response.reason = raw.reason
                response.url = url;response.request = request
                response.headers = requests.structures.CaseInsensitiveDict(response_headers)
                response.raw = HTTPResponse(body=raw, headers=response_headers, status=raw.status,
                    preload_content=False, decode_content=False, original_response=raw)
            except (OSError, http.client.HTTPException) as error:
                if sock:sock.close()
                connection.close()
                raise requests.ConnectionError('Medya bağlantısı tamamlanamadı') from error
            if response.status_code in (301, 302, 303, 307, 308) and kwargs.get('allow_redirects', True):
                location = response.headers.get('Location')
                response.close();connection.close()
                if not location or redirect == 10:
                    raise StreamValidationError('Geçersiz medya yönlendirmesi')
                url = urljoin(url, location)
                continue
            return response
        raise StreamValidationError('Çok fazla medya yönlendirmesi')


class StreamYoutubeDL(YoutubeDL):
    """All extractor and native downloader requests use the guarded transport."""
    def __init__(self, options, headers):
        self.stream_session = StreamSession(headers)
        self.blocked_error = None
        super().__init__(dict(options, http_headers=headers, proxy='', cachedir=False,
            hls_prefer_native=None, external_downloader={}, enable_file_urls=False,
            fixup='never', skip_unavailable_fragments=False))

    def close(self):
        self.stream_session.close()
        super().close()

    def dl(self, name, info, subtitle=False, test=False):
        from yt_dlp.downloader import get_suitable_downloader
        from video_http import SDMHttpFD
        from video_fragments import ObservedHlsFD, ObservedDashFD
        downloader = get_suitable_downloader(info, self.params, to_stdout=name == '-')
        if downloader not in (SDMHttpFD, ObservedHlsFD, ObservedDashFD):
            raise StreamValidationError('Bu akış güvenli yerel indirmeyi desteklemiyor')
        return super().dl(name, info, subtitle, test)

    def urlopen(self, request):
        url = request if isinstance(request, str) else request.url
        headers = {} if isinstance(request, str) else request.headers
        method = 'GET' if isinstance(request, str) else request.method
        try:
            response = self.stream_session.request(method, url, headers=headers, stream=True,
                timeout=self.params.get('socket_timeout') or 20)
            result = Response(response.raw, response.url, response.headers, response.status_code, response.reason)
            if response.status_code >= 400:raise HTTPError(result)
            return result
        except StreamValidationError as error:
            self.blocked_error = error
            raise TransportError(cause=error) from error
        except requests.RequestException as error:
            raise TransportError(cause=error) from error


def checked_info(info, kind):
    if not info or info.get('_type') in ('playlist', 'url', 'url_transparent'):
        raise StreamValidationError('Geçersiz medya kaynağı')
    if info.get('is_live'):
        raise StreamValidationError('Genel canlı akışta yerel indirme desteklenmiyor')
    if info.get('has_drm'):raise StreamDRMError()
    if 'formats' in info and not info['formats']:
        return info
    formats = info.get('formats') or [info]
    if all(f.get('has_drm') for f in formats):raise StreamDRMError()
    formats = [f for f in formats if not f.get('has_drm')]
    protocols = {'file': ('http', 'https'), 'hls': ('m3u8_native',),
                 'dash': ('http_dash_segments', 'http_dash_segments_generator')}
    if any(f.get('protocol') not in protocols[kind] for f in formats):
        raise StreamValidationError('Medya türü akışla uyuşmuyor')
    if info.get('formats'):info['formats'] = formats
    return info


def extract_stream(ydl, url, kind):
    try:
        return checked_info(ydl.extract_info(url, download=False, force_generic_extractor=True), kind)
    except Exception:
        if ydl.blocked_error:raise ydl.blocked_error
        raise


def fetch_stream_formats(media_url, page_url, kind, title=''):
    from video_downloader import format_options, tool_options
    from utils import clean_filename
    _, headers = stream_spec(media_url, page_url, kind)
    options = dict(quiet=True, no_warnings=True, noplaylist=True, skip_download=True,
                   socket_timeout=20, allow_unplayable_formats=True, **tool_options())
    with StreamYoutubeDL(options, headers) as ydl:
        info = extract_stream(ydl, media_url, kind)
    if title:info['title'] = clean_filename(title)
    result = format_options(info)
    if kind == 'file' and ('formats' not in info or info['formats']):
        result['qualities'] = [dict(height=info.get('height') or 0,
            label=f"{info['height']}p" if info.get('height') else 'Orijinal',
            filesize=info.get('filesize') or info.get('filesize_approx') or 0,
            extension=info.get('ext') or 'mp4', estimated=not bool(info.get('filesize')))]
    return result
