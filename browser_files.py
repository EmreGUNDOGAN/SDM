"""Validate browser transfers without accepting local network URLs."""
import ipaddress
import os
import socket
import re
from urllib.parse import urlparse, urljoin
import requests
from utils import extract_filename_from_url


def validate_file_url(url):
    if not isinstance(url,str) or len(url)>8192:
        raise ValueError('Invalid URL')
    parsed=urlparse(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Invalid URL')
    addresses=socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
    if not addresses or (os.environ.get('SDM_ALLOW_LOCAL_TEST_URLS')!='1' and
            any(not ipaddress.ip_address(addr[4][0]).is_global for addr in addresses)):
        raise ValueError('Local network addresses are not transferred')
    return url


def prepare_transfer(url):
    url=validate_file_url(url)
    for attempt in range(6):
        with requests.get(url,headers={'Range':'bytes=0-0','Accept-Encoding':'identity'},
                          stream=True,timeout=12,allow_redirects=False) as response:
            if response.is_redirect:
                url=validate_file_url(urljoin(url,response.headers['Location']))
                continue
            response.raise_for_status()
            if response.headers.get('Content-Type','').split(';')[0] in ('text/html','application/xhtml+xml'):
                raise ValueError('Login or HTML page; keep browser download')
            filename=extract_filename_from_url(url,response.headers.get('Content-Disposition'))
            size = response.headers.get('Content-Range', '').rsplit('/', 1)[-1] if response.status_code == 206 else response.headers.get('Content-Length', '0')
            supports_ranges=response.status_code==206 and bool(re.fullmatch(r'bytes 0-0/[1-9][0-9]*',response.headers.get('Content-Range','')))
            return {'kind':'file','url':url,'filename':filename,'filesize':int(size) if size.isdigit() else 0,'supports_ranges':supports_ranges}
    raise ValueError('Too many redirects')
