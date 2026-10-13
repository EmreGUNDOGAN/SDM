"""Shared persisted capture preferences; site matching includes subdomains."""
import time
from urllib.parse import urlsplit
from pathlib import PurePosixPath


def normalize_domain(value):
    value = value.strip().lower()
    if '://' not in value:
        value = 'https://' + value
    parsed = urlsplit(value)
    host = (parsed.hostname or '').strip('.').removeprefix('*.')
    if not host or '/' in host or ' ' in host or parsed.username or parsed.password:
        raise ValueError('Geçerli bir site adı girin: canva.com')
    return host.encode('idna').decode('ascii')


def excluded(url, settings):
    host = (urlsplit(url or '').hostname or '').lower().strip('.')
    return any(host == domain or host.endswith('.' + domain)
               for domain in settings.get('excluded_sites', ['canva.com']))


def capture_enabled(settings, now=None):
    now = time.time() if now is None else now
    until = settings.get('capture_paused_until', 0)
    return bool(settings.get('browser_capture', True)) and until != -1 and now >= until


def should_capture(url, source_url, settings, filename=''):
    if not capture_enabled(settings) or excluded(url, settings) or excluded(source_url, settings):
        return False
    allowed = settings.get('capture_extensions', [])
    extension = PurePosixPath(filename or urlsplit(url).path).suffix.lower().lstrip('.')
    return not allowed or extension in allowed
