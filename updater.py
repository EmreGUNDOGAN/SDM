"""GitHub releases updater. Credentials stay DPAPI-encrypted on this PC."""
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
import requests
from app_version import VERSION
from utils import ensure_config_dir

REPO = 'EmreGUNDOGAN/SDM'
API = f'https://api.github.com/repos/{REPO}'


class UpdateError(RuntimeError):
    pass


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def _protect(data, decrypt=False):
    if os.name != 'nt':
        raise UpdateError('Güvenli token saklama yalnızca Windows üzerinde kullanılabilir.')
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise UpdateError('Windows şifreleme işlemi tamamlanamadı.')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


def save_token(token):
    path = ensure_config_dir() / 'github-update-token.bin'
    if not token.strip():
        path.unlink(missing_ok=True)
    else:
        temp = path.with_suffix('.tmp')
        temp.write_bytes(_protect(token.strip().encode()))
        temp.replace(path)


def load_token():
    path = ensure_config_dir() / 'github-update-token.bin'
    return _protect(path.read_bytes(), True).decode() if path.exists() else ''


def version_tuple(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise UpdateError('Sürüm numarası geçersiz.')
    return tuple(map(int, match.groups()))


class GitHubUpdater:
    def __init__(self, token=None, session=None):
        self.token = load_token() if token is None else token
        self.session = session or requests.Session()

    def _get(self, url, binary=False):
        # Credentials are sent only to this repository's API, never to redirects.
        if not url.startswith(API + '/'):
            raise UpdateError('Güncelleme kaynağı doğrulanamadı.')
        headers = {'Accept': 'application/octet-stream' if binary else 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': f'SDM/{VERSION}'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        try:
            response = self.session.get(url, headers=headers, timeout=(15, 45),
                                        stream=binary, allow_redirects=False)
            for _ in range(5):
                if response.status_code not in (301, 302, 303, 307, 308):
                    break
                location = response.headers.get('Location', '')
                parsed = urlsplit(location)
                if parsed.scheme != 'https' or parsed.hostname not in {
                    'release-assets.githubusercontent.com', 'objects.githubusercontent.com'} or parsed.username or parsed.password:
                    response.close()
                    raise UpdateError('GitHub indirme yönlendirmesi doğrulanamadı.')
                response.close()
                response = self.session.get(location, headers={'Accept': 'application/octet-stream'},
                                            stream=binary, timeout=(15, 45), allow_redirects=False)
            if response.status_code in (401, 403, 404):
                response.close()
                raise UpdateError('Özel depoya erişilemiyor. SDM deposu için Contents: Read yetkili token girin; süresi dolmuşsa yenileyin.')
            response.raise_for_status()
            return response
        except requests.RequestException:
            raise UpdateError('GitHub bağlantısı tamamlanamadı. İnternet bağlantınızı kontrol edip tekrar deneyin.') from None

    def check(self):
        with self._get(API + '/releases/latest') as response:
            release = response.json()
        version = release.get('tag_name', '')
        if release.get('draft') or release.get('prerelease'):
            raise UpdateError('Kararlı bir sürüm bulunamadı.')
        if version_tuple(version) <= version_tuple(VERSION):
            return None
        name = f'SDM-Setup-{version.lstrip("v")}.exe'
        asset = next((a for a in release.get('assets', []) if a.get('name') == name), None)
        digest = asset.get('digest', '') if asset else ''
        if not asset or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
            raise UpdateError('Yeni sürümün setup dosyası veya SHA-256 doğrulama bilgisi bulunamadı.')
        expected_url = f'{API}/releases/assets/{int(asset["id"])}'
        if asset.get('url') != expected_url or not 0 < asset.get('size', 0) < 1024 ** 3:
            raise UpdateError('Setup dosyasının kaynak bilgisi geçersiz.')
        return {'version': version, 'asset': asset}

    def download(self, update, progress=None):
        asset = update['asset']
        # Do not accept arbitrary executable names from the server or caller.
        name = f'SDM-Setup-{update["version"].lstrip("v")}.exe'
        version_tuple(update['version'])
        if asset['name'] != name or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', asset.get('digest', '')):
            raise UpdateError('Setup doğrulama bilgisi geçersiz.')
        folder = ensure_config_dir() / 'updates'
        folder.mkdir(exist_ok=True)
        target = folder / name
        partial = target.with_suffix('.part')
        digest = hashlib.sha256()
        count = 0
        try:
            with self._get(f'{API}/releases/assets/{int(asset["id"])}', True) as response, partial.open('wb') as output:
                for chunk in response.iter_content(256 * 1024):
                    if not chunk:
                        continue
                    count += len(chunk)
                    if count > asset['size']:
                        raise UpdateError('Setup dosya boyutu beklenenden büyük.')
                    output.write(chunk)
                    digest.update(chunk)
                    if progress:
                        progress(count, asset['size'])
            if count != asset['size'] or digest.hexdigest() != asset['digest'].split(':')[1].lower():
                raise UpdateError('Setup bütünlük kontrolünden geçemedi; kurulum başlatılmadı.')
            with partial.open('rb') as stream:
                if stream.read(2) != b'MZ':
                    raise UpdateError('Setup dosyası geçerli bir Windows uygulaması değil.')
            partial.replace(target)
            return target
        finally:
            partial.unlink(missing_ok=True)


def launch_installer(path):
    subprocess.Popen([str(path), '/NORESTART'], close_fds=True)
