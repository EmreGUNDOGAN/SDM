import requests
from browser_files import validate_file_url
from urllib.parse import urljoin

def check_links(urls,cancel):
    results=[]
    with requests.Session() as session:
        for original in list(dict.fromkeys(u.strip() for u in urls if u.strip()))[:100]:
            if cancel.is_set():break
            url=original
            try:
                for _ in range(6):
                    validate_file_url(url)
                    with session.get(url,headers={'Range':'bytes=0-0','Accept-Encoding':'identity'},stream=True,allow_redirects=False,timeout=(8,15)) as response:
                        if response.is_redirect:url=urljoin(url,response.headers['Location']);continue
                        if response.status_code in (401,403):state='Yetki gerekiyor veya sunucu engelledi'
                        elif response.status_code in (404,410):state='Bağlantı bulunamadı'
                        elif response.status_code not in (200,206):state=f'Doğrulanamadı (HTTP {response.status_code})'
                        elif 'text/html' in response.headers.get('Content-Type',''):state='Sayfa erişilebilir; dosya indirmesi doğrulanamadı'
                        else:state='Erişilebilir'
                        break
                else:state='Yönlendirme sınırı; doğrulanamadı'
            except Exception:state='Bağlantı kurulamadı veya adres desteklenmiyor'
            results.append((original,state))
    return results
